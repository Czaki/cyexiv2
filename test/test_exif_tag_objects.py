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

import pytest

from pyexiv2.exif import ExifTag, ExifValueError
from .helpers import D, DT, FR, LazyTagCreator, expand_conversions, load_image

TAG_TEMPLATES = {
    'Ascii': 'Exif.Image.Copyright',
    'DateTime': ('Exif.Image.DateTime', 'Ascii'),
    'Date': ('Exif.GPSInfo.GPSDateStamp', 'Ascii'),
    'Comment': 'Exif.Photo.UserComment',
    'Byte': 'Exif.GPSInfo.GPSVersionID',
    'SByte': 'Exif.Pentax.Temperature',
    'Short': 'Exif.Image.BitsPerSample',
    'SShort': 'Exif.Image.TimeZoneOffset',
    'Long': 'Exif.Image.ImageWidth',
    'SLong': 'Exif.OlympusCs.ManometerReading',
    'Rational': 'Exif.Image.XResolution',
    'SRational': 'Exif.Image.BaselineExposure',
    'Undefined': 'Exif.Photo.ExifVersion',
}
TAG_CACHE = LazyTagCreator(ExifTag, TAG_TEMPLATES)
INVALID = ExifValueError


@pytest.mark.parametrize("tag, to_what, inp, exp", expand_conversions([
    ("Ascii", "python", [
        ('Some text.', 'Some text.'),
        (
            'Some text with exotic chàräctérʐ.',
            'Some text with exotic chàräctérʐ.'
        ),
    ]),
    ("Ascii", "string", [
        ('Some text.', 'Some text.'),
        (
            'Some text with exotic chàräctérʐ.',
            'Some text with exotic chàräctérʐ.'
        ),
    ]),

    ("DateTime", "python", [
        # Valid datetimes are converted to datetime objects
        ('2009-03-01 12:46:51', DT(2009, 3, 1, 12, 46, 51, tz=None)),
        ('2009:03:01 12:46:51', DT(2009, 3, 1, 12, 46, 51, tz=None)),
        ('2009-03-01T12:46:51Z', DT(2009, 3, 1, 12, 46, 51, tz=None)),

        # Invalid datetimes are preserved as strings
        ('2009-13-01 12:46:51', '2009-13-01 12:46:51'),
        ('2009-12-01', '2009-12-01'),
    ]),
    ("DateTime", "string", [
        # Timestamp fields accept either date or datetime objects
        (DT(2009, 3, 1, 12, 54, 28), '2009:03:01 12:54:28'),
        (D(2009, 3, 1), '2009:03:01 00:00:00'),
        (DT(1899, 12, 31, 23, 59, 59), '1899:12:31 23:59:59'),
        (D(1899, 12, 31), '1899:12:31 00:00:00'),
    ]),

    ("Date", "python", [
        # Valid dates are converted to date objects
        ('2009:08:04', D(2009, 8, 4)),

        # Invalid dates are preserved as strings
        ('2009:13:01', '2009:13:01'),
        ('2009-12-01', '2009-12-01'),
    ]),
    ("Date", "string", [
        # Datestamp fields accept date objects
        (D(2009, 3, 1), '2009:03:01'),
        (D(1899, 12, 31), '1899:12:31'),
    ]),

    ("Comment", "python", [
        ('A comment', 'A comment'),
        ('charset="Ascii" A comment', 'A comment'),
        ('charset="Unicode" A comment', 'A comment'),
        ('charset="Jis" A comment', 'A comment'),
        ('charset="Undefined" A comment', 'A comment'),
        ('charset="InvalidCharsetId" A comment', 'A comment'),

        # charset= is ignored when converting to python
        ('déjà vu', 'déjà vu'),
        ('charset="Ascii" déjà vu', 'déjà vu'),
        ('charset="Unicode" déjà vu', 'déjà vu'),
        ('charset="Jis" déjà vu', 'déjà vu'),
        ('charset="Undefined" déjà vu', 'déjà vu'),
        ('charset="InvalidCharsetId" déjà vu', 'déjà vu'),
    ]),
    ("Comment", "string", [
        ('A comment', b'A comment'),
        ('charset="Ascii" A comment', b'charset="Ascii" A comment'),
        (
            'charset="Unicode" A comment',
            b'charset="Unicode" A comment'
        ),
        ('charset="Jis" A comment', b'charset="Jis" A comment'),
        (
            'charset="Undefined" A comment',
            b'charset="Undefined" A comment'
        ),
        (
            'charset="InvalidCharsetId" A comment',
            b'charset="InvalidCharsetId" A comment'
        ),

        # when converting to bytes, if charset= is *known* not to
        # be able to represent the input string, None is returned
        ('déjà vu', b'd\xc3\xa9j\xc3\xa0 vu'),
        ('charset="Ascii" déjà vu', None),
        ('charset="Jis" déjà vu', None),
        (
            'charset="Unicode" déjà vu',
            b'charset="Unicode" d\xc3\xa9j\xc3\xa0 vu'
        ),
        (
            'charset="Undefined" déjà vu',
            b'charset="Undefined" d\xc3\xa9j\xc3\xa0 vu'
        ),
        (
            'charset="InvalidCharsetId" déjà vu',
            b'charset="InvalidCharsetId" d\xc3\xa9j\xc3\xa0 vu'
        ),
    ]),

    ("Byte", "python", [
        ('D', 'D'),
    ]),
    ("Byte", "string", [
        ('D', b'D'),
        (None, INVALID),
        (-57, INVALID),
        (3.14, INVALID),
    ]),

    ("SByte", "python", [
        ('15', '15'),
        ('-57', '-57'),
    ]),
    ("SByte", "string", [
        ('13', b'13'),
        ('-57', b'-57'),
        (None, INVALID),
    ]),

    ("Short", "python", [
        ('8', 8),
        ('+5628', 5628),
        ('abc', INVALID),
        ('5,64', INVALID),
        ('47.0001', INVALID),
        ('1E3', INVALID),
    ]),
    ("Short", "string", [
        (123, '123'),
        (-57, INVALID),
        ('invalid', INVALID),
        (3.14, INVALID),
    ]),

    ("SShort", "python", [
        ('8', 8),
        ('+5', 5),
        ('-6', -6),
        ('abc', INVALID),
        ('5,64', INVALID),
        ('47.0001', INVALID),
        ('1E3', INVALID),
    ]),
    ("SShort", "string", [
        (12, '12'),
        (-3, '-3'),
        ('invalid', INVALID),
        (3.14, INVALID),
    ]),

    ("Long", "python", [
        ('8', 8),
        ('+5628', 5628),
        ('abc', INVALID),
        ('5,64', INVALID),
        ('47.0001', INVALID),
        ('1E3', INVALID),
    ]),
    ("Long", "string", [
        (123, '123'),
        (678024, '678024'),
        (-57, INVALID),
        ('invalid', INVALID),
        (3.14, INVALID),
    ]),

    ("SLong", "python", [
        ('23', 23),
        ('+5628', 5628),
        ('-437', -437),
        ('abc', INVALID),
        ('5,64', INVALID),
        ('47.0001', INVALID),
        ('1E3', INVALID),
    ]),
    ("SLong", "string", [
        (123, '123'),
        (678024, '678024'),
        (-437, '-437'),
        ('invalid', INVALID),
        (3.14, INVALID),
    ]),

    ("Rational", "python", [
        ('5/3', FR(5, 3)),
        ('invalid', INVALID),
        ('-5/3', INVALID),
        ('5 / 3', INVALID),
        ('5/-3', INVALID),
    ]),
    ("Rational", "string", [
        (FR(5, 3), '5/3'),
        ('invalid', INVALID),
        (FR(-5, 3), INVALID),
    ]),

    ("SRational", "python", [
        ('5/3', FR(5, 3)),
        ('-5/3', FR(-5, 3)),
        ('invalid', INVALID),
        ('5 / 3', INVALID),
        ('5/-3', INVALID),
    ]),
    ("SRational", "string", [
        (FR(5, 3), '5/3'),
        (FR(-5, 3), '-5/3'),
        ('invalid', INVALID),
    ]),

    ("Undefined", "python", [
        ('48 49 48 48', '0100'),
    ]),
    ("Undefined", "string", [
        ('0100', '48 49 48 48'),
        (3, INVALID),
    ]),
]))
def test_conversion(tag, to_what, inp, exp):
    tag = TAG_CACHE[tag]
    if to_what == 'python':
        conv = tag._convert_to_python
    else:
        conv = tag._convert_to_string
    if exp is ExifValueError:
        with pytest.raises(ExifValueError):
            conv(inp)
    else:
        assert conv(inp) == exp


def test_set_value():
    tag = ExifTag('Exif.Thumbnail.Orientation', 1)  # top, left
    old_value = tag.value
    tag.value = 2
    assert tag.value != old_value


def test_set_raw_value_invalid():
    tag = ExifTag('Exif.GPSInfo.GPSVersionID')
    with pytest.raises(ValueError):
        tag.raw_value = '2 0 0 foo'


def test_makernote_types():
    # Makernote tags not attached to an image have an Undefined type by
    # default. When read from an existing image though, their type should
    # be correctly set.
    # See <https://bugs.launchpad.net/pyexiv2/+bug/781464>.
    tag1 = ExifTag('Exif.Pentax.PreviewResolution')
    tag1.raw_value = '640 480'
    assert tag1.type == 'Undefined'

    tag2 = ExifTag('Exif.Pentax.CameraInfo')
    tag2.raw_value = '76830 20070527 2 1 4228109'
    assert tag2.type == 'Undefined'
    with pytest.raises(ValueError):
        tag2.value

    metadata = load_image(
        'pentax-makernote.jpg', '646804b309a4a2d31feafe9bffc5d7f0'
    )
    tag1 = metadata[tag1.key]
    assert tag1.type == 'Short'
    assert tag1.value == [640, 480]

    tag2 = metadata[tag2.key]
    assert tag2.type == 'Long'
    assert tag2.value == [76830, 20070527, 2, 1, 4228109]
