# -.- coding: utf-8 -.-

# Zeitgeist
#
# Copyright © 2009 Mikkel Kamstrup Erlandsen <mikkel.kamstrup@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import dbus
import dbus.service
from xdg import BaseDirectory
from _zeitgeist.engine.extension import Extension

import logging
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("zeitgeist.blacklist")

CONFIG_FILE = os.path.join(BaseDirectory.save_config_path("zeitgeist"),
                           "blacklist.pickle")

DBUS_OBJECT_PATH = "/org/gnome/zeitgeist/blacklist"
DBUS_INTERFACE = "org.gnome.zeitgeist.Blacklist"
SIG_EVENT="(asaasay)"

class Blacklist(Extension, dbus.service.Object):
	PUBLIC_METHODS = []
	
	def __init__ (self, engine):
		Extension.__init__(self, engine)
		dbus.service.Object.__init__(self, dbus.SessionBus(),
		                             DBUS_OBJECT_PATH)
		if os.path.exists(CONFIG_FILE):
			try:
				self._blacklist = pickle.load(file(CONFIG_FILE))
				log.debug("Loaded blacklist config from %s" % CONFIG_FILE)
			except IOError, e:
				log.warn("Failed to load blacklist config file %s: %s" % (CONFIG_FILE, e))
				self._blacklist = []
		else:
			log.debug("No existing blacklist config found")
			self._blacklist = []
	
	def insert_event_hook(self, event):
		print "EVENT", event
		return event
	
	@dbus.service.method(DBUS_INTERFACE,
	                     in_signature=SIG_EVENT)
	def AddBlacklist(self, event_templates):
		pass
	
