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

# utility
# ------------------------------------------------------------------------------

def convert_time(raw):
	"""Format a number of seconds to the hh:mm:ss format"""
	# Converts raw time to "hh:mm:ss" with leading zeros as appropriate

	hour, minutes, sec = ["%02d" % c for c in (raw/3600,
			(raw%3600)/60, raw%60)]

	if hour == "00":
		if minutes.startswith("0"):
			minutes = minutes[1:]
		return minutes + ":" + sec
	else:
		if hour.startswith("0"):
			hour = hour[1:]
		return hour + ":" + minutes + ":" + sec

def fileexists_insensitive(path):
	"""check if a file exists, case-insensitively for the last component 
	(basename)"""
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

# svg
# ------------------------------------------------------------------------------

def make_svg(icon, s):
	header = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
			<svg xmlns:svg="http://www.w3.org/2000/svg" 
					xmlns="http://www.w3.org/2000/svg" version="1.1" 
					xmlns:xlink="http://www.w3.org/1999/xlink" 
					width="%s" 
					height="%s">\n""" % (s, s)
	footer = "</svg>\n"

	if icon == "cd":
		# main radii
		r = [x * s for x in [0.5, 0.05, 0.48, 0.13]]

		# start definitions block
		body = "<defs>\n"

		# mask for the whole CD
		body = body + """
				<mask id="cd">
					<circle cx="0" cy="0" r="%f" fill="white"/>
					<circle cx="0" cy="0" r="%f" fill="black"/>
				</mask>""" % (r[0], r[1])

		# mask for the shiny area
		body = body + """
				<mask id="shinybit">
					<circle cx="0" cy="0" r="%f" fill="white"/>
					<circle cx="0" cy="0" r="%f" fill="black"/>
				</mask>""" % (r[2], r[3])

		# gaussian blur for the shine
		body = body + """
				<filter id="blur">
					<feGaussianBlur stdDeviation="%f"/>
				</filter>""" % (0.05*s)

		# shape for the shine
		body = body + """<path id="shine" d="m %f,%f %f,0 %f,%f %f,0 z"/>\n""" \
				% (-s, -s, 2*s, -2*s, 2*s, 2*s)

		# gradient for gloss
		body = body + """
				<linearGradient id="whitefade"
						x1="0" y1="0" x2="0" y2="100%%">
					<stop offset="0%%" stop-color="white" stop-opacity="0"/>
					<stop offset="100%%" stop-color="white" stop-opacity="1"/>
				</linearGradient>\n"""

		# end definitions block
		body = body + "</defs>\n"

		# group masking to the CD's shape and shifting everything into view so 
		# 0,0 can be the centre
		body = body + """<g mask="url(#cd)"
				transform="translate(%f, %f)">\n""" % (0.5*s, 0.5*s)

		# transparent outside, only visible when large
		body = body + """<circle cx="0" cy="0" r="%f"
				fill="none" stroke="#d0d0d0" stroke-width="%f"
				opacity="0.4"/>""" % (0.5*s, 0.3*s)

		# shiny bit
		body = body + """
				<g mask="url(#shinybit)">
					<circle cx="0" cy="0" r="%f" fill="#b3b3b3"/>
					<g filter="url(#blur)">
						<use xlink:href="#shine" fill="white" opacity="0.9"
								transform="rotate(30) scale(0.3, 1)"/>
						<g opacity="0.75">
							<use xlink:href="#shine" fill="purple"
									transform="rotate(145) scale(0.15, 1)"/>
							<use xlink:href="#shine" fill="blue"
									transform="rotate(135) scale(0.15, 1)"/>
							<use xlink:href="#shine" fill="cyan"
									transform="rotate(125) scale(0.15, 1)"/>
							<use xlink:href="#shine" fill="lime"
									transform="rotate(115) scale(0.15, 1)"/>
							<use xlink:href="#shine" fill="yellow"
									transform="rotate(105) scale(0.15, 1)"/>
							<use xlink:href="#shine" fill="red"
									transform="rotate(95) scale(0.1, 1)"/>
						</g>
					</g>
				</g>\n""" % (r[0])

		# transparent centre bit
		body = body + """<circle cx="0" cy="0" r="%f"
				fill="#4b4b4b"
				opacity="0.30"/>""" % (0.16*s)
		body = body + """<circle cx="0" cy="0" r="%f"
				fill="none" stroke="#2b2b2b" stroke-width="1"
				opacity="0.15"/>""" % (0.105*s)
		body = body + """<circle cx="0" cy="0" r="%f"
				fill="none" stroke="#2b2b2b" stroke-width="1"
				opacity="0.15"/>""" % (0.07*s)

		# gloss
		body = body + """<path
				d="m %f,%f
					C %f,%f %f,%f %f,%f
					C %f,%f %f,%f %f,%f
					C %f,%f %f,%f %f,%f
					V %f H %f z"
				fill="url(#whitefade)" opacity="0.15"/>\n""" % (
						-0.5*s, 0.05*s, # start point just below left centre
						-0.45*s, 0, -0.35*s, -0.03*s, -0.2*s, -0.03*s,
						-0.03*s, -0.03*s, 0.03*s, 0.03*s, 0.2*s, 0.03*s,
						0.35*s, 0.03*s, 0.45*s, 0, 0.5*s, -0.05*s,
						-0.5*s, -0.5*s, # corners
						)

		# 1 pixel light rim
		body = body + """<circle cx="0" cy="0" r="%f"
				fill="none" stroke="#e0e0e0" stroke-width="4"
				opacity="0.8"/>""" % (0.5*s)

		# 1 pixel dark outline
		body = body + """<circle cx="0" cy="0" r="%f"
				fill="none" stroke="#606060" stroke-width="2"
				opacity="0.7"/>""" % (0.5*s)
		body = body + """<circle cx="0" cy="0" r="%f"
				fill="none" stroke="#606060" stroke-width="2"
				opacity="0.3"/>""" % (r[1])

		# end group
		body = body + "</g>\n"
	else:
		# usable size (size minus 1-pixel outline on each side)
		u = s - 2

		# size of pause bars
		if u % 3 == 0:
			pw = u / 3
		elif u % 3 == 1:
			if u == 4:
				pw = 1 # edge case to keep gap visible
			else:
				pw = u / 3 + 1
		else:
			pw = u / 3 + 1

		paths = {
				"play": [
						[(1, 1), (0, u), (u, -u/2.0)],
						],
				"stop": [
						[(1, 1), (0, u), (u, 0), (0, -u)],
						],
				"pause": [
						[(1, 1), (0, u), (pw, 0), (0, -u)],
						[(u+1, 1), (0, u), (-pw, 0), (0, -u)],
						],
				}

		body = ""
		for path in paths[icon]:
			# outline
			body = """%s<path d="m %s z"
					fill="none" stroke="black" stroke-width="2" opacity="0.8"/>""" \
					% (body, " ".join("%s,%s" % p for p in path))

			# fill
			body = """%s<path d="m %s z"
					fill="white" stroke="none" opacity="0.8"/>""" \
					% (body, " ".join("%s,%s" % p for p in path))

	return "%s%s%s" % (header, body, footer)

def svg_to_pixbuf(svg):
	pl = gtk.gdk.PixbufLoader("svg")
	pl.write(svg)
	pl.close()
	return pl.get_pixbuf()

# main class
# ------------------------------------------------------------------------------

class Notifier:
	"Main class for mpn"
	options = None
	host = "localhost"
	port = 6600
	mpd = None
	status = None
	current = None
	notifier = None
	title_txt = None
	body_txt = None
	current_image_url = None
	pixbuf_notification = None
	pixbuf_statusicon = None
	status_icon_size = None
	re = {}
	menu = None
	menu_play = None
	menu_pause = None
	menu_stop = None

	# callbacks
	# --------------------------------------------------------------------------

	def _mpd_command(self, command):
		if self.options.debug:
			print "mpd command: %s" % command
		if not self.options.once:
			try:
				self.mpd.noidle()
				self.mpd.fetch_idle()
			except (mpd.ConnectionError, mpd.socket.error):
				self.reconnect()
		while True:
			try:
				command()
				self.mpd.send_idle("player")
				break
			except (mpd.ConnectionError, mpd.socket.error):
				self.reconnect()
		if self.options.once:
			self.quit()
		return True
	def play_cb(self, *args, **kwargs):
		self._mpd_command(self.mpd.play)
	def pause_cb(self, *args, **kwargs):
		self._mpd_command(self.mpd.pause)
	def stop_cb(self, *args, **kwargs):
		self._mpd_command(self.mpd.stop)
	def prev_cb(self, *args, **kwargs):
		self._mpd_command(self.mpd.previous)
	def next_cb(self, *args, **kwargs):
		self._mpd_command(self.mpd.next)

	def closed_cb(self, *args, **kwargs):
		if self.options.debug:
			print "Notification closed"
		if self.options.once:
			self.quit()

	def player_cb(self, *args, **kwargs):
		try:
			self.mpd.fetch_idle()
		except (mpd.ConnectionError, mpd.socket.error):
			self.reconnect()
		while True:
			try:
				self.checkstate()
				self.mpd.send_idle("player")
				return True
			except (mpd.ConnectionError, mpd.socket.error):
				self.reconnect()

	def on_activate(self, *args, **kwargs):
		"""Status icon was clicked"""
		if self.status["state"] in ["play", "pause"]:
			self.notifier.show()

	def on_popup_menu(self, icon, button, time):
		"""Status icon was right-clicked"""
		self.update_menu()
		self.menu.popup(None, None, gtk.status_icon_position_menu, button, time, 
				self.status_icon)

	def on_status_icon_size_changed(self, *args, **kwargs):
		"""Status icon's size changed"""
		self.update()

	def show_about_dialog(self, widget):
		"""About dialog requested"""
		about_dialog = gtk.AboutDialog()

		about_dialog.set_destroy_with_parent(True)
		about_dialog.set_name("MPN")
		about_dialog.set_version(VERSION)

		about_dialog.set_logo(svg_to_pixbuf(make_svg("cd", 196)))

		authors = []
		for i, n in enumerate(AUTHOR.split(", ")):
			authors.append(n + " <" + AUTHOR_EMAIL.split(", ")[i] + ">")
		about_dialog.set_authors(authors)

		about_dialog.run()
		about_dialog.destroy()

	# environment variables
	# --------------------------------------------------------------------------

	def get_host(self):
		"""get host name from MPD_HOST env variable"""
		host = os.environ.get("MPD_HOST", "localhost")
		if "@" in host:
			return host.split("@", 1)
		return host

	def get_port(self):
		"""get host name from MPD_PORT env variable"""
		return os.environ.get("MPD_PORT", 6600)

	# current status
	# --------------------------------------------------------------------------

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
			now, length = [int(c) for c in time.split(":")]
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

	# mpd connection
	# --------------------------------------------------------------------------

	def connect(self):
		while True:
			host = self.get_host()
			port = self.get_port()
			try:
				self.mpd.connect(self.get_host(), self.get_port())
				return True
			except mpd.socket.error:
				print "Failed to connect to %s:%s: socket error" % (host, port)
			except mpd.ConnectionError:
				print "Failed to connect to %s:%s: connection error" % (host, port)
			if not self.options.persist:
				return False
			time.sleep(5)

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
		if not self.options.persist:
			print "Lost connection to server, exiting..."
			self.quit(code=1)
		self.connect()

	# when idle calls back find out what changed
	# --------------------------------------------------------------------------

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

	# show or close the notification
	# --------------------------------------------------------------------------

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

	# image manipulation
	# --------------------------------------------------------------------------

	def generate_notification_image(self):
		if self.current_image_url is None:
			self.pixbuf_notification = svg_to_pixbuf(
					make_svg("cd", self.options.icon_size))
		else:
			self.pixbuf_notification = gtk.gdk.pixbuf_new_from_array(
					numpy.array(Image.open(self.current_image_url).resize(
							(self.options.icon_size, self.options.icon_size),
							Image.ANTIALIAS)),
					gtk.gdk.COLORSPACE_RGB, 8)

	def generate_status_image(self):
		si_size = self.status_icon.get_size()
		self.status_icon_size = si_size

		if self.current_image_url is None:
			si = svg_to_pixbuf(make_svg("cd", si_size))
		else:
			si = gtk.gdk.pixbuf_new_from_array(
					numpy.array(Image.open(self.current_image_url).resize(
							(si_size, si_size), Image.ANTIALIAS)),
					gtk.gdk.COLORSPACE_RGB, 8)

		if not si.get_has_alpha():
			si = si.add_alpha(True, 0, 0, 0)

		self.pixbuf_statusicon = {}
		p_size = int(round(si_size * self.options.play_state_icon_size))
		for name in ("stop", "play", "pause"):
			self.pixbuf_statusicon[name] = si.copy()
			if p_size == 0:
				continue

			p = svg_to_pixbuf(make_svg(name, p_size))
			p.composite(self.pixbuf_statusicon[name],
					si_size - p_size, si_size - p_size,
					p_size, p_size,
					si_size - p_size, si_size - p_size,
					1, 1, gtk.gdk.INTERP_NEAREST, 255)

	# take action when something we care about has changed
	# --------------------------------------------------------------------------

	def update(self):
		"""Something we care about has changed -- take necessary actions"""
		if "file" not in self.current:
			title = "no song"
			body = "no song is currently playing"
		else:
			title = self.title_txt
			body = self.body_txt

			# perform placeholder substitutions on title and body
			for x in self.re.itervalues():
				if len(x) < 3:
					args = ()
				else:
					args = x[2]
				title = x[0].sub(x[1](*args), title)
				body = x[0].sub(x[1](*args), body)

		# show title and body for debug
		if self.options.debug:
			print "Title string: " + title
			print "Body string: " + body

		if self.options.status_icon and not self.options.once:
			# update tooltip
			self.status_icon.set_tooltip(re.sub("<.*?>", "", "%s\n%s\n(%s)"
					% (title, body, self.status["state"])))

			# update menu
			self.update_menu()

		# update notification text
		self.notifier.update(title, body)

		# update images
		images_changed = self.regenerate_images_if_necessary()

		# update notification icon
		if images_changed:
			self.notifier.set_icon_from_pixbuf(self.pixbuf_notification)

		# update status icon (not only when images changed -- play state may 
		# have changed)
		if self.options.status_icon and not self.options.once:
			if self.options.debug:
				print "setting icon, state %s" % self.status["state"]
			self.status_icon.set_from_pixbuf(
					self.pixbuf_statusicon[self.status["state"]])

	def regenerate_images_if_necessary(self):
		"""Regenerate images for notification and status icon if necessary, 
		return true if anything changed"""

		coverpath = None
		if "file" in self.current and self.options.music_path is not None:
			dirname = os.path.dirname(
					os.path.join(self.options.music_path, self.current["file"]))
			for f in possible_cover_filenames():
				f = fileexists_insensitive(os.path.join(dirname, f))
				if f:
					coverpath = f
					break

		generate_notification = False
		generate_status = False

		if self.pixbuf_notification is None \
				or coverpath != self.current_image_url:
			generate_notification = True
			generate_status = True
		if self.options.status_icon and not self.options.once and \
				self.status_icon_size != self.status_icon.get_size():
			generate_status = True
		if not self.options.status_icon or self.options.once:
			generate_status = False

		self.current_image_url = coverpath

		if generate_notification:
			self.generate_notification_image()
		if generate_status:
			self.generate_status_image()

		return generate_notification or generate_status

	def update_menu(self):
		"""Hide/show the play, pause and stop buttons in the menu depending on 
		play state"""
		if self.status["state"] == "play":
			self.menu_pause.show()
			self.menu_play.hide()
		else:
			self.menu_pause.hide()
			self.menu_play.show()
		if self.status["state"] == "stop":
			self.menu_stop.hide()
		else:
			self.menu_stop.show()

	# start and stop MPN
	# --------------------------------------------------------------------------

	def run(self):
		"""Launch the first iteration"""
		if not self.connect():
			self.quit(code=1)
		self.checkstate()
		if not self.options.once:
			self.mpd.send_idle("player")
			gobject.io_add_watch(self.mpd, gobject.IO_IN, self.player_cb)
		# We only need the main loop when iterating or if keys are enabled
		if self.options.keys or not self.options.once:
			gtk.main()

	def quit(self, *args, **kwargs):
		"""Shut down cleanly"""
		self.close_notification()
		self.disconnect()
		try:
			gtk.main_quit()
		except RuntimeError:
			pass # main wasn't running yet
		try:
			code = kwargs.code
		except AttributeError:
			code = 0
		sys.exit(code)

	# initialize MPN
	# --------------------------------------------------------------------------

	def __init__(self, options):
		"""Initialisation of mpd client and pynotify"""
		self.options = options

		# regular expressions
		self.re = {
				"t": (re.compile("(%t)", re.S), self.get_title),
				"a": (re.compile("(%a)", re.S), self.get_tag, ("artist",)),
				"b": (re.compile("(%b)", re.S), self.get_tag, ("album",)),
				"d": (re.compile("(%d)", re.S), self.get_time),
				"f": (re.compile("(%f)", re.S), self.get_file),
				"n": (re.compile("(%n)", re.S), self.get_tag, ("track",)),
				"p": (re.compile("(%p)", re.S), self.get_tag, ("pos",)),
				}

		# Contents are updated before displaying
		self.notifier = pynotify.Notification("MPN")

		# set closed handler
		self.notifier.connect("closed", self.closed_cb)

		if self.options.status_icon and not self.options.once:
			# status icon
			self.status_icon = gtk.StatusIcon()
			self.status_icon.connect("activate", self.on_activate)
			self.status_icon.connect("popup_menu", self.on_popup_menu)
			self.status_icon.connect("size_changed",
					self.on_status_icon_size_changed)
			self.status_icon.set_from_pixbuf(
					svg_to_pixbuf(make_svg("cd", self.status_icon.get_size())))
			self.status_icon.set_tooltip("MPN")
			self.status_icon.set_visible(True)

			self.notifier.attach_to_status_icon(self.status_icon)

			# popup menu
			self.menu = gtk.Menu()

			w = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PAUSE)
			w.connect("activate", self.pause_cb)
			self.menu.append(w)
			self.menu_pause = w

			w = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PLAY)
			w.connect("activate", self.play_cb)
			self.menu.append(w)
			self.menu_play = w

			w = gtk.ImageMenuItem(gtk.STOCK_MEDIA_STOP)
			w.connect("activate", self.stop_cb)
			self.menu.append(w)
			self.menu_stop = w

			w = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PREVIOUS)
			w.connect("activate", self.prev_cb)
			self.menu.append(w)

			w = gtk.ImageMenuItem(gtk.STOCK_MEDIA_NEXT)
			w.connect("activate", self.next_cb)
			self.menu.append(w)

			self.menu.append(gtk.SeparatorMenuItem())

			w = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
			w.connect("activate", self.show_about_dialog)
			self.menu.append(w)

			w = gtk.ImageMenuItem(gtk.STOCK_QUIT)
			w.connect("activate", self.quit)
			self.menu.append(w)

			self.menu.show_all()

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

# application class
# ------------------------------------------------------------------------------

class Application:
	def run(self):
		default_options = {}
		default_options.update(DEFAULT_OPTIONS)
		try:
			stream = file(os.path.expanduser("~/.mpnrc"), "r")
			default_options.update(yaml.load(stream))
			stream.close()
		except IOError:
			try:
				stream = file("mpnrc", "r")
				default_options.update(yaml.load(stream))
				stream.close()
			except IOError:
				pass

		# initializate the argument parser
		parser = optparse.OptionParser(version="%prog " + VERSION, 
				description=DESCRIPTION,
				epilog="Defaults shown are after the influence of any "
						"configuration file. Negative options exist for each "
						"of the booleans starting with \"--no-\", for instance "
						"--no-status-icon. Send the USR1 signal to a running "
						"MPN process to display a notification, for instance "
						"from a keyboard shortcut.")

		def d(option):
			return "(default: %sset)" % \
					("" if default_options[option] else "un")

		parser.add_option("--show-defaults", action="store_true",
				help="Dump YAML of the default options, suitable for use as "
						"a ~/.mpnrc file, and exit")
		parser.add_option("--debug", action="store_true", 
				default=default_options["debug"],
				help="Turn on debugging information %s" % d("debug"))
		parser.add_option("--no-debug", dest="debug", action="store_false", 
				help=optparse.SUPPRESS_HELP)
		parser.add_option("-d", "--daemon", action="store_true", 
				default=default_options["daemon"],
				help="Fork into the background %s" % d("daemon"))
		parser.add_option("--no-daemon", dest="daemon", action="store_false", 
				help=optparse.SUPPRESS_HELP)
		parser.add_option("-p", "--persist", action="store_true", 
				default=default_options["persist"],
				help="Do not exit when connection fails %s" % d("persist"))
		parser.add_option("--no-persist", dest="persist", action="store_false", 
				help=optparse.SUPPRESS_HELP)
		parser.add_option("-t", "--timeout", type="int", metavar="SECS", 
				default=default_options["timeout"],
				help="Notification timeout in secs (default %default, use 0 to "
						"disable)")
		parser.add_option("-k", "--keys", action="store_true", 
				default=default_options["keys"],
				help="Add Prev/Next buttons to notify window %s" % d("keys"))
		parser.add_option("--no-keys", dest="keys", action="store_false", 
				help=optparse.SUPPRESS_HELP)
		parser.add_option("-o", "--once", action="store_true", 
				default=default_options["once"],
				help="Notify once and exit %s" % d("once"))
		parser.add_option("--no-once", dest="once", action="store_false", 
				help=optparse.SUPPRESS_HELP)
		parser.add_option("-s", "--icon-size", type="int", metavar="PIXELS", 
				default=default_options["icon_size"],
				help="Size in pixels to which the cover art should be resized "
						"in notifications (default: %default)")
		parser.add_option("-m", "--music-path", metavar="PATH", 
				default=default_options["music_path"],
				help="Path to music files, where album art will be looked for "
						"(default: %default, use empty string to disable)")
		parser.add_option("--status-icon", action="store_true", 
				default=default_options["status_icon"],
				help="Enable status icon %s" % d("status_icon"))
		parser.add_option("--no-status-icon", dest="status_icon", 
				action="store_false", help=optparse.SUPPRESS_HELP)
		parser.add_option("--play-state-icon-size", type="float", 
				default=default_options["play_state_icon_size"],
				help="Size of the play state (pause, stop, play) icon as a "
						"proportion of the status icon size (default: "
						"%default, use 0 for no play state icon")

		group = optparse.OptionGroup(parser,
				"Format related options for the notification display",
				"Supported wildcards: "
						"%t title / "
						"%a artist / "
						"%b album / "
						"%d song duration / "
						"%f base filename / "
						"%n track number / "
						"%p playlist position / "
						"<i> </i> italic text / "
						"<b> </b> bold text / "
						"<br> line break")
		group.add_option("-F", "--title-format", 
				default=default_options["title_format"], metavar="FORMAT",
				help="Format for the notification header (defalut %default)")
		group.add_option("-f", "--body-format", 
				default=default_options["body_format"], metavar="FORMAT",
				help="Format for the notification body (defalut %default)")
		parser.add_option_group(group)

		# parse the commandline
		(options, args) = parser.parse_args()

		if len(args):
			optionparser.error("Expected no non-option arguments")

		# dump default options if requested
		if options.show_defaults:
			print yaml.dump(DEFAULT_OPTIONS, default_flow_style=False)
			sys.exit()

		# initializate the notifier
		if not pynotify.init("mpn"):
			print "Failed to initialize pynotify module"
			sys.exit(1)

		# listen for kill signals and exit cleanly
		def handle_exit_signal(*args, **kwargs):
			mpn.quit()
		signal.signal(signal.SIGINT, handle_exit_signal)
		signal.signal(signal.SIGTERM, handle_exit_signal)

		mpn = Notifier(options=options)

		# fork if necessary
		if options.daemon and not options.debug:
			if os.fork() != 0:
				sys.exit()

		# run the notifier
		try:
			mpn.run()
		except KeyboardInterrupt:
			mpn.quit()

# defaults
# ------------------------------------------------------------------------------

DEFAULT_OPTIONS = {
	"daemon": False,
	"once": False,
	"debug": False,
	"persist": True,
	"timeout": 3,
	"keys": True,
	"icon_size": 128,
	"music_path": "/var/lib/mpd/music",
	"title_format": "%t",
	"body_format": "<b>%b</b><br><i>%a</i>",
	"status_icon": True,
	"play_state_icon_size": 0.4,
	}

# run if called directly
# ------------------------------------------------------------------------------

if __name__ == "__main__":
	app = Application()
	app.run()
