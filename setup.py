#!/usr/bin/env python

from distutils.core import setup
import mpn

with open("README.md") as file:
	long_description = file.read()

setup(
		name=mpn.NAME,
		version=mpn.VERSION,
		description=mpn.DESCRIPTION,
		long_description=long_description,
		author=mpn.AUTHOR,
		author_email=mpn.AUTHOR_EMAIL,
		url=mpn.URL,
		license=mpn.LICENSE,

		py_modules=["mpn"],
		scripts=["mpn"],
		classifiers=[
				"Intended Audience :: End Users/Desktop",
				"License :: OSI Approved :: GNU General Public License (GPL)",
				"Operating System :: OS Independent",
				"Programming Language :: Python",
				"Topic :: Multimedia :: Sound/Audio",
				],
		requires = [
				"pyyaml",
				"pygtk",
				"mpd",
				"pynotify"
				],
		)
