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
# Author: Olivier Tilloy <olivier@tilloy.net>
#
# ******************************************************************************

from datetime import datetime
import hashlib

import pytest

from pyexiv2.metadata import ImageMetadata
from .helpers import load_data_file


@pytest.fixture(scope='module')
def smiley():
    return load_data_file('smiley1.jpg', 'c066958457c685853293058f9bf129c1')


def metadata_from_buffer(fi):
    return ImageMetadata.from_buffer(fi.filedata)


def test_from_file_and_from_buffer(smiley):
    # from file
    m1 = ImageMetadata(smiley.filepath)
    m1.read()
    assert hashlib.md5(m1.buffer).hexdigest() == smiley.md5sum

    # from buffer
    m2 = metadata_from_buffer(smiley)
    assert hashlib.md5(m2.buffer).hexdigest() == smiley.md5sum


def test_buffer_not_updated_until_write_called(smiley):
    m = metadata_from_buffer(smiley)
    m.read()
    assert hashlib.md5(m.buffer).hexdigest() == smiley.md5sum

    # Modify the value of an EXIF tag
    m['Exif.Image.DateTime'].value = datetime.today()
    # Check that the buffer is unchanged until write() is called
    assert hashlib.md5(m.buffer).hexdigest() == smiley.md5sum
    # Write back the changes
    m.write()
    # Check that the buffer has changed
    assert hashlib.md5(m.buffer).hexdigest() != smiley.md5sum


def test_from_original_buffer(smiley):
    m1 = metadata_from_buffer(smiley)
    m2 = ImageMetadata.from_buffer(m1.buffer)
    assert hashlib.md5(m2.buffer).hexdigest() == smiley.md5sum


def test_from_modified_buffer(smiley):
    m1 = metadata_from_buffer(smiley)
    m1.read()
    key = 'Exif.Image.ImageDescription'
    value = 'my kingdom for a semiquaver'
    m1[key] = value
    m1.write()

    m2 = ImageMetadata.from_buffer(m1.buffer)
    m2.read()
    assert m2[key].value == value
