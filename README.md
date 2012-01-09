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

Options can be given on the command line (see `mpn --help` for details) or in a 
configuration file (or both). Command line options override anything given in a 
configuration file, which obviously in turn overwrite the defaults.

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

If that file doesn't exist, `mpnrc` in the current directory is also tried.

None of the configuration keys are required, and any given settings override the 
defaults. The defaults can be shown by running `mpn --show-defaults`. That YAML 
output can be used as the starting point for a configuration file.

The fields have the same names as the long forms of the command line arguments, 
but with underscores instead of hyphens. Full details can be found in the help 
text (`mpn --help`), in which the defaults are shown *after* the influence of 
any configuration file.

Download
--------

### This fork

- At Github: <https://github.com/tremby/mpn>

### Original MPN

- On PyPI: <http://pypi.python.org/pypi/MPNotifier>
- Directly: <http://chadok.info/mpn/MPNotifier-1.1.tar.gz>
- Darcs repository: <http://chadok.info/darcs/mpn>

Licence
-------

MPNotifier is free software, released under the term of the GPLv2+.

- Copyright 2007-2010 Olivier Schwander <olivier.schwander@chadok.info>
- Copyright 2009-2010 Walther Maldonado <walther.md@gmail.com>
- Copyright 2011 Bart Nagel <bart@tremby.net>
