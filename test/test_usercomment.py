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

import tempfile

import pytest

from pyexiv2.metadata import ImageMetadata
from .helpers import load_image, EMPTY_JPG_DATA


@pytest.fixture(scope='module')
def uc_ascii():
    return load_image(
        'usercomment-ascii.jpg', 'ad29ac65fb6f63c8361aaed6cb02f8c7'
    )


def test_read_ascii(uc_ascii):
    tag = uc_ascii['Exif.Photo.UserComment']
    assert tag.type == 'Comment'
    assert tag.raw_value == b'charset="Ascii" deja vu'
    assert tag.value == 'deja vu'


def test_write_ascii(uc_ascii):
    tag = uc_ascii['Exif.Photo.UserComment']
    assert tag.type == 'Comment'
    tag.value = 'foo bar'
    assert tag.raw_value == b'foo bar'
    assert tag.value == 'foo bar'


def test_write_unicode_over_ascii(uc_ascii):
    tag = uc_ascii['Exif.Photo.UserComment']
    assert tag.type == 'Comment'
    tag.value = 'déjà vu'
    assert tag.raw_value == b'd\xc3\xa9j\xc3\xa0 vu'
    assert tag.value == 'déjà vu'


@pytest.fixture(scope='module')
def uc_unicode_ii():
    return load_image(
        'usercomment-unicode-ii.jpg', '13b7cc09129a8677f2cf18634f5abd3c'
    )


def test_read_unicode_ii(uc_unicode_ii):
    tag = uc_unicode_ii['Exif.Photo.UserComment']
    assert tag.type == 'Comment'
    assert tag.raw_value == b'charset="Unicode" d\xc3\xa9j\xc3\xa0 vu'
    assert tag.value == 'déjà vu'


def test_write_ascii_over_unicode_ii(uc_unicode_ii):
    tag = uc_unicode_ii['Exif.Photo.UserComment']
    assert tag.type == 'Comment'
    tag.value = 'foo bar'
    assert tag.raw_value == b'foo bar'
    assert tag.value == 'foo bar'


def test_write_unicode_ii(uc_unicode_ii):
    tag = uc_unicode_ii['Exif.Photo.UserComment']
    assert tag.type == 'Comment'
    tag.value = 'παράδειγμα'
    assert tag.raw_value == (
        b'\xcf\x80\xce\xb1\xcf\x81\xce\xac\xce\xb4'
        b'\xce\xb5\xce\xb9\xce\xb3\xce\xbc\xce\xb1'
    )
    assert tag.value == 'παράδειγμα'


@pytest.fixture(scope='module')
def uc_unicode_mm():
    return load_image(
        'usercomment-unicode-mm.jpg', '7addfed7823c556ba489cd4ab2037200'
    )


def test_read_unicode_mm(uc_unicode_mm):
    tag = uc_unicode_mm['Exif.Photo.UserComment']
    assert tag.type == 'Comment'
    assert tag.raw_value == b'charset="Unicode" d\xc3\xa9j\xc3\xa0 vu'
    assert tag.value == 'déjà vu'


def test_write_ascii_over_unicode_mm(uc_unicode_mm):
    tag = uc_unicode_mm['Exif.Photo.UserComment']
    assert tag.type == 'Comment'
    tag.value = 'foo bar'
    assert tag.raw_value == b'foo bar'
    assert tag.value == 'foo bar'


def test_write_unicode_mm(uc_unicode_mm):
    tag = uc_unicode_mm['Exif.Photo.UserComment']
    assert tag.type == 'Comment'
    tag.value = 'παράδειγμα'
    assert tag.raw_value == (
        b'\xcf\x80\xce\xb1\xcf\x81\xce\xac\xce\xb4'
        b'\xce\xb5\xce\xb9\xce\xb3\xce\xbc\xce\xb1'
    )
    assert tag.value == 'παράδειγμα'


@pytest.fixture
def uc_empty():
    with tempfile.NamedTemporaryFile(suffix='.jpg', mode="w+b") as fp:
        fp.write(EMPTY_JPG_DATA)
        fp.flush()
        fp.seek(0)
        yield fp.name


@pytest.mark.parametrize("value", [
    'deja vu',
    'déjà vu',
    'παράδειγμα',
])
def test_add_comment(value, uc_empty):
    metadata = ImageMetadata(uc_empty)
    metadata.read()
    key = 'Exif.Photo.UserComment'
    metadata[key] = value
    metadata.write()

    metadata = ImageMetadata(uc_empty)
    metadata.read()
    assert key in metadata.exif_keys
    tag = metadata[key]
    assert tag.type == 'Comment'
    assert tag.value == value
