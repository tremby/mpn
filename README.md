MPNotifier
==========

Description
-----------

MPNotifier is a lightweight client for [MPD](http://www.musicpd.org) displaying 
a popup notification each time a new song is played by the server. This kind of 
notification is usual for most graphical MPD clients but if you prefer to use a 
text-mode client like ncmpc or pms, you need to use separate tool like 
MPNotifier.

This version is a fork by Bart Nagel.

Prerequisite
------------

The following python packages are needed:

- python-notify
- python-mpd
- python-gtk2

The following python packages are recommended:

- python-imaging

Configuration
-------------

Options can be given on the command line (see `mpn.py --help` for details) or in 
a configuration file. Command line options override anything given in a 
configuration file.

MPNotifier will load the file `~/.mpnrc` if it exists, which is a YAML file like 
this:

    persist: True
    timeout: 10
    keys: False
    icon_size: 64
    music_path: /home/me/music
    title_format: >-
      %t
    body_format: >-
      from <i>%b</i>
      by <b>%a</b>

None of the configuration keys are required, and any given settings override the 
defaults, which are given in the help text (`mpn.py --help`, shown *after* the 
influence of any configuration file) and also as YAML in the `mpnrc` file 
distributed with MPN.

The fields have the same names as the long forms of the command line arguments 
(with underscores instead of hyphens). Again, see the help text for full 
details.

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
