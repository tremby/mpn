MPNotifier
==========

Description
-----------

MPNotifier is a lightweight client for [MPD](http://www.musicpd.org) displaying 
a popup notification each time a new song is played by the server. This kind of 
notification is usual for most graphical MPD clients but if you prefer to use a 
text-mode client like [ncmpc](http://mpd.wikia.com/wiki/Client:Ncmpc) or 
[pms](http://pms.sourceforge.net/), you need to use separate tool like 
MPNotifier.

This version is a fork by Bart Nagel adding various features and fixing bugs. A 
few of the added features:

- an optional system tray icon showing play state
- popup menu for that icon with basic playback controls
- album art shown in the notifications and in miniature on the tray icon
- remote control via signals

Showing album art is only available if the library directory tree is available 
on the local machine, whether physically local or mounted with NFS or similar, 
and when the album art files are named as MPNotifier expects (see below).

Prerequisites
-------------

The following python packages are needed:

- gtk, glib, gobject
- mpd
- notify2
- yaml
- Image
- numpy

These can be installed in Ubuntu with the following command:

    sudo aptitude install python-gtk2 python-imaging python-notify2 python-numpy python-yaml
    sudo easy_install python-mpd2

The prodecure may differ with different distributions or operating systems.

Installation and running
------------------------

Installation is optional (it'll run from its source directory). To install do 
the normal Python thing:

    sudo python setup.py install

To run, execute its startup script. If installed that's just `mpn`, otherwise 
`./mpn` if in the same directory.

Configuration
-------------

Options can be given on the command line (see `mpn --help` for details) or in a 
configuration file (or both). Options given in a configuration file override the 
defaults, and options given on the command line in turn override those.

MPNotifier will load the file `~/.mpnrc` if it exists, which is a YAML file like 
this:

    persist: True
    timeout: 10
    keys: False
    icon_size: 64
    music_path: /home/me/music
    title_format: "%t"
    body_format: |
        from <i>%b</i>
        by <b>%a</b>
    play_state_icon_size: 0.5

If that file doesn't exist, `mpnrc` in the current directory is also tried.

None of the configuration keys are required, and any given settings override the 
defaults. The defaults can be shown by running `mpn --show-defaults`. That YAML 
output can be used as the starting point for a configuration file.

The fields have the same names as the long forms of the command line arguments, 
but with underscores instead of hyphens. Full details can be found in the help 
text (`mpn --help`), in which the defaults are shown *after* the influence of 
any configuration file.

Album art
---------

To display album art (in notifications and as the system tray icon icon) the 
`music_path` option must be set via a configuration file or the `--music-path` 
command line option. Its value must point to the root of MPD's music library, 
which must be available on the local machine (whether physically local or 
mounted via NFS or similar). The configuration variable's default value is 
`/var/lib/mpd/music`, which is the library's default location on Ubuntu, so this 
may or may not already be correct for you.

MPNotifier then hopes to find an image file in the same directory as the 
currently playing song matching one of a long list of possibile filenames, 
including `cover`, `front` and `album`, with `.png` or `.jpg` suffixes and 
optionally with a `.` prefix. See the `possible_cover_filenames` function in the 
source code to see how the possibilities are built, and just edit the source if 
you use a scheme not covered.

If a suitable image isn't found a placeholder image of a CD will be used 
instead.

Download
--------

### This fork

- At Github: <https://github.com/tremby/mpn>

### Original MPNotifier

- On PyPI: <http://pypi.python.org/pypi/MPNotifier>
- Directly: <http://chadok.info/mpn/MPNotifier-1.1.tar.gz>
- Darcs repository: <http://chadok.info/darcs/mpn>

Licence
-------

MPNotifier is free software, released under the term of the GPLv2+.

- Copyright 2007-2010 Olivier Schwander <olivier.schwander@chadok.info>
- Copyright 2009-2010 Walther Maldonado <walther.md@gmail.com>
- Copyright 2011 Bart Nagel <bart@tremby.net>
