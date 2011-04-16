#!/usr/bin/env python

from distutils.core import setup

with open('README') as file:
    long_description = file.read()

setup(name             = 'MPNotifier',
      version          = '1.1',
      description      = 'A lightweigh notifier for MPD',
      long_description = long_description,
      author           = 'Olivier Schwander',
      author_email     = 'olivier.schwander@chadok.info',
      url              = 'http://chadok.info/mpn',
      scripts          = ['mpn'],
      classifiers  = [
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Multimedia :: Sound/Audio',
        ],
      requires = [
        "pyyaml",
        "pygtk",
        "mpd",
        "pynotify"
        ],

     )

