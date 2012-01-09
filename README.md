MPNotifier
==========

Description
-----------

MPNotifier is a lightweight client for `MPD <http://www.musicpd.org>`_
displaying a popup notification each time a new song is played by the
server. This kind of notification is usual for most of graphical MPD
clients but if you prefer to use a text-mode client like ncmpc, you need
to use a third-party tool like MPNotifier.

This version is a fork by Bart Nagel.

Prerequisite
------------

The following python packages are needed:

*  python-notify,
*  python-mpd,
*  python-gtk2.

The following python packages are recommended:

*  python-imaging

Configuration
-------------

MPNotifier will load the file `~/.mpnrc`, which a YAML file like this
one::

   daemon: False
   once: False
   debug: False
   persist: True
   timeout: 3
   keys: True
   icon: gnome-mime-audio
   icon_size: 128
   music_path: /var/lib/mpd/music
   title: >-
     %t
   body: >-
     <b>%b</b>
     <i>%a</i>

The fields have the same names than the long form of the command line
arguments, see `mpn -h` for explanation.

Download
--------

### This fork

- At Github: https://github.com/tremby/mpn

### Original MPN

- On PyPI: http://pypi.python.org/pypi/MPNotifier
- Directly: http://chadok.info/mpn/MPNotifier-1.1.tar.gz
- Darcs repository: http://chadok.info/darcs/mpn

Licence
-------

MPNotifier is free software, released under the term of the GPLv2+.

- Copyright 2007-2010 Olivier Schwander <olivier.schwander@chadok.info>
- Copyright 2009-2010 Walther Maldonado <walther.md@gmail.com>
- Copyright 2011 Bart Nagel <bart@tremby.net>