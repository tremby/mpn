#! /usr/bin/python
# -*- coding: utf-8 -*-

"""
Copyright 2007-2011 Olivier Schwander <olivier.schwander@ens-lyon.org>
Copyright 2009-2011 Walther Maldonado <walther.md@gmail.com>
Copyright 2011 Bart Nagel <bart@tremby.net>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""

NAME = "MPNotifier"
VERSION = "1.2~git"
DESCRIPTION = "A lightweight notifier for MPD"
AUTHOR = ", ".join((
		"Olivier Schwander",
		"Wather Maldonado",
		"Bart Nagel",
		))
AUTHOR_EMAIL = ", ".join((
		"olivier.schwander@chadok.info",
		"walther.md@gmail.com",
		"bart@tremby.net",
		))
URL = "https://github.com/tremby/mpn"
LICENSE = "GNU GPLv2+"

import os, sys, cgi, time
import optparse
import re
import socket

import gobject
import gtk, glib
import mpd
import pynotify
import yaml
import signal

import Image
import numpy

MPN = None

def pixmap_dir():
	"""get pixmap location"""
	# FIXME: the absolute paths here only work on Unix and if it was installed 
	# to the default place
	for d in (os.path.join(os.path.dirname(__file__), "pixmaps"),
			"/usr/local/share/pixmaps/mpn",
			"/usr/share/pixmaps/mpn"):
		if os.access(d, os.R_OK):
			return d
	return False
PIXMAP_DIR = pixmap_dir()
assert PIXMAP_DIR

def convert_time(raw):
	"""Format a number of seconds to the hh:mm:ss format"""
	# Converts raw time to 'hh:mm:ss' with leading zeros as appropriate

	hour, minutes, sec = ['%02d' % c for c in (raw/3600,
			(raw%3600)/60, raw%60)]

	if hour == '00':
		if minutes.startswith('0'):
			minutes = minutes[1:]
		return minutes + ':' + sec
	else:
		if hour.startswith('0'):
			hour = hour[1:]
		return hour + ':' + minutes + ':' + sec

def fileexists_insensitive(path):
	"""check if a file exists, case-insensitively for the last component (basename)"""
	searchdir = os.path.dirname(path)
	searchfile = os.path.basename(path).lower()
	if not os.path.exists(searchdir):
		return False
	files = os.listdir(searchdir)
	for file in files:
		if file.lower() == searchfile:
			return os.path.join(searchdir, file)
	return False

def possible_cover_filenames():
	"""return a whole bunch of possible filenames for cover art"""
	PREFIXES = [
		"",
		".",
	]
	MIDDLES = [
		"cover",
		"coverart",
		"frontcover",
		"front",
		"albumart",
		"albumcover",
		"album",
		"folder",
	]
	SUFFIXES = [
		".png",
		".jpg",
	]
	filenames = []
	for pre in PREFIXES:
		for mid in MIDDLES:
			for suf in SUFFIXES:
				filenames.append(pre + mid + suf)
	return filenames

class Notifier:
	"Main class for mpn"
	options = None
	host = "localhost"
	port = 6600
	mpd = None
	status = None
	current = None
	notifier = None
	iterate_handler = None
	title_txt = None
	body_txt = None
	current_image_url = None
	pixbuf_notification = None
	pixbuf_statusicon = None
	re_t = re.compile('(%t)', re.S) #Title
	re_a = re.compile('(%a)', re.S) #Artist
	re_b = re.compile('(%b)', re.S) #alBum
	re_d = re.compile('(%d)', re.S) #song Duration
	re_f = re.compile('(%f)', re.S) #File
	re_n = re.compile('(%n)', re.S) #track Number
	re_p = re.compile('(%p)', re.S) #playlist Position

	def play_cb(self, *args, **kwargs):
		if self.options.debug:
			print "Play"
		if not self.options.once:
			self.mpd.noidle()
			self.mpd.fetch_idle()
		self.mpd.play()
		if self.options.once:
			self.quit()
		self.mpd.send_idle()

	def pause_cb(self, *args, **kwargs):
		if self.options.debug:
			print "Pause"
		if not self.options.once:
			self.mpd.noidle()
			self.mpd.fetch_idle()
		self.mpd.pause()
		if self.options.once:
			self.quit()
		self.mpd.send_idle()

	def prev_cb(self, *args, **kwargs):
		if self.options.debug:
			print "Previous song"
		if not self.options.once:
			self.mpd.noidle()
			self.mpd.fetch_idle()
		self.mpd.previous()
		if self.options.once:
			self.quit()
		self.mpd.send_idle()

	def next_cb(self, *args, **kwargs):
		if self.options.debug:
			print "Next song"
		if not self.options.once:
			self.mpd.noidle()
			self.mpd.fetch_idle()
		self.mpd.next()
		if self.options.once:
			self.quit()
		self.mpd.send_idle()

	def closed_cb(self, *args, **kwargs):
		if self.options.debug:
			print "Notification closed"
		if self.options.once:
			self.quit()

	def get_host(self):
		"""get host name from MPD_HOST env variable"""
		host = os.environ.get('MPD_HOST', 'localhost')
		if '@' in host:
			return host.split('@', 1)
		return host

	def get_port(self):
		"""get host name from MPD_PORT env variable"""
		return os.environ.get('MPD_PORT', 6600)

	def get_title(self, safe=False):
		"""Get the current song title"""
		try:
			title = self.current["title"]
			#In case the file has a multi-title tag
			if type(title) is list:
				title = " - ".join(title)
		except KeyError:
			#Attempt to use filename
			title = self.get_file(safe)
			if title == "":
				title = "???"
		if self.options.debug:
			print "Title :" + title
		if safe:
			return cgi.escape(title)
		return title

	def get_time(self, elapsed=False):
		"""Get current time and total length of the current song"""
		try:
			time = self.status["time"]
			now, length = [int(c) for c in time.split(':')]
			now_time = convert_time(now)
			length_time = convert_time(length)

			if self.options.debug:
				print "Position : " + now_time + " / " + length_time
			if elapsed:
				return now_time
			return length_time
		except KeyError:
			return "unknown"

	def get_tag(self, tag, safe=False):
		"""Get a generic tag from the current data"""
		try:
			data = self.current[tag]
			#In case the file has a multi-value tag
			if type(data) is list:
				data = " / ".join(data)
		except KeyError:
			data = ""
		if self.options.debug:
			print tag + ": " + data
		if safe:
			return cgi.escape(data)
		return data

	def get_file(self, safe=False):
		"""Get the current song file"""
		try:
			file = self.current["file"]
			# Remove left-side path
			file = re.sub(".*"+os.sep, "", file)
			# Remove right-side extension
			file = re.sub("(.*)\..*", "\\1", file)
		except KeyError:
			file = ""
		if self.options.debug:
			print "Filename: " + file
		if safe:
			return cgi.escape(file)
		return file

	def connect(self):
		try:
			self.mpd.connect(self.host, self.port)
			return True
		except mpd.socket.error:
			return False
		# Already connected
		except mpd.ConnectionError:
			return True

	def disconnect(self):
		try:
			self.mpd.disconnect()
			return True
		except mpd.socket.error:
			return False
		except mpd.ConnectionError:
			return False

	def reconnect(self):
		# Ugly, but there's no mpd.isconnected() method
		self.disconnect()
		if self.options.persist:
			self.connect()
			return True
		else:
			print "mpn: Lost connection to server, exiting...\n"
			self.quit(1)
			return False

	def checkstate(self):
		"""Check what has changed, take action"""
		if self.options.debug:
			print "checking state"

		# get state
		try:
			status = self.mpd.status()
			current = self.mpd.currentsong()
		except mpd.ConnectionError, (ce):
			return self.reconnect()
		except socket.error, (se):
			return self.reconnect()

		# if in "once" mode and no song is playing, exit
		if self.options.once and status["state"] == "stop":
			if self.options.debug:
				print "Status is stopped, exiting"
			sys.exit()

		# has status changed
		status_changed = self.status is None or \
				status["state"] != self.status["state"]
		oldstatus = self.status
		self.status = status
		if self.options.debug and status_changed:
			print "status has changed: ", status

		# has song changed
		song_changed = self.current is None or current != self.current
		self.current = current
		if self.options.debug and song_changed:
			print "song has changed: ", current

		# if stopped close the notification
		if status["state"] == "stop":
			self.close_notification()

		# if anything important is different update icons, tooltip etc
		if status_changed or song_changed:
			self.update()

		# if not stopped and the song changed, or was stopped and now not, 
		# display the notification
		if (oldstatus is None or oldstatus["state"] == "stop") \
				and status["state"] != "stop" \
				or song_changed and status["state"] != "stop":
			self.show_notification()

	def close_notification(self):
		try:
			self.notifier.close()
		except glib.GError:
			pass

	def show_notification(self):
		if not self.notifier.show():
			print "Impossible to display the notification"
			return False
		return True

	def update(self):
		if "file" not in self.current:
			title = "no song"
			body = "no song is currently playing"
		else:
			title = self.title_txt
			body = self.body_txt

			# get values with the strings html safe
			title = self.re_t.sub(self.get_title(), title)
			title = self.re_f.sub(self.get_file(), title)
			title = self.re_d.sub(self.get_time(), title)
			title = self.re_a.sub(self.get_tag('artist'), title)
			title = self.re_b.sub(self.get_tag('album'), title)
			title = self.re_n.sub(self.get_tag('track'), title)
			title = self.re_p.sub(self.get_tag('pos'), title)

			body = self.re_t.sub(self.get_title(True), body)
			body = self.re_f.sub(self.get_file(True), body)
			body = self.re_d.sub(self.get_time(), body)
			body = self.re_a.sub(self.get_tag('artist', True), body)
			body = self.re_b.sub(self.get_tag('album', True), body)
			body = self.re_n.sub(self.get_tag('track'), body)
			body = self.re_p.sub(self.get_tag('pos'), body)

		# show title and body for debug
		if self.options.debug:
			print "Title string: " + title
			print "Body string: " + body

		# update tooltip
		if self.options.status_icon and not self.options.once:
			self.status_icon.set_tooltip(re.sub("<.*?>", "", "%s\n%s\n(%s)"
					% (title, body, self.status["state"])))

		# update notification text
		self.notifier.update(title, body)

		# get and process album art
		if "file" not in self.current:
			self.current_image_url = None
		elif self.options.music_path is not None:
			artist = self.get_tag("albumartist")
			if not artist:
				artist = self.get_tag("artist")
			dirname = os.path.dirname(
					os.path.join(self.options.music_path, self.current["file"]))
			for coverfilename in possible_cover_filenames():
				coverpath = fileexists_insensitive(
						os.path.join(dirname, coverfilename))
				if not coverpath:
					self.current_image_url = None
				else:
					if coverpath == self.current_image_url:
						# don't regenerate images if it's the same source image
						break
					self.current_image_url = coverpath
					im = Image.open(coverpath)

					# resize for notification image
					im_notification = im.resize(
							(self.options.icon_size, self.options.icon_size),
							Image.ANTIALIAS)
					self.pixbuf_notification = \
							gtk.gdk.pixbuf_new_from_array(
									numpy.array(im_notification),
									gtk.gdk.COLORSPACE_RGB, 8)

					# resize for status icon and paste on state symbols
					if self.options.status_icon and not self.options.once:
						si_size = self.status_icon.get_size()
						im_statusicon = im.resize((si_size, si_size), 
								Image.ANTIALIAS)
						si = gtk.gdk.pixbuf_new_from_array(
										numpy.array(im_statusicon),
										gtk.gdk.COLORSPACE_RGB, 8)
						if not si.get_has_alpha():
							si = si.add_alpha(True, 0, 0, 0)

						self.pixbuf_statusicon = {}
						p_size = int(si_size * 
								self.options.play_state_icon_size)
						for name in ("stop", "play", "pause"):
							self.pixbuf_statusicon[name] = si.copy()
							if p_size == 0:
								continue
							p = gtk.gdk.pixbuf_new_from_file_at_size(
									"%s/%s.svg" % (PIXMAP_DIR, name),
									p_size, p_size)
							p.composite(self.pixbuf_statusicon[name],
									si_size - p_size, si_size - p_size,
									p_size, p_size,
									si_size - p_size, si_size - p_size,
									1, 1, gtk.gdk.INTERP_NEAREST, 255)
					break

		# update status icon
		if self.options.status_icon and not self.options.once:
			if self.current_image_url is None:
				self.status_icon.set_from_stock(gtk.STOCK_CDROM) # TODO: change this
			else:
				if self.options.debug:
					print "setting icon, state %s" % self.status["state"]
				self.status_icon.set_from_pixbuf(
						self.pixbuf_statusicon[self.status["state"]])

		# update notification icon
		if self.current_image_url is None:
			self.notifier.set_icon_from_pixbuf(
					gtk.gdk.pixbuf_new_from_file_at_size(
							gtk.icon_theme_get_default().lookup_icon(
									self.options.default_icon,
									self.options.icon_size,
									0).get_filename(),
							self.options.icon_size,
							self.options.icon_size))
		else:
			self.notifier.set_icon_from_pixbuf(self.pixbuf_notification)

	def player_cb(self, *args, **kwargs):
		self.mpd.fetch_idle()
		self.checkstate()
		self.mpd.send_idle('player')
		return True

	def run(self):
		"""Launch the iteration"""
		self.checkstate()
		if not self.options.once:
			self.mpd.send_idle('player')
			gobject.io_add_watch(self.mpd, gobject.IO_IN, self.player_cb)

	def quit(self, *args, **kwargs):
		self.close_notification()
		self.disconnect()
		gtk.main_quit()
		try:
			code = kwargs.code
		except AttributeError:
			code = 0
		sys.exit(code)

	def __init__(self, options):
		"""Initialisation of mpd client and pynotify"""
		self.options = options

		# Contents are updated before displaying
		self.notifier = pynotify.Notification("MPN")

		# set closed handler
		self.notifier.connect("closed", self.closed_cb)

		if self.options.status_icon and not self.options.once:
			self.status_icon = gtk.StatusIcon()
			self.status_icon.connect("activate", self.on_activate)
			self.status_icon.connect("popup_menu", self.on_popup_menu)
			self.status_icon.set_from_stock(gtk.STOCK_CDROM) # TODO: change this
			self.status_icon.set_tooltip("MPN")
			self.status_icon.set_visible(True)

			self.notifier.attach_to_status_icon(self.status_icon)

		# param timeout is in seconds
		if self.options.timeout == 0:
			self.notifier.set_timeout(pynotify.EXPIRES_NEVER)
		else:
			self.notifier.set_timeout(1000 * self.options.timeout)

		if self.options.keys:
			self.notifier.add_action("back", "&lt;&lt;", self.prev_cb)
			self.notifier.add_action("forward", "&gt;&gt;", self.next_cb)

		self.title_txt = re.sub("<br>", "\n", self.options.title_format)
		self.body_txt = re.sub("<br>", "\n", self.options.body_format)

		if self.options.debug:
			print "Title format: " + self.title_txt
			print "Body format: " + self.body_txt
		self.mpd = mpd.MPDClient()

		if not self.options.once:
			def handle_signal_usr1(*args, **kwargs):
				self.on_activate()
			signal.signal(signal.SIGUSR1, handle_signal_usr1)

		# listen for kill signals and exit cleanly
		def handle_exit_signal(*args, **kwargs):
			self.quit()
		signal.signal(signal.SIGINT, handle_exit_signal)
		signal.signal(signal.SIGTERM, handle_exit_signal)

		while True:
			# Connection loop in case network is down / resolution fails
			self.host = self.get_host()
			self.port = self.get_port()
			if self.connect():
				break
			print "Failed to connect to server " + self.host
			if not self.options.persist:
				self.quit(1)
			time.sleep(5)

	def on_activate(self, *args, **kwargs):
		if self.status["state"] in ['play', 'pause']:
			self.notifier.show()

	def on_popup_menu(self, icon, button, time):
		menu = gtk.Menu()

		if self.status["state"] == "play":
			w = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PAUSE)
			w.connect("activate", self.pause_cb)
		else:
			w = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PLAY)
			w.connect("activate", self.play_cb)
		# FIXME: presence of play/pause doesn't switch when menu is already open 
		# and state changes
		menu.append(w)
		w = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PREVIOUS)
		w.connect("activate", self.prev_cb)
		menu.append(w)
		w = gtk.ImageMenuItem(gtk.STOCK_MEDIA_NEXT)
		w.connect("activate", self.next_cb)
		menu.append(w)

		menu.append(gtk.SeparatorMenuItem())

		w = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
		w.connect("activate", self.show_about_dialog)
		menu.append(w)
		w = gtk.ImageMenuItem(gtk.STOCK_QUIT)
		w.connect("activate", self.quit)
		menu.append(w)

		menu.show_all()
		menu.popup(None, None, gtk.status_icon_position_menu, button, time, 
				self.status_icon)

	def show_about_dialog(self, widget):
		about_dialog = gtk.AboutDialog()

		about_dialog.set_destroy_with_parent(True)
		about_dialog.set_name("MPN")
		about_dialog.set_version(VERSION)

		authors = []
		for i, n in enumerate(AUTHOR.split(", ")):
			authors.append(n + " <" + AUTHOR_EMAIL.split(", ")[i] + ">")
		about_dialog.set_authors(authors)

		about_dialog.run()
		about_dialog.destroy()

DEFAULT_OPTIONS = {
	"daemon": False,
	"once": False,
	"debug": False,
	"persist": True,
	"timeout": 3,
	"keys": True,
	"default_icon": "gnome-mime-audio",
	"icon_size": 128,
	"music_path": "/var/lib/mpd/music",
	"title_format": "%t",
	"body_format": "<b>%b</b><br><i>%a</i>",
	"status_icon": True,
	"play_state_icon_size": 0.25,
	}

class Application:
	def run(self):
		default_options = {}
		default_options.update(DEFAULT_OPTIONS)
		try:
			stream = file(os.path.expanduser('~/.mpnrc'), 'r')
			default_options.update(yaml.load(stream))
			stream.close()
		except IOError:
			try:
				stream = file('mpnrc', 'r')
				default_options.update(yaml.load(stream))
				stream.close()
			except IOError:
				pass

		# initializate the argument parser
		parser = optparse.OptionParser(version="%prog " + VERSION, 
				description=DESCRIPTION,
				epilog="Defaults shown are after the influence of any "
						"configuration file. Send the USR1 signal to a running MPN "
						"process to display a notification, for instance from a "
						"keyboard shortcut")

		parser.add_option("--show-defaults", action="store_true",
				help="Dump YAML of the default options, suitable for use as a "
						"~/.mpnrc file, and exit")
		parser.add_option("--debug", action="store_true", 
				default=default_options['debug'],
				help="Turn on debugging information")
		parser.add_option("-d", "--daemon", action="store_true", 
				default=default_options['daemon'],
				help="Fork into the background")
		parser.add_option("-p", "--persist", action="store_true", 
				default=default_options['persist'],
				help="Do not exit when connection fails")
		parser.add_option("-t", "--timeout", type="int", metavar="SECS", 
				default=default_options['timeout'],
				help="Notification timeout in secs (use 0 to disable)")
		parser.add_option("-k", "--keys", action="store_true", 
				default=default_options['keys'],
				help="Add Prev/Next buttons to notify window")
		parser.add_option("-o", "--once", action="store_true", 
				default=default_options['once'],
				help="Notify once and exit")
		parser.add_option("-i", "--default-icon", metavar="ICON", 
				default=default_options['default_icon'],
				help="Default icon URI/name (default: %default)")
		parser.add_option("-s", "--icon-size", type="int", metavar="PIXELS", 
				default=default_options['icon_size'],
				help="Size in pixels to which the cover art should be resized "
						"(default: %default)")
		parser.add_option("-m", "--music-path", metavar="PATH", 
				default=default_options["music_path"],
				help="Path to music files, where album art will be looked for "
						"(default: %default)")
		parser.add_option("--status-icon", action="store_true", 
				default=default_options['status_icon'],
				help="Enable status icon")
		parser.add_option("--play-state-icon-size", type="float", 
				default=default_options["play_state_icon_size"],
				help="Size of the play state (pause, stop, play) icon as a "
				"proportion of the status icon size (default: %default, use 0 "
				"for no play state icon")
		parser.add_option("--no-status-icon", dest="status_icon", 
				action="store_false", default=default_options['status_icon'],
				help="Disable status icon")

		group = optparse.OptionGroup(parser,
				"Format related options for the notification display",
				"Supported wildcards:"
				" %t title /"
				" %a artist /"
				" %b album /"
				" %d song duration /"
				" %f base filename /"
				" %n track number /"
				" %p playlist position /"
				" <i> </i> italic text /"
				" <b> </b> bold text /"
				" <br> line break")
		group.add_option("-F", "--title-format", 
				default=default_options['title_format'], metavar="FORMAT",
				help="Format for the notification header")
		group.add_option("-f", "--body-format", 
				default=default_options['body_format'], metavar="FORMAT",
				help="Format for the notification body")
		parser.add_option_group(group)

		# parse the commandline
		(options, _) = parser.parse_args()

		# dump default options if requested
		if options.show_defaults:
			print yaml.dump(DEFAULT_OPTIONS, default_flow_style=False)
			sys.exit()

		# initializate the notifier
		if not pynotify.init('mpn'):
			print "Failed to initialize pynotify module"
			sys.exit(1)

		MPN = Notifier(options=options)

		# fork if necessary
		if options.daemon and not options.debug:
			if os.fork() != 0:
				sys.exit()

		# run the notifier
		try:
			MPN.run()
			# We only need the main loop when iterating or if keys are enabled
			if options.keys or not options.once:
				gtk.main()
		except KeyboardInterrupt:
			pass

if __name__ == "__main__":
	app = Application()
	app.run()
