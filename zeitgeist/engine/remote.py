# -.- encoding: utf-8 -.-

# Zeitgeist
#
# Copyright © 2009 Siegfried-Angel Gevatter Pujals <rainct@ubuntu.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import dbus
import dbus.service
import logging

from zeitgeist.engine.engine import get_default_engine
from zeitgeist.dbusutils import dictify_data, sig_plain_data
from zeitgeist.singleton import SingletonApplication

_engine = get_default_engine()

class RemoteInterface(SingletonApplication):
	
	# Initialization
	
	def __init__(self, start_dbus=True, mainloop=None):
		SingletonApplication.__init__(self, bus_name = "org.gnome.zeitgeist",
											path_name = "/org/gnome/zeitgeist")
		self._mainloop = mainloop
	
	# Reading stuff
	
	@dbus.service.method("org.gnome.zeitgeist",
						in_signature="as", out_signature="a"+sig_plain_data)
	def GetItems(self, uris):
		"""Get items by uri
		
		:param uris: list of uris
		:type uris: list of strings
		:returns: list of items
		:rtype: list of tuples presenting an :ref:`item-label`
		"""
		return map(_engine.get_item, uris)
	
	@dbus.service.method("org.gnome.zeitgeist",
						in_signature="iiibsaa{sv}", out_signature="a"+sig_plain_data)
	def FindEvents(self, min_timestamp, max_timestamp, limit,
			sorting_asc, mode, filters):
		"""Search for Items which matches different criterias
		
		:param min_timestamp: search for events beginning after this timestamp
		:type min_timestamp: integer
		:param max_timestamp: search for events beginning before this timestamp;
			``max_timestamp`` equals ``0`` means indefinite time
		:type max_timestamp: integer
		:param limit: limit the number of returned items;
			``limit`` equals ``0`` returns all matching items
		:type limit: integer
		:param sorting_asc: sort result in ascending order of timestamp, otherwise descending
		:type sorting_asc: boolean
		:param mode: The first mode returns all events, the second one only returns
			the last event when items are repeated and the ``mostused`` mode
			is like ``item`` but returns the results sorted by the number of
			events.
		:type mode: string, either ``event``, ``item`` or ``mostused``
		:param filters: list of filter, multiple filters are connected by an ``OR`` condition
		:type filters: list of tuples presenting a :ref:`filter-label`
		:returns: list of items
		:rtype: list of tuples presenting an :ref:`item-label`
		"""
		# filters is a list of dicts, where each dict can have the following items:
		#   text_name: <str>
		#   text_uri: <str>
		#   tags: <list> of <str>
		#   mimetypes: <list> or <str>
		#   source: <str>
		#   content: <str>
		#   bookmarked: <bool> (True means bookmarked items, and vice versa
		return _engine.find_events(min_timestamp, max_timestamp, limit,
			sorting_asc, mode, filters, False)
	
	@dbus.service.method("org.gnome.zeitgeist",
						in_signature="iisaa{sv}", out_signature="a"+sig_plain_data)
	def CountEvents(self, min_timestamp, max_timestamp, mode, filters):
		"""This method is similar to ``FindEvents()``, but returns all results
		in ascending order
		
		:param min_timestamp: search for events beginning after this timestamp
		:type min_timestamp: integer
		:param max_timestamp: search for events beginning before this timestamp;
			``max_timestamp`` equals ``0`` means indefinite time
		:type max_timestamp: integer
		:param mode: The first mode returns all events, the second one only returns
			the last event when items are repeated and the ``mostused`` mode
			is like ``item`` but returns the results sorted by the number of
			events.
		:type mode: string, either ``event``, ``item`` or ``mostused``
		:param filters: list of filter, multiple filters are connected by an ``OR`` condition
		:type filters: list of tuples presenting a :ref:`filter-label`
		:returns: list of items
		:rtype: list of tuples presenting an :ref:`item-label`
		"""
		return _engine.find_events(min_timestamp, max_timestamp, 0, True,
			mode, filters, True)
	
	@dbus.service.method("org.gnome.zeitgeist",
						in_signature="sii", out_signature="i")
	def GetCountForUri(self, uri, start, end):
		return _engine.get_count_for_item(self, uri, start, end)
	
	@dbus.service.method("org.gnome.zeitgeist",
						in_signature="i", out_signature="i")
	def GetLastTimestamp(self, uri):
		"""Gets the timestamp of the most recent item in the database. If
		``uri`` is not empty, it will give the last timestamp for the
		indicated URI. Returns 0 if there are no items in the database.
		
		:param uri: URI of item
		:type uri: string
		:returns: timestamp of most recent item
		:rtype: Integer
		"""
		return _engine.get_last_timestamp(uri)
	
	@dbus.service.method("org.gnome.zeitgeist",
						in_signature="siii", out_signature="a(si)")
	def GetTags(self, name_filter, amount, min_timestamp, max_timestamp):
		"""Returns a list containing tuples with the name and the number of
		occurencies of the tags matching ``name_filter``, or all existing
		tags in case it's empty, sorted from most used to least used. ``amount``
		can base used to limit the amount of results.
		
		Use ``min_timestamp`` and ``max_timestamp`` to limit the time frames you
		want to consider.
		
		:param name_filter: 
		:type name_filter: string
		:param amount: max amount of returned elements, ``amount`` equals ``0``
			means the result not beeing limited
		:type amount: integer
		:param min_timestamp:
		:type min_timestamp: Integer
		:param max_timestamp:
		:type max_timestamp: Integer
		:returns: list of tuple containing the name and number of occurencies
		:rtype: list of tuples
		"""
		return _engine.get_tags(name_filter, amount, min_timestamp, max_timestamp)
	
	@dbus.service.method("org.gnome.zeitgeist",
						in_signature="s", out_signature="a"+sig_plain_data)
	def GetRelatedItems(self, item_uri):
		# FIXME: Merge this into FindEvents so that matches can be
		# filtered?
		return _engine.get_related_items(item_uri)
	
	@dbus.service.method("org.gnome.zeitgeist",
						in_signature="s", out_signature="i")
	def GetLastInsertionDate(self, application):
		"""Returns the timestamp of the last item which was inserted
		related to the given ``application``. If there is no such record,
		0 is returned.
		
		:param application: application to query for
		:type application: string
		:returns: timestamp of last insertion date
		:rtype: integer
		"""
		return _engine.get_last_insertion_date(application)
	
	@dbus.service.method("org.gnome.zeitgeist",
						in_signature="", out_signature="as")
	def GetTypes(self):
		"""Returns a list of all different types in the database.
		
		:returns: list of types
		:rtype: list of strings
	   	"""
		return _engine.get_types()
	
	# Writing stuff
	
	@dbus.service.method("org.gnome.zeitgeist",
						in_signature="a"+sig_plain_data, out_signature="i")
	def InsertItems(self, items_list):
		"""Inserts an item into the database. Returns ``1`` if any item
		has been added successfully or ``0`` otherwise
		
		:param item_list: list of items to be inserted in the database
		:type item_list: list of tuples presenting an :ref:`item-label`
		:returns: ``1`` on success, ``0`` otherwise
		:rtype: Integer
		"""
		result = _engine.insert_items([dictify_data(x) for x in items_list])
		return result if (result and self.EventsChanged()) else 0
	
	@dbus.service.method("org.gnome.zeitgeist",
						in_signature="a"+sig_plain_data, out_signature="")
	def UpdateItems(self, item_list):
		"""Update items in the database
		
		:param item_list: list of items to be inserted in the database
		:type item_list: list of tuples presenting an :ref:`item-label`
		"""
		_engine.update_items([dictify_data(x) for x in item_list])
		self.EventsChanged()
	
	@dbus.service.method("org.gnome.zeitgeist",
						in_signature="as", out_signature="")
	def DeleteItems(self, uris):
		"""Delete items from the database
		
		:param uris: list of uris representing an item
		:type uris: list of strings
		"""
		_engine.delete_items(uris)
		self.EventsChanged()
	
	# Signals and signal emitters
	
	@dbus.service.signal("org.gnome.zeitgeist")
	def EventsChanged(self):
		"""This Signal is emmitted whenever one or more items have been changed"""
		return True
	
	@dbus.service.signal("org.gnome.zeitgeist")
	def EngineStart(self):
		"""This signal is emmitted once the engine successfully started and
		is ready to process requests
		"""
		return True
	
	@dbus.service.signal("org.gnome.zeitgeist")
	def EngineExit(self):
		return True
	
	# Commands
	
	@dbus.service.method("org.gnome.zeitgeist")
	def Quit(self):
		"""Terminate the running RemoteInterface process"""
		if self._mainloop:
			self._mainloop.quit()
