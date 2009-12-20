#!/usr/bin/python
# -.- coding: utf-8 -.-

# Update python path to use local zeitgeist module
import sys
import os
import unittest
import dbus

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from zeitgeist.datamodel import *
from testutils import RemoteTestCase

class BlacklistTest(RemoteTestCase):
	
	def __init__(self, methodName):
		super(BlacklistTest, self).__init__(methodName)
		self.blacklist = None
	
	def setUp(self):
		# We set up the connection lazily in order to wait for the
		# engine to come up
		super(BlacklistTest, self).setUp()
		obj = dbus.SessionBus().get_object("org.gnome.zeitgeist.Engine",
		                                              "/org/gnome/zeitgeist/blacklist")
		self.blacklist = dbus.Interface(obj, "org.gnome.zeitgeist.Blacklist")
	
	def testClear(self):
		self.blacklist.SetBlacklist([])
		empty = self.blacklist.GetBlacklist()
		self.assertEquals(empty, [])
		
	def testSetOne(self):
		orig = Event.new_for_values(interpretation=Interpretation.OPEN_EVENT,
		                            subject_uri="http://nothingtoseehere.gov")
		self.blacklist.SetBlacklist([orig])
		result = map(Event, self.blacklist.GetBlacklist())
		
		self.assertEquals(len(result), 1)
		result = result[0]
		self.assertEquals(result.manifestation, "")
		self.assertEquals(result.interpretation, Interpretation.OPEN_EVENT)
		self.assertEquals(len(result.subjects), 1)
		self.assertEquals(result.subjects[0].uri, "http://nothingtoseehere.gov")
		self.assertEquals(result.subjects[0].interpretation, "")
		
if __name__ == "__main__":
	unittest.main()
