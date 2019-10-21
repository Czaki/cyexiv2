# -*- coding: utf-8 -*-

# ******************************************************************************
#
# Copyright (C) 2010 Olivier Tilloy <olivier@tilloy.net>
# Copyright (C) 2015-2016 Vincent Vande Vyvre <vincent.vandevyvre@oqapy.eu>
#
# This file is part of the pyexiv2 distribution.
#
# pyexiv2 is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# pyexiv2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyexiv2; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, 5th Floor, Boston, MA 02110-1301 USA.
#
# Maintainer: Vincent Vande Vyvre <vincent.vandevyvre@oqapy.eu>
#
# ******************************************************************************

import unittest
import os
import locale
from tempfile import gettempdir

from pyexiv2.metadata import ImageMetadata

_BINDATA = (
    b'\xff\xd8\xff\xe0\x00\x10\x4a\x46\x49\x46\x00\x01\x01\x01\x00\x48'
    b'\x00\x48\x00\x00\xff\xe1\x00\x36\x45\x78\x69\x66\x00\x00\x49\x49'
    b'\x2a\x00\x08\x00\x00\x00\x01\x00\x32\x01\x02\x00\x14\x00\x00\x00'
    b'\x1a\x00\x00\x00\x00\x00\x00\x00\x32\x30\x31\x30\x3a\x30\x33\x3a'
    b'\x31\x38\x20\x31\x33\x3a\x33\x39\x3a\x35\x38\x00\xff\xdb\x00\x43'
    b'\x00\x05\x03\x04\x04\x04\x03\x05\x04\x04\x04\x05\x05\x05\x06\x07'
    b'\x0c\x08\x07\x07\x07\x07\x0f\x0b\x0b\x09\x0c\x11\x0f\x12\x12\x11'
    b'\x0f\x11\x11\x13\x16\x1c\x17\x13\x14\x1a\x15\x11\x11\x18\x21\x18'
    b'\x1a\x1d\x1d\x1f\x1f\x1f\x13\x17\x22\x24\x22\x1e\x24\x1c\x1e\x1f'
    b'\x1e\xff\xdb\x00\x43\x01\x05\x05\x05\x07\x06\x07\x0e\x08\x08\x0e'
    b'\x1e\x14\x11\x14\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e'
    b'\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e'
    b'\x1e\x1e\x1e\x1e\x1e\x1e\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03'
    b'\x01\x22\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x15\x00\x01\x01'
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08'
    b'\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x14\x01\x01\x00\x00\x00\x00'
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x14'
    b'\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00'
    b'\xb2\xc0\x07\xff\xd9'
)


class TestEncodings(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        os.chdir(gettempdir())
        try:
            locale.setlocale(locale.LC_ALL, '')
        except locale.Error:
            self.encoding = None
        else:
            lc, self.encoding = locale.getlocale()

    def tearDown(self):
        os.chdir(self._cwd)

    def _create_file(self, filename):
        try:
            os.remove(filename)
        except OSError:
            pass
        fd = open(filename, 'wb')
        fd.write(_BINDATA)
        fd.close()

    def _test_filename(self, filename):
        self._create_file(filename)
        m = ImageMetadata(filename)
        m.read()
        os.remove(filename)

    def test_ascii(self):
        self._test_filename('test.jpg')

    def test_latin1(self):
        self._test_filename('tést.jpg')

    def test_latin1_escaped(self):
        self._test_filename('t\xc3\xa9st.jpg')

    def test_unicode_ascii(self):
        if self.encoding is not None:
            self._test_filename(u'test.jpg')

    def test_unicode_latin1(self):
        if self.encoding is not None:
            self._test_filename(u'tést.jpg')

    def test_unicode_latin1_escaped(self):
        if self.encoding is not None:
            self._test_filename(u't\xe9st.jpg')
