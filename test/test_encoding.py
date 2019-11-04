# -*- coding: utf-8 -*-

# ******************************************************************************
#
# Copyright (C) 2006-2012 Olivier Tilloy <olivier@tilloy.net>
# Copyright (C) 2015-2019 Vincent Vande Vyvre <vincent.vandevyvre@oqapy.eu>
# Copyright (C) 2019      Zack Weinberg <zackw@panix.com>
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
# along with pyexiv2.  If not, see <https://www.gnu.org/licenses/>.
#
# Maintainer: Vincent Vande Vyvre <vincent.vandevyvre@oqapy.eu>
#
# ******************************************************************************

import os
from tempfile import TemporaryDirectory

import pytest

from pyexiv2.metadata import ImageMetadata
from .helpers import UNUSUAL_JPG_DATA, UNUSUAL_JPG_DATETIME


@pytest.fixture(scope='module')
def tempdir():
    with TemporaryDirectory(prefix="cyexiv2-test-encoding-") as td:
        yield td


@pytest.mark.parametrize('filename', [
    b'btest.jpg',
    b'bt\xe9st.jpg',
    b'bt\xc3\xa9st.jpg',
    u'utest.jpg',
    u'ut\u00c3st.jpg'
])
def test_read_from_filename(tempdir, filename):
    if isinstance(filename, bytes):
        tempdir = tempdir.encode("ascii")
    filepath = os.path.join(tempdir, filename)
    try:
        with open(filepath, 'wb') as fd:
            fd.write(UNUSUAL_JPG_DATA)
    except OSError as e:
        # The OS might not let us create files with some of the above names.
        pytest.skip("could not create test file: " + str(e))

    m = ImageMetadata(filepath)
    m.read()
    assert m['Exif.Image.DateTime'].value.isoformat() == UNUSUAL_JPG_DATETIME
