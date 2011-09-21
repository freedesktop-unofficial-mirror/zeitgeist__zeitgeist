#!/usr/bin/python
# -.- coding: utf-8 -.-

# Update python path to use local zeitgeist module
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from zeitgeist.datamodel import *
from testutils import import_events

import unittest
import logging

TEST_ACTOR = "/usr/share/applications/gnome-about.desktop"

test_event_1 = None
def create_test_event_1():
	ev = Event()
	ev.timestamp = 0
	ev.interpretation = Manifestation.USER_ACTIVITY
	ev.manifestation = Interpretation.CREATE_EVENT
	ev.actor = TEST_ACTOR
	subj = Subject()
	subj.uri = u"test://mytest"
	subj.manifestation = "lala"
	subj.interpretation = "tinky winky"
	subj.origin = "test://"
	subj.mimetype = "YOMAMA"
	subj.text = "SUCKS"
	subj.storage = "MyStorage"

	ev.append_subject(subj)
	return ev


class _engineTestClass(unittest.TestCase):
	
	def setUp (self):
		from _zeitgeist.engine import constants
		from _zeitgeist.engine import get_engine
		
		self.save_default_ext = os.environ.get("ZEITGEIST_DEFAULT_EXTENSIONS")
		self.save_extra_ext = os.environ.get("ZEITGEIST_EXTRA_EXTENSIONS")
		os.environ["ZEITGEIST_DEFAULT_EXTENSIONS"] = ""
		os.environ["ZEITGEIST_EXTRA_EXTENSIONS"] = ""
		global test_event_1
		test_event_1 = create_test_event_1()
		
		# Some extensions keep state around that interferes
		# with the tests, so we disable all extensions
		constants.DEFAULT_EXTENSIONS = []
		
		# Memory backed tmp DB
		constants.DATABASE_FILE = ":memory:"
		
		self.engine = get_engine()
	
	def tearDown (self):
		import _zeitgeist.engine
		if self.save_default_ext is not None:
			os.environ["ZEITGEIST_DEFAULT_EXTENSIONS"] = self.save_default_ext
		else:
			del os.environ["ZEITGEIST_DEFAULT_EXTENSIONS"]
		if self.save_extra_ext is not None:
			os.environ["ZEITGEIST_EXTRA_EXTENSIONS"] = self.save_extra_ext
		else:
			del os.environ["ZEITGEIST_EXTRA_EXTENSIONS"]
		self.engine.close()
		_zeitgeist.engine._engine = None

class ZeitgeistEngineTest(_engineTestClass):
	"""
	This class tests that the zeitgeist.engine.engine.ZeitgeistEngine class
	"""
		
	def testSingleInsertGet(self):
		global test_event_1
		# Insert item and event
		ids = self.engine.insert_events([test_event_1])
		result = self.engine.get_events(ids)
		
		self.assertEquals(1, len(result))
		resulting_event = result.pop()
		self.assertEquals(len(resulting_event), len(test_event_1))
		
		# fixing id, the initial event does not have any id set
		test_event_1[0][0] = 1
		
		self.assertEqual(resulting_event, test_event_1)
		
		# Reset the id because other test cases rely on this one
		test_event_1[0][0] = None
	
	def testInsertGetWithoutTimestamp(self):
		# We test two things, that Event creates a default timestamp
		# and that the engine provides one for us if don't do our selves
		
		subj = Subject.new_for_values(interpretation="foo://interp",
					manifestation="foo://manif",
					uri="nowhere")
		ev = Event.new_for_values(interpretation="foo://bar",
					manifestation="foo://quiz",
					actor="actor://myself",
					subjects=[subj])
		
		# Assert that timestamp is set
		self.assertTrue(ev.timestamp)
		
		# Clear the timestamp and insert event
		ev.timestamp = ""
		ids = self.engine.insert_events([ev])
		result = self.engine.get_events(ids)
		
		self.assertEquals(1, len(result))
		resulting_event = Event(result.pop())
		self.assertEquals("foo://bar", resulting_event.interpretation)
		self.assertTrue(ev.timestamp) # We should have a timestamp again
	
	def testDuplicateEventInsertion(self):
		self.testSingleInsertGet()
		
		# Inserting the same event again should be ok, but not
		# cause duplicates
		self.testSingleInsertGet()
		
		# Find all events, and make sure that this is exactly one event
		result = self.engine.find_eventids(
			(0, 10000000),
			[],
			StorageState.Any,
			10,
			0)
		self.assertEquals(1, len(result))
		self.assertEquals(1, result[0]) # The single event must have id 1
	
	def testDeleteSingle(self):
		self.testSingleInsertGet()
		self.engine.delete_events([1])
		result = self.engine.get_events([1])
		self.assertEquals(0, len(filter(None, result)))
	
	def testEventInsertionAfterRemovingCachedRow(self):
		# This test case reproduces bug #598666: "Invalid cache access".
		
		# Insert an event with interpretation "tinky winky" and
		# delete it thereafter - there's no event with that interpretation
		# left (so the interpretation is removed from the database)
		self.testDeleteSingle()
		self.assertEqual(len(self.engine._interpretation), 0)
		
		# Now we insert an event with the same interpretation again
		ids = self.engine.insert_events([test_event_1])
		self.assertEqual(len(self.engine._interpretation), 2)
		self.assertEqual(len(self.engine._cursor.execute("SELECT * FROM interpretation").fetchall()), 2)
	
	def testDeleteSingleCascades(self):
		manif_value = "stfu:EpicFailActivity"
		
		def row_count(table, value=None):
			sql = "SELECT * FROM %s" % table
			if value:
				sql += " WHERE value=\"%s\"" % value
			return len(self.engine._cursor.execute(sql).fetchall())
		
		# Ensure DB sanity
		self.assertEquals(row_count("manifestation", manif_value), 0)
		
		# Insert data
		import_events("test/data/five_events.js", self.engine)
		self.assertEquals(row_count("manifestation", manif_value), 1)
		
		# Delete one event
		event_template = Event.new_for_values(manifestation=manif_value)
		result = self.engine.find_eventids(TimeRange.always(),
			[event_template], StorageState.Any, 0, 1)
		self.assertEquals(1, len(result))
		self.engine.delete_events([result[0]])
		
		# Ensure it got deleted
		self.assertEquals(row_count("manifestation", manif_value), 0)
		
		# Delete all other events
		result = self.engine.find_eventids(TimeRange.always(), [],
			StorageState.Any, 0, 1)
		self.engine.delete_events(result)
		
		# Ensure everything got deleted
		self.assertEquals(row_count("interpretation"), 0)
		self.assertEquals(row_count("manifestation"), 0)
		self.assertEquals(row_count("actor"), 0)
		self.assertEquals(row_count("uri"), 0)
		self.assertEquals(row_count("payload"), 0)
	
	def testIllegalPredefinedEventId(self):
		event = Event()
		event[0][0] = 23 # This is illegal, we assert the erro later
		event.timestamp = 0
		event.interpretation = Manifestation.USER_ACTIVITY
		event.manifestation = Interpretation.CREATE_EVENT
		event.actor = "/usr/share/applications/gnome-about.desktop"
		
		subject = Subject()
		subject.uri = "file:///tmp/file.txt"
		subject.manifestation = Manifestation.FILE_DATA_OBJECT
		subject.interpretation = Interpretation.DOCUMENT
		subject.origin = "test://"
		subject.mimetype = "text/plain"
		subject.text = "This subject has no text"
		subject.storage = "368c991f-8b59-4018-8130-3ce0ec944157" # UUID of home partition
		
		event.append_subject(subject)
		
		# Insert item and event
		ids = self.engine.insert_events([event,])
		self.assertEquals(len(ids), 1)
		# event is not inserted, id == 0 means error
		self.assertEquals(ids[0], 0)
		# check if really not events were inserted
		ids = self.engine.find_eventids(TimeRange.always(), [],
			StorageState.Any, 0, ResultType.MostRecentEvents)
		self.assertEquals(len(ids), 0)
		
	def testGetNonExisting(self):
		events = self.engine.get_events([23,45,65])
		self.assertEquals(3, len(events))
		for ev in events : self.assertEquals(None, ev)
		
	def testGetDuplicateEventIds(self):
		import_events("test/data/five_events.js", self.engine)
		events = self.engine.get_events([1, 1])
		self.assertEqual(2, len(events))
		self.assertEqual(2, len(filter(None, events)))
		self.assertTrue(events[0].id == events[1].id == 1)
		
	def testFindEventsId(self):
		global test_event_1
		self.testSingleInsertGet()
		result = self.engine.find_eventids(
			(0, 100),
			[],
			StorageState.Any,
			5,
			0,)
		self.assertEquals(1, len(result))
		test_event_1[0][0] = 1
		self.assertEqual(result[0], test_event_1.id)
	
	def testFindNothing(self):
		result = self.engine.find_eventids(
			(10000, 1000000),
			[],
			StorageState.Any,
			5,
			0,)
		self.assertEquals(0, len(result))

	def testFindNothingBackwards(self):
		result = self.engine.find_eventids(
			(1000000, 1),
			[],
			StorageState.Any,
			5,
			0,)
		self.assertEquals(0, len(result))

	def testFindFilteredByEventButNotSubject(self):
		# revision rainct@ubuntu.com-20091128164327-j8ez3fsifd1gygkr (1185)
		# Fix _build_templates so that it works when the Subject is empty.
		self.testSingleInsertGet()
		result = self.engine.find_eventids(
			TimeRange.always(),
			[Event.new_for_values(interpretation=Interpretation.LEAVE_EVENT)],
			StorageState.Any, 0, 0)
		self.assertEquals(0, len(result))

	def testFindFive(self):
		import_events("test/data/five_events.js", self.engine)
		result = self.engine.find_eventids(
			(1, 10000000),
			[],
			StorageState.Any,
			0,
			0)
		self.assertEquals(5, len(result))

	def testFindFiveWithStorageState(self):
		import_events("test/data/five_events.js", self.engine)
		# The event's storage is unknown, so we get them back always.
		result = self.engine.find_eventids(TimeRange.always(), [],
			StorageState.Available, 0, 0)
		self.assertEquals(5, len(result))
		result = self.engine.find_eventids(TimeRange.always(), [],
			StorageState.NotAvailable, 0, 0)
		self.assertEquals(5, len(result))

	def testFindWithNonExistantActor(self):
		# Bug 496109: filtering by timerange and a non-existing actor gave an
		# incorrect result.
		import_events("test/data/five_events.js", self.engine)
		result = self.engine.find_eventids(
			TimeRange.until_now(),
			[Event.new_for_values(actor="fake://foobar")],
			StorageState.Any, 0, 0)
		self.assertEquals(0, len(result))

	def testFindWithSubjectText(self):
		import_events("test/data/five_events.js", self.engine)
		result = self.engine.find_eventids(
			(1, 10000000),
			[Event.new_for_values(subject_text='this is not real')],
			StorageState.Any,
			0,
			0)
		self.assertEquals(0, len(result))
		result = self.engine.find_eventids(
			(1, 10000000),
			[Event.new_for_values(subject_text='some text')],
			StorageState.Any,
			0,
			0)
		self.assertEquals(1, len(result))
		result = self.engine.find_eventids(
			(1, 10000000),
			[Event.new_for_values(subject_text='this *')],
			StorageState.Any,
			0,
			0)
		self.assertEquals(0, len(result)) # wildcards are not supported
		result = self.engine.find_eventids(
			(1, 10000000),
			[Event.new_for_values(subject_text='this item *')],
			StorageState.Any,
			0,
			0)
		self.assertEquals(1, len(result))

	def testSortFindByTimeAsc(self):
		import_events("test/data/twenty_events.js", self.engine)
		result = self.engine.find_eventids(
			(1, 10000000),
			[],
			StorageState.Any,
			2,
			ResultType.LeastRecentEvents,)
		event1 = self.engine.get_events([result[0]])[0]
		event2 = self.engine.get_events([result[1]])[0]
		self.assertEquals(True, event1.timestamp < event2.timestamp)
		
	def testSortFindByTimeDesc(self):
		import_events("test/data/twenty_events.js", self.engine)
		result = self.engine.find_eventids(
			(1, 10000000),
			[],
			StorageState.Any,
			2,
			ResultType.MostRecentEvents,)
		event1 = self.engine.get_events([result[0]])[0]
		event2 = self.engine.get_events([result[1]])[0]
		self.assertEquals(True, event1.timestamp > event2.timestamp)
	
	def testFindWithActor(self):
		global test_event_1
		self.testSingleInsertGet()
		subj = Subject()
		event_template = Event.new_for_values(actor=TEST_ACTOR, subjects=[subj,])
		result = self.engine.find_eventids(
			(0, 100),
			[event_template, ],
			StorageState.Any,
			0,
			1,)
		self.assertEquals(1, len(result))
		test_event_1[0][0] = 1
		self.assertEqual(result[0], test_event_1.id)

	def testFindWithInterpretation(self):
		import_events("test/data/five_events.js", self.engine)
		subj = Subject()
		event_template = Event.new_for_values(interpretation="stfu:OpenEvent", subjects=[subj])
		result = self.engine.find_eventids(TimeRange.always(),
			[event_template,], StorageState.Any, 0, 1)
		self.assertEquals(2, len(result))
		events = self.engine.get_events(result)
		for event in events:
			self.assertEqual(event.interpretation, "stfu:OpenEvent")

	def testFindWithInterpretationReturnEvents(self):
		import_events("test/data/five_events.js", self.engine)
		event_template = Event.new_for_values(interpretation="stfu:OpenEvent",
		    subjects=[Subject()])
		events = self.engine.find_events(TimeRange.always(), [event_template],
		    StorageState.Any, 0, 1)
		self.assertEquals(2, len(events))
		for event in events:
			self.assertEqual(event.interpretation, "stfu:OpenEvent")

	def testFindEventTwoInterpretations(self):
		import_events("test/data/twenty_events.js", self.engine)
		result = self.engine.find_eventids((102, 117), [
			Event.new_for_values(interpretation="stfu:OpenEvent"),
			Event.new_for_values(interpretation="stfu:EvilEvent")
			], StorageState.Any, 0, 0)
		self.assertEquals(15, len(result))

	def testFindWithFakeInterpretation(self):
		import_events("test/data/twenty_events.js", self.engine)
		result = self.engine.find_events(TimeRange.until_now(),
			[Event.new_for_values(interpretation="this-is-not-an-intrprettin")],
			StorageState.Any, 0, 0)
		self.assertEquals(0, len(result))

	def testFindWithManifestation(self):
		import_events("test/data/five_events.js", self.engine)
		subj = Subject()
		event_template = Event.new_for_values(manifestation="stfu:EpicFailActivity", subjects=[subj])
		result = self.engine.find_eventids(TimeRange.always(),
			[event_template,], StorageState.Any, 0, 1)
		self.assertEquals(1, len(result))
		events = self.engine.get_events(result)
		for event in events:
			self.assertEqual(event.manifestation, "stfu:EpicFailActivity")
	
	def testFindWithEventOrigin(self):
		import_events("test/data/twenty_events.js", self.engine)
		event_template = Event.new_for_values(origin="origin3")
		result = self.engine.find_eventids(TimeRange.always(),
			[event_template], StorageState.Any, 0, 1)
		events = self.engine.get_events(result)
		
		self.assertTrue(len(events) > 0)
		self.assertTrue(all(ev.origin == "origin3" for ev in events))
	
	def testFindWithEventOriginNegatedWildcard(self):
		import_events("test/data/twenty_events.js", self.engine)
		event_template = Event.new_for_values(origin="!origin*")
		result = self.engine.find_eventids(TimeRange.always(),
			[event_template], StorageState.Any, 0, 1)
		events = self.engine.get_events(result)
		
		self.assertTrue(len(events) > 0)
		self.assertFalse(any(ev.origin.startswith("origin") for ev in events))
	
	def testFindWithSubjectOrigin(self):
		import_events("test/data/five_events.js", self.engine)
		subj = Subject.new_for_values(origin="file:///tmp")
		event_template = Event.new_for_values(subjects=[subj])
		result = self.engine.find_eventids((0, 1000), [event_template, ], StorageState.Any, 0, 1)
		events = self.engine.get_events(result)
		for event in events:
			test = any(subj.origin == "file:///tmp" for subj in event.subjects)
			self.assertTrue(test)

	def testFindMultipleEvents(self):
		import_events("test/data/five_events.js", self.engine)
		subj1 = Subject.new_for_values(uri="file:///home/foo.txt")
		event_template1 = Event.new_for_values(subjects=[subj1])
		subj2 = Subject.new_for_values(uri="file:///tmp/foo.txt")
		event_template2 = Event.new_for_values(subjects=[subj2])
		result = self.engine.find_eventids((0, 1000), [event_template1, event_template2], StorageState.Any, 0, 4)
		self.assertEquals(2, len(result))
		events = self.engine.get_events(result)
		
	def testGetWithMultipleSubjects(self):
		subj1 = Subject.new_for_values(uri="file:///tmp/foo.txt")
		subj2 = Subject.new_for_values(uri="file:///tmp/loo.txt")
		event_template = Event.new_for_values(subjects=[subj1, subj2])
		result = self.engine.insert_events([event_template])
		events = self.engine.get_events(result)
		self.assertEquals(2, len(events[0].subjects))
		self.assertEquals("file:///tmp/foo.txt", events[0].subjects[0].uri)
		self.assertEquals("file:///tmp/loo.txt", events[0].subjects[1].uri)
	
	def testFindEventIdsWithMultipleSubjects(self):
		subj1 = Subject.new_for_values(uri="file:///tmp/foo.txt")
		subj2 = Subject.new_for_values(uri="file:///tmp/loo.txt")
		event = Event.new_for_values(subjects=[subj1, subj2])
		orig_ids = self.engine.insert_events([event])
		result_ids = self.engine.find_eventids(TimeRange.always(), [Event()], StorageState.Any, 0, 1)
		self.assertEquals(orig_ids, list(result_ids))

	def testFindEventsEventTemplate(self):
		import_events("test/data/five_events.js", self.engine)
		subj = Subject.new_for_values(interpretation="stfu:Bee")
		subj1 = Subject.new_for_values(interpretation="stfu:Bar")
		event_template = Event.new_for_values(subjects=[subj, subj1])
		result = self.engine.find_eventids(
			(0, 200),
			[event_template, ],
			StorageState.Any,
			100,
			0,)
		self.assertEquals(0, len(result)) # no subject with two different
										  # interpretations at the same time
		subj = Subject.new_for_values(uri="file:///tmp/foo.txt")
		subj1 = Subject.new_for_values(interpretation="stfu:Image")
		event_template = Event.new_for_values(subjects=[subj, subj1])
		result = self.engine.find_eventids(
			(0, 200),
			[event_template, ],
			StorageState.Any,
			100,
			0,)
		self.assertEquals(1, len(result))		
	
	def testJsonImport(self):
		import_events("test/data/single_event.js", self.engine)
		results = self.engine.get_events([1])
		self.assertEquals(1, len(results))
		ev = results[0]
		self.assertEquals(1, ev.id)
		self.assertEquals("123", ev.timestamp)
		self.assertEquals("stfu:OpenEvent", ev.interpretation)
		self.assertEquals("stfu:UserActivity", ev.manifestation)
		self.assertEquals("firefox", ev.actor)
		self.assertEquals(1, len(ev.subjects))
		
		subj = ev.subjects[0]
		self.assertEquals("file:///tmp/foo.txt", subj.uri)
		self.assertEquals("stfu:Document", subj.interpretation)
		self.assertEquals("stfu:File", subj.manifestation)
		self.assertEquals("text/plain", subj.mimetype)
		self.assertEquals("this item has no text... rly!", subj.text)
		self.assertEquals("368c991f-8b59-4018-8130-3ce0ec944157", subj.storage)
		
	def testInsertSubjectOptionalAttributes(self):
		ev = Event.new_for_values(
			timestamp=123,
			interpretation=Interpretation.ACCESS_EVENT,
			manifestation=Manifestation.USER_ACTIVITY,
			actor="Freak Mamma"
		)
		subj = Subject.new_for_values(
			uri="void://foobar",
			interpretation=Interpretation.DOCUMENT,
			manifestation=Manifestation.FILE_DATA_OBJECT,
			)
		ev.append_subject(subj)
		
		ids = self.engine.insert_events([ev,])
		result = self.engine.get_events(ids)
		self.assertEquals(len(ids), len(result))
	
	def testEventWithoutSubject(self):
		ev = Event.new_for_values(timestamp=123,
					interpretation=Interpretation.ACCESS_EVENT,
					manifestation=Manifestation.USER_ACTIVITY,
					actor="Freak Mamma")
		ids = self.engine.insert_events([ev,])
		self.assertEquals(len(ids), 1)
		# event is not inserted, id == 0 means error
		self.assertEquals(ids[0], 0)
		# check if really not events were inserted
		ids = self.engine.find_eventids(TimeRange.always(), [],
			StorageState.Any, 0, ResultType.MostRecentEvents)
		self.assertEquals(len(ids), 0)
		
	def testUnicodeEventInsert(self):
		# Insert and get a unicode event
		ids = import_events("test/data/unicode_event.js", self.engine)
		self.assertEquals(len(ids), 1)
		result = self.engine.get_events(ids)
		self.assertEquals(1, len(result))
		event = result[0]
		self.assertEquals(1, len(event.subjects))
		self.assertEquals(u"hällö, I'm gürmen - åge drikker øl - ☠", event.subjects[0].text)
		self.assertEquals(u"http://live.gnome.org/☠", event.subjects[0].uri)
		
		# update the event we got from the DB's timestamp and insert
		# it again, we want to to test some ping-pong back and forth
		event[0][Event.Id] = None
		event.timestamp = 243
		ids = self.engine.insert_events([event])
		result = self.engine.get_events(ids)
		self.assertEquals(1, len(result))
		event = result[0]
		self.assertEquals(1, len(event.subjects))
		self.assertEquals(u"hällö, I'm gürmen - åge drikker øl - ☠", event.subjects[0].text)
		self.assertEquals(u"http://live.gnome.org/☠", event.subjects[0].uri)		
		
		# try and find a unicode event, we use unicode and not
		# inconsequently on deliberation
		subj = Subject.new_for_values(text="hällö, I'm gürmen - åge drikker øl - ☠",
					origin="file:///åges_øl í",
					uri=u"http://live.gnome.org/☠")
		event_template = Event.new_for_values(subjects=[subj,])
		result = self.engine.find_eventids(
			(0, 200),
			[event_template, ],
			StorageState.Any,
			100,
			0,)
		self.assertEquals(len(result), 1)
	
	def testEventWithBinaryPayload(self):
		ev = Event()
		subject = Subject()
		ev.actor = "application:///firefox.desktop"
		ev.manifestation = Manifestation.USER_ACTIVITY
		ev.interpretation = Interpretation.ACCESS_EVENT
		subject.uri = "http://www.google.com"
		subject.interpretation = Interpretation #InterPretation.UNKNOWN
		subject.manifestation = Manifestation #Manifestation.WEB_HISTORY
		subject.text = None
		subject.mimetype = "text/html"
		subject.origin = None
		subject.storage = None
		ev.subjects.append(subject)

		sampleString = """
		<Content name="Telepathy" class="Text">
		  <header>johnsmith@foo.bar</header>
		  <body>
		    John: Here is a talking point
		    You: Ok that looks fine
		  </body>
		  <launcher command="{application} johnsmith@foo.bar"/>
		</Content>"""
		
		ev.payload = sampleString.encode("UTF-8")
		ids = self.engine.insert_events([ev])
		_ev = self.engine.get_events(ids)[0]
		self.assertEquals(ev.payload, _ev.payload)
		
		# Note: engine.insert_events() sets the id of the Event objects
		self.assertEquals(ev, _ev)

	def testQueryByParent (self):
		ev = Event.new_for_values(subject_interpretation=Interpretation.AUDIO)
		_ids = self.engine.insert_events ([ev])
		
		tmpl = Event.new_for_values(subject_interpretation=Interpretation.MEDIA)
		ids = self.engine.find_eventids(TimeRange.always(),
			[tmpl], StorageState.Any, 10, ResultType.MostRecentEvents)
		
		self.assertEquals(1, len(ids))
		self.assertEquals(_ids, list(ids))
		
	def testNegation(self):
		import_events("test/data/five_events.js", self.engine)

		template = Event.new_for_values(
			interpretation = "!stfu:OpenEvent"
		)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(3, len(ids))
		
		template = Event.new_for_values(
			manifestation = "!stfu:YourActivity"
		)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(4, len(ids))
		
		template = Event.new_for_values(
			actor = "!firefox"
		)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(2, len(ids))
		
		template = Event.new_for_values(
			subject_uri = "!file:///tmp/foo.txt"
		)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(3, len(ids))
		
		template = Event.new_for_values(
			subject_interpretation = "!stfu:Document"
		)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(4, len(ids))
		
		template = Event.new_for_values(
			subject_manifestation = "!stfu:File"
		)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(0, len(ids))
		
		template = Event.new_for_values(
			subject_origin = "!file:///tmp"
		)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(0, len(ids))
		
		template = Event.new_for_values(
			subject_mimetype = "!text/plain"
		)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(0, len(ids))
		
		# the next two fields do not support negation, '!' is treated as
		# content
		
		template = Event.new_for_values(
			subject_text = "!boo"
		)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(0, len(ids))
		
		# searching by subject_storage is not working
		#~ template = Event.new_for_values(
			#~ subject_storage = "!boo"
		#~ )
		#~ ids = self.engine.find_eventids(TimeRange.always(),
			#~ [template,], StorageState.Any, 10, ResultType.MostRecentEvents
		#~ )
		#~ self.assertEquals(0, len(ids))
		
	def testNegationOntology(self):
		events = [
			Event.new_for_values(interpretation=Interpretation.MEDIA, subject_uri="test"),
			Event.new_for_values(interpretation=Interpretation.AUDIO, subject_uri="test"),
			Event.new_for_values(interpretation=Interpretation.VIDEO, subject_uri="test"),
			Event.new_for_values(interpretation=Interpretation.DOCUMENT, subject_uri="test"),
		]
		self.engine.insert_events(events)
		
		template = Event.new_for_values(interpretation="!%s" %Interpretation.AUDIO)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(3, len(ids))
		
		template = Event.new_for_values(interpretation="!%s" %Interpretation.MEDIA)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(1, len(ids))
		
		
	def testNegationCombination(self):
		import_events("test/data/five_events.js", self.engine)
		
		template = Event.new_for_values(
			interpretation = "!stfu:OpenEvent",
			actor = "!firefox"
		)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(2, len(ids))
		
		template = Event.new_for_values(
			interpretation = "!stfu:OpenEvent",
			manifestation = "!stfu:YourActivity"
		)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(3, len(ids))
		
	def testFindStorageNotExistant(self):
		events = [
			Event.new_for_values(timestamp=1000, subject_storage="sometext"),
			Event.new_for_values(timestamp=2000, subject_storage="anotherplace")
		]
		ids_in = self.engine.insert_events(events)
		template = Event.new_for_values(subject_storage="xxx")
		results = self.engine.find_eventids(TimeRange.always(), [template], 
						StorageState.Any, 10, ResultType.MostRecentEvents)
		self.assertEquals(0, len(results))
				
	def testFindStorage(self):
		events = [
			Event.new_for_values(timestamp=1000, subject_storage="sometext"),
			Event.new_for_values(timestamp=2000, subject_storage="anotherplace")
		]
		ids_in = self.engine.insert_events(events)
		template = Event.new_for_values(subject_storage="sometext")
		results = self.engine.find_eventids(TimeRange.always(), [template], 
						StorageState.Any, 10, ResultType.MostRecentEvents)
		self.assertEquals(1, len(results))
		
	def testWildcard(self):
		import_events("test/data/five_events.js", self.engine)

		template = Event.new_for_values(
			actor = "ge*"
		)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(2, len(ids))
		
		template = Event.new_for_values(
			actor = "!ge*"
		)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(3, len(ids))
		
		template = Event.new_for_values(
			subject_mimetype = "text/*"
		)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(5, len(ids))
		
		template = Event.new_for_values(
			subject_uri = "http://*"
		)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(1, len(ids))

		template = Event.new_for_values(
			subject_current_uri = "http://*"
		)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(1, len(ids))
		
		template = Event.new_for_values(
			subject_origin = "file://*"
		)
		ids = self.engine.find_eventids(TimeRange.always(),
			[template,], StorageState.Any, 10, ResultType.MostRecentEvents
		)
		self.assertEquals(5, len(ids))
		
	def testWildcardOptimization(self):
		from _zeitgeist.engine.sql import WhereClause
		
		cursor = self.engine._cursor
		strings = [
			(u"hällö, I'm gürmen - åge drikker øl - ☠ bug",),
			(u"ä ☠ åø",),
			(u"h" + unichr(0x10ffff),),
			(unichr(0x10ffff),),
			("",),
			(unichr(0x10ffff) + unichr(0x10ffff) + "aa",),
		]
		
		# does it work for ascii chars?
		cursor.executemany("INSERT INTO uri(value) VALUES(?)", strings)
		stm = WhereClause.optimize_glob("value", "uri", u"h")
		self.assertEquals(
			cursor.execute(*stm).fetchall(),
			cursor.execute("SELECT value FROM uri WHERE value GLOB ?", ("h*",)).fetchall()
		)
		self.assertEquals(len(cursor.execute(*stm).fetchall()), 2)
		
		# bunch of unicode in the prefix
		stm = WhereClause.optimize_glob("value", "uri", u"ä ☠ å")
		self.assertEquals(
			cursor.execute(*stm).fetchall(),
			cursor.execute("SELECT value FROM uri WHERE value GLOB ?", (u"ä ☠ å*",)).fetchall()
		)
		self.assertEquals(len(cursor.execute(*stm).fetchall()), 1)
		
		# bunch of unicode in the prefix, prefix is not 'utf-8' decoded
		stm = WhereClause.optimize_glob("value", "uri", "ä ☠ å")
		self.assertEquals(
			cursor.execute(*stm).fetchall(),
			cursor.execute("SELECT value FROM uri WHERE value GLOB ?", ("ä ☠ å*",)).fetchall()
		)
		self.assertEquals(len(cursor.execute(*stm).fetchall()), 1)
		
		# select all
		stm = WhereClause.optimize_glob("value", "uri", "")
		self.assertEquals(
			cursor.execute(*stm).fetchall(),
			cursor.execute("SELECT value FROM uri WHERE value GLOB ?", ("*",)).fetchall()
		)
		self.assertEquals(len(cursor.execute(*stm).fetchall()), len(strings))
		
		# what if the biggest char is the last character of the search prefix?
		prefix = u"h" + unichr(0x10ffff)
		stm = WhereClause.optimize_glob("value", "uri", prefix)
		self.assertEquals(
			cursor.execute(*stm).fetchall(),
			cursor.execute(
				"SELECT value FROM uri WHERE value GLOB ?", (u"%s*" %prefix,)
			).fetchall()
		)
		self.assertEquals(len(cursor.execute(*stm).fetchall()), 1)
		
		# what if the search prefix only contains the biggest char
		prefix = unichr(0x10ffff) + unichr(0x10ffff)
		stm = WhereClause.optimize_glob("value", "uri", prefix)
		self.assertEquals(
			cursor.execute(*stm).fetchall(),
			cursor.execute(
				"SELECT value FROM uri WHERE value GLOB ?", (u"%s*" %prefix,)
			).fetchall()
		)
		self.assertEquals(len(cursor.execute(*stm).fetchall()), 1)
		
		
class FindRelatedUrisTest(_engineTestClass):
	
	def testRelatedForEventsSortRelevancy(self):
		import_events("test/data/apriori_events.js", self.engine)
		result = self.engine.find_related_uris(
			TimeRange.always(), [Event.new_for_values(subject_uri = "i2")], [],
			StorageState.Any, 2, 0)
		self.assertEquals(result, ["i1", "i3"])
		
	def testRelatedForResultTemplateSortRelevancy(self):
		import_events("test/data/apriori_events.js", self.engine)
		result = self.engine.find_related_uris(
			TimeRange.always(), [Event.new_for_values(subject_uri = "i2")],
			[Event.new_for_values(subject_uri = "i1")],
			StorageState.Any, 2, 0)
		self.assertEquals(result, ["i1"])
		
	def testRelatedForNoneSortRelevancy(self):
		import_events("test/data/apriori_events.js", self.engine)
		result = self.engine.find_related_uris(
			TimeRange.always(), [], [],
			StorageState.Any, 2, 0)
		self.assertEquals(result, [])
		
	def testRelatedForActorSortRelevancy(self):
		import_events("test/data/apriori_events.js", self.engine)
		event = Event()
		event.set_actor("firefox")
		result = self.engine.find_related_uris(
			TimeRange.always(), [event], [],
			StorageState.Any, 2, 0)
		logging.debug("************* %s" %result)
		self.assertEquals(result, [])
	
	def testRelatedForEventsSortRecency(self):
		import_events("test/data/apriori_events.js", self.engine)
		result = self.engine.find_related_uris(
			TimeRange.always(), [Event.new_for_values(subject_uri = "i2")], [],
			StorageState.Any, 2, 1)
		self.assertEquals(result, ["i3", "i1",])
	
	def testRelatedForEventsWithManifestation(self):
		import_events("test/data/apriori_events.js", self.engine)
		result = self.engine.find_related_uris(TimeRange.always(),
			[Event.new_for_values(subject_uri = "i4")],
			[Event.new_for_values(subject_manifestation="stfu:File")],
			StorageState.Any,
			10, 0)
		self.assertEquals(result, ["i1", "i3", "i5"])

	
	def testRelatedForMultipleEvents(self):
		import_events("test/data/apriori_events.js", self.engine)
		result = self.engine.find_related_uris(
			TimeRange.always(), [Event.new_for_values(subject_uri = "i1"),
				Event.new_for_values(subject_uri = "i4")], [],
			StorageState.Any, 2, 0),
		self.assertEquals(result, (["i2", "i3", ],))


class MoveEvent(_engineTestClass):
		
	def testSubjectCurrentUri(self):
		event = Event.new_for_values(timestamp=100, subject_uri="http://x")
		ids1 = self.engine.insert_events([event])
		
		subj1 = Subject.new_for_values(uri="http://x", current_uri="http://y")
		event = Event.new_for_values(timestamp=200,
			interpretation=Interpretation.MOVE_EVENT, subjects=[subj1])
		ids2 = self.engine.insert_events([event])
		
		results = self.engine.get_events(ids1 + ids2)
		self.assertEquals(subj1.current_uri, results[0].subjects[0].current_uri)
		self.assertEquals(subj1.current_uri, results[1].subjects[0].current_uri)
		
		subj2 = Subject.new_for_values(uri="http://y", current_uri="http://x")
		event = Event.new_for_values(timestamp=300,
			interpretation=Interpretation.MOVE_EVENT, subjects=[subj2])
		ids3 = self.engine.insert_events([event])
		
		results = self.engine.get_events(ids1 + ids2 + ids3)
		self.assertEquals(subj2.current_uri, results[0].subjects[0].current_uri)
		self.assertEquals(subj1.current_uri, results[1].subjects[0].current_uri)
		self.assertEquals(subj2.current_uri, results[2].subjects[0].current_uri)
	
	def _get_all_timestamp_uri_pairs(self):
		return [(e[0][1], e[1][0][7]) for e in self.engine.find_events(
			TimeRange.always(), [Event.new_for_values(
				interpretation="!"+Interpretation.MOVE_EVENT)],
			StorageState.Any, 0,
			ResultType.LeastRecentEvents)]

	@staticmethod
	def _make_move_event(timestamp, old_uri, new_uri):
		return Event.new_for_values(timestamp=timestamp,
			interpretation=Interpretation.MOVE_EVENT,
			subject_uri=old_uri, subject_current_uri=new_uri)

	def testMoveEventTimeWarp(self):
		# Let's insert some test events...
		s1 = Event.new_for_values(timestamp=100, subject_uri="A")
		s2 = Event.new_for_values(timestamp=200, subject_uri="A")
		s3 = Event.new_for_values(timestamp=300, subject_uri="A")
		s4 = Event.new_for_values(timestamp=400, subject_uri="B")
		s5 = Event.new_for_values(timestamp=500, subject_uri="A")
		self.engine.insert_events([s1, s2, s3, s4, s5])
		self.assertEquals(self._get_all_timestamp_uri_pairs(), [
			(s1.timestamp, "A"), (s2.timestamp, "A"),
			(s3.timestamp, "A"), (s4.timestamp, "B"),
			(s5.timestamp, "A")])
		
		# Now we insert a move event and ensure only older events are affected
		m1 = self._make_move_event(500, "A", "X")
		self.engine.insert_events([m1])
		uris = self._get_all_timestamp_uri_pairs()
		self.assertEquals(uris, [
			(s1.timestamp, "X"), (s2.timestamp, "X"),
			(s3.timestamp, "X"), (s4.timestamp, "B"),
			(s5.timestamp, "A")])
		
		# While we're at it, let's ensure both the cache and the DB are fine
		self.engine._event_cache.clear()
		self.assertEquals(self._get_all_timestamp_uri_pairs(), uris)
		
		# FIXME: We need a lot more evil tests here to fully reproduce bug
		# 778140, but the more advanced cases are left for the next release
		# after 0.8.0.

	def testMoveEventTimeWarp2(self):
		# There is no guarantee events are logged in the correct order.
		# This is why the timestamp has to be checked.....
		import_events("test/data/five_events.js", self.engine)
		import_events("test/data/five_events_ext_move.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0,
			ResultType.LeastRecentCurrentUri)
		self.assertEquals([e.timestamp for e in events],
			["123", "153", "200"])
	
	def testIllegalMoveEvent(self):
		# Incorrect event type with uri != current_uri
		subj = Subject.new_for_values(uri="http://x", current_uri="http://y")
		event = Event.new_for_values(interpretation=Interpretation.ACCESS_EVENT, subjects=[subj])
		self.assertRaises(ValueError, self.engine._insert_event, event)
		
		# Move event with uri == current_uri
		subj = Subject.new_for_values(uri="http://x", current_uri="http://x")
		event = Event.new_for_values(interpretation=Interpretation.MOVE_EVENT, subjects=[subj])
		self.assertRaises(ValueError, self.engine._insert_event, event)


class ResultTypeTest(_engineTestClass):
	
	def testResultTypesMostRecentEvents(self):
		import_events("test/data/five_events.js", self.engine)
		
		# MostRecentEvents - new -> old
		ids = self.engine.find_eventids(
			TimeRange.always(), [], StorageState.Any, 0,
			ResultType.MostRecentEvents)
		events = self.engine.get_events(ids)
		sorted_event_ids = [
			event.id for event in sorted(events,
				cmp=lambda x, y: cmp(int(x.timestamp), int(y.timestamp)),
				reverse=True
			)
		]
		self.assertEquals(list(ids), sorted_event_ids)
		
	def testResultTypesLeastRecentEvents(self):
		import_events("test/data/five_events.js", self.engine)
		
		# LeastRecentEvents - old -> new
		ids = self.engine.find_eventids(
			TimeRange.always(), [], StorageState.Any, 0,
			ResultType.LeastRecentEvents)
		events = self.engine.get_events(ids)
		sorted_event_ids = [
			event.id for event in sorted(events,
				cmp=lambda x, y: cmp(int(x.timestamp), int(y.timestamp)))
		]
		self.assertEquals(list(ids), sorted_event_ids)
	
	def testResultTypesMostPopularActor(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.MostPopularActor)
		self.assertEquals([e[0][4] for e in events], ["firefox", "icedove",
			"frobnicator"])
		self.assertEquals([e.timestamp for e in events], ["119", "114", "105"])
	
	def testResultTypesMostPopularActor2(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange(105,107), [], StorageState.Any, 0, ResultType.MostPopularActor)
		self.assertEquals(len(events), 2)
		self.assertEquals([e[0][4] for e in events], ["firefox", "frobnicator"])
		self.assertEquals([e.timestamp for e in events], ["107", "105"])

	def testResultTypesLeastPopularActor(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.LeastPopularActor)
		self.assertEquals([e[0][4] for e in events], ["frobnicator", "icedove",
			"firefox"])
		self.assertEquals([e.timestamp for e in events], ["105", "114", "119"])

	def testResultTypesLeastPopularActor2(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange(105,107), [], StorageState.Any, 0, ResultType.LeastPopularActor)
		self.assertEquals(len(events), 2)
		self.assertEquals([e[0][4] for e in events], ["frobnicator", "firefox"])
		self.assertEquals([e.timestamp for e in events], ["105", "107"])

	def testResultTypesMostRecentSubject(self):
		import_events("test/data/five_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.MostRecentSubjects)
		self.assertEquals([e.timestamp for e in events],
			["163", "153", "143", "123"])

	def testResultTypesLeastRecentSubject(self):
		import_events("test/data/five_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.LeastRecentSubjects)
		self.assertEquals([e.timestamp for e in events],
			["123", "143", "153", "163"])

	def testResultTypesMostPopularSubject(self):
		import_events("test/data/five_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.MostPopularSubjects)
		self.assertEquals([e.timestamp for e in events],
			["143", "163", "153", "123"])
	
	def testResultTypesLeastPopularSubject(self):
		import_events("test/data/five_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.LeastPopularSubjects)
		self.assertEquals([e.timestamp for e in events],
			["123", "153", "163", "143"])

	def testResultTypesMostRecentCurrentUri(self):
		import_events("test/data/five_events.js", self.engine)
		import_events("test/data/five_events_ext_move.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0,
			ResultType.MostRecentCurrentUri)
		self.assertEquals([e.timestamp for e in events],
			["200", "153", "123"])

	def testResultTypesLeastRecentCurrentUri(self):
		import_events("test/data/five_events.js", self.engine)
		import_events("test/data/five_events_ext_move.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0,
			ResultType.LeastRecentCurrentUri)
		self.assertEquals([e.timestamp for e in events],
			["123", "153", "200"])

	def testResultTypesMostPopularCurrentUri(self):
		import_events("test/data/five_events.js", self.engine)
		import_events("test/data/five_events_ext_move.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0,
			ResultType.MostPopularCurrentUri)
		self.assertEquals([e.timestamp for e in events],
			["200", "123", "153"])
	
	def testResultTypesLeastPopularCurrentUri(self):
		import_events("test/data/five_events.js", self.engine)
		import_events("test/data/five_events_ext_move.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0,
			ResultType.LeastPopularSubjects)
		self.assertEquals([e.timestamp for e in events],
			["123", "153", "163", "200"])

	def testResultTypesMostRecentActor(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.MostRecentActor)
		self.assertEquals([e.timestamp for e in events], ["119", "114", "105"])
	
	def testResultTypesMostRecentActor2(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange(105,107), [], StorageState.Any, 0, ResultType.MostRecentActor)
		self.assertEquals([e.timestamp for e in events], ["107", "105"])
	
	def testResultTypesOldestActorBug641968(self):
		events = [
			Event.new_for_values(timestamp=1, actor="boo", subject_uri="tmp/boo"),
			Event.new_for_values(timestamp=2, actor="boo", subject_uri="home/boo"),
			Event.new_for_values(timestamp=3, actor="bar", subject_uri="tmp/boo"),
			Event.new_for_values(timestamp=4, actor="baz", subject_uri="tmp/boo"),
		]
		self.engine.insert_events(events)
		
		# Get the least recent actors
		ids = self.engine.find_eventids(TimeRange.always(),
			[], StorageState.Any, 0, ResultType.OldestActor)
		self.assertEquals(list(ids), [1, 3, 4])
		
		# Get the least recent actors for "home/boo"
		template = Event.new_for_values(subject_uri="home/boo")
		ids = self.engine.find_eventids(TimeRange.always(),
			[template], StorageState.Any, 0, ResultType.OldestActor)
		self.assertEquals(list(ids), [2])
		
		# Let's also try the same with MostRecentActor... Although there
		# should be no problem here.
		template = Event.new_for_values(subject_uri="home/boo")
		ids = self.engine.find_eventids(TimeRange.always(),
			[template], StorageState.Any, 0, ResultType.OldestActor)
		self.assertEquals(list(ids), [2])
	
	def testResultTypesOldestActor(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(),
			[Event.new_for_values(subject_manifestation="stfu:File")],
			StorageState.Any, 0, ResultType.OldestActor)
		self.assertEquals([e.timestamp for e in events], ["100", "101", "105"])

	def testResultTypesLeastRecentActor(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(),
			[Event.new_for_values(subject_manifestation="stfu:File")],
			StorageState.Any, 0, ResultType.LeastRecentActor)
		self.assertEquals([e.timestamp for e in events], ['105', '114', '119'])
	
	def testResultTypesLeastRecentActor2(self):
		# The same test as before, but this time with fewer events so that
		# it is actually understandable.
		events = [
			Event.new_for_values(timestamp=1, actor="gedit", subject_uri="oldFile"),
			Event.new_for_values(timestamp=2, actor="banshee", subject_uri="oldMusic"),
			Event.new_for_values(timestamp=3, actor="banshee", subject_uri="newMusic"),
			Event.new_for_values(timestamp=4, actor="gedit", subject_uri="newFile"),
		]
		self.engine.insert_events(events)
		
		events = self.engine.find_events(TimeRange.always(),
			[], StorageState.Any, 0, ResultType.LeastRecentActor)
		self.assertEquals([e.timestamp for e in events], ['3', '4'])

	def testResultTypesMostPopularEventOrigin(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0,
			ResultType.MostPopularEventOrigin)
		self.assertEquals([e[0][5] for e in events],
			["origin1", "origin3", "origin2"])
		self.assertEquals([e.timestamp for e in events], ["102", "103", "100"])

	def testResultTypesLeastPopularEventOrigin(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0,
			ResultType.LeastPopularEventOrigin)
		self.assertEquals([e[0][5] for e in events],
			["origin2", "origin3", "origin1"])
		self.assertEquals([e.timestamp for e in events], ["100", "103", "102"])

	def testResultTypesMostRecentEventOrigin(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0,
			ResultType.MostRecentEventOrigin)
		self.assertEquals([e.timestamp for e in events], ["103", "102", "100"])

	def testResultTypesLeastRecentEventOrigin(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0,
			ResultType.LeastRecentEventOrigin)
		self.assertEquals([e.timestamp for e in events], ["100", "102", "103"])

	def testResultTypesMostPopularSubjectOrigin(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.MostPopularOrigin)
		self.assertEquals([e[1][0][3] for e in events], ["file:///tmp", "file:///home",
			"file:///etc"])
		self.assertEquals([e.timestamp for e in events], ["116", "118", "119"])

	def testResultTypesLeastPopularSubjectOrigin(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.LeastPopularOrigin)
		self.assertEquals([e[1][0][3] for e in events], ["file:///etc", "file:///home",
			"file:///tmp"])
		self.assertEquals([e.timestamp for e in events], ["119", "118", "116"])

	def testResultTypesMostRecentSubjectOrigin(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.MostRecentOrigin)
		self.assertEquals([e.timestamp for e in events], ["119", "118", "116"])

	def testResultTypesLeastRecentSubjectOrigin(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.LeastRecentOrigin)
		self.assertEquals([e.timestamp for e in events], ["116", "118", "119"])
		
	def testResultTypesMostRecentMimeType(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.MostRecentMimeType)
		self.assertEquals([e.timestamp for e in events], ['119', '114', '110', '107'])
		
	def testResultTypesLeastRecentMimeType(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.LeastRecentMimeType)
		self.assertEquals([e.timestamp for e in events], ['107', '110', '114', '119'])
		
	def testResultTypesMostPopularMimeType(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.MostPopularMimeType)
		self.assertEquals([e.timestamp for e in events], ['119', '110', '107', '114'])
		
	def testResultTypesLeastPopularMimeType(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.LeastPopularMimeType)
		self.assertEquals([e.timestamp for e in events], ['114', '107', '110', '119'])
		
	def testResultTypesMostRecentSubjectInterpretation(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.MostRecentSubjectInterpretation)
		self.assertEquals([e.timestamp for e in events], ['119', '118', '116', '106'])
		
	def testResultTypesLeastRecentSubjectInterpretation(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.LeastRecentSubjectInterpretation)
		self.assertEquals([e.timestamp for e in events], ['106', '116', '118', '119'])
		
	def testResultTypesMostPopularSubjectInterpretation(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.MostPopularSubjectInterpretation)
		self.assertEquals([e.timestamp for e in events], ['119', '116', '106', '118'])
		
	def testResultTypesLeastPopularSubjectInterpretation(self):
		import_events("test/data/twenty_events.js", self.engine)
		
		events = self.engine.find_events(
			TimeRange.always(), [], StorageState.Any, 0, ResultType.LeastPopularSubjectInterpretation)
		self.assertEquals([e.timestamp for e in events], ['118', '106', '116', '119'])
		

class ZeitgeistEngineBugsTest(_engineTestClass):
	
	def testBug683146(self):
		""" test if different types for timestamp work correctly """
		subjects = [Subject.new_for_values(uri="http://test"),]
		events = [
			Event.new_for_values(timestamp=1300000000, subjects=subjects),
			Event.new_for_values(timestamp=1200000000L, subjects=subjects),
			Event.new_for_values(timestamp=1, subjects=subjects),
		]
		ids = self.engine.insert_events(events)
		result = self.engine.find_eventids(
			(1300000000 - 10, 1300000000 + 10),
			[], StorageState.Any, 10, 0
		)
		self.assertEquals(len(result), 1)
		result = self.engine.find_eventids(
			(1200000000L - 10, 1200000000L + 10),
			[], StorageState.Any, 10, 0
		)
		self.assertEquals(len(result), 1)
		result = self.engine.find_eventids(
			(0, 10),
			[], StorageState.Any, 10, 0
		)
		self.assertEquals(len(result), 1)
	
if __name__ == "__main__":
	unittest.main()
