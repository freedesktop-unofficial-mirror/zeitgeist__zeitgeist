# -.- encoding: utf-8 -.-

# Zeitgeist
#
# Copyright © 2009 Seif Lotfy <seif@lotfy.com>
# Copyright © 2009 Siegfried-Angel Gevatter Pujals <rainct@ubuntu.com>
# Copyright © 2009 Natan Yellin <aantny@gmail.com>
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

from zeitgeist.loggers.zeitgeist_base import DataProvider

try:
	import twitter
except ImportError:
	twitter = None
	print "Twitter support is disabled. Please install python-twitter to enable it."

class TwitterSource(DataProvider):
	"""
	Indexes Twitter statuses.
	"""
	
	def __init__(self):
		# TODO: Store the user's username and password using GNOME Keychain.
		DataProvider.__init__(self, uri="gzg/twitter", name="Twitter")
		self.username = ""
		self.password = ""
		self.comment = " tweets to Twitter"
		
	def get_icon_static(self, icon_size):
		loc = glob.glob(os.path.expanduser("~/.zeitgeist/twitter.png"))
		self.icon = gtk.gdk.pixbuf_new_from_file_at_size(loc[0], -1, int(24))
		
	def get_items_uncached(self):
		# If twitter isn't installed or if we don't have a username and password
		if twitter is None or self.username=="" or self.password=="":
			return
		
		# Connect to twitter, loop over statuses, and create items for each status
		self.api = twitter.Api(username=self.username, password=self.password)
		for status in self.api.GetUserTimeline(count = 500):
			yield {
				"timestamp": tweet.created_at_in_seconds,
				"uri": unicode("http://explore.twitter.com/" + tweet.user.screen_name + "/status/" + str(tweet.id)),
				"name": unicode(tweet.user.name + ":\n" + tweet.text),
				"type": u"Twitter",
				"use": u"tweet",
				"app": u"",
				}

if twitter is not None:
	__datasource__ = TwitterSource()