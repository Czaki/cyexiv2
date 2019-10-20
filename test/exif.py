# -*- coding: utf-8 -*-

# ******************************************************************************
#
# Copyright (C) 2009-2011 Olivier Tilloy <olivier@tilloy.net>
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

from pyexiv2.exif import ExifTag, ExifValueError
from pyexiv2.metadata import ImageMetadata

from .testutils import get_absolute_file_path, md5sum_file, D, DT, FR


class TestExifTag(unittest.TestCase):
    def do_test_convert_to_python(self, name, tagtype, valid=[], invalid=[]):
        tag = ExifTag(name)
        self.assertEqual(tag.type, tagtype)
        for s, exp in valid:
            self.assertEqual(tag._convert_to_python(s), exp)
        for s in invalid:
            try:
                self.assertRaises(ExifValueError, tag._convert_to_python, s)
            except AssertionError as e:
                e.args = (e.args[0] + " (s=%s)" % repr(s), )
                raise

    def do_test_convert_to_string(self, name, tagtype, valid=[], invalid=[]):
        tag = ExifTag(name)
        self.assertEqual(tag.type, tagtype)
        for v, exp in valid:
            self.assertEqual(tag._convert_to_string(v), exp)
        for v in invalid:
            try:
                self.assertRaises(ExifValueError, tag._convert_to_string, v)
            except AssertionError as e:
                e.args = (e.args[0] + " (v=%s)" % repr(v), )
                raise

    def test_convert_to_python_ascii(self):
        # Unstructured text fields (despite "Ascii", yes they can
        # contain unicode)
        self.do_test_convert_to_python(
            'Exif.Image.Copyright',
            'Ascii',
            valid=[
                ('Some text.', 'Some text.'),
                (
                    'Some text with exotic chàräctérʐ.',
                    'Some text with exotic chàräctérʐ.'
                ),
            ]
        )

        # Timestamps represented with text strings
        self.do_test_convert_to_python(
            'Exif.Image.DateTime',
            'Ascii',
            valid=[
                # Valid datetimes are converted to datetime objects
                ('2009-03-01 12:46:51', DT(2009, 3, 1, 12, 46, 51, tz=None)),
                ('2009:03:01 12:46:51', DT(2009, 3, 1, 12, 46, 51, tz=None)),
                ('2009-03-01T12:46:51Z', DT(2009, 3, 1, 12, 46, 51, tz=None)),

                # Invalid datetimes are preserved as strings
                ('2009-13-01 12:46:51', '2009-13-01 12:46:51'),
                ('2009-12-01', '2009-12-01'),
            ]
        )

        # Datestamps represented with text strings
        self.do_test_convert_to_python(
            'Exif.GPSInfo.GPSDateStamp',
            'Ascii',
            valid=[
                # Valid dates are converted to date objects
                ('2009:08:04', D(2009, 8, 4)),

                # Invalid dates are preserved as strings
                ('2009:13:01', '2009:13:01'),
                ('2009-12-01', '2009-12-01'),
            ]
        )

    def test_convert_to_string_ascii(self):
        # Unstructured text fields
        self.do_test_convert_to_string(
            'Exif.Image.Copyright',
            'Ascii',
            valid=[
                ('Some text.', 'Some text.'),
                (
                    'Some text with exotic chàräctérʐ.',
                    'Some text with exotic chàräctérʐ.'
                ),
            ]
        )

        # Timestamp fields accept either date or datetime objects
        self.do_test_convert_to_string(
            'Exif.Image.DateTime',
            'Ascii',
            valid=[
                (DT(2009, 3, 1, 12, 54, 28), '2009:03:01 12:54:28'),
                (D(2009, 3, 1), '2009:03:01 00:00:00'),
                (DT(1899, 12, 31, 23, 59, 59), '1899:12:31 23:59:59'),
                (D(1899, 12, 31), '1899:12:31 00:00:00'),
            ]
        )

        # Datestamp fields accept date objects
        self.do_test_convert_to_string(
            'Exif.GPSInfo.GPSDateStamp',
            'Ascii',
            valid=[
                (D(2009, 3, 1), '2009:03:01'),
                (D(1899, 12, 31), '1899:12:31'),
            ]
        )

    def test_convert_to_python_byte(self):
        self.do_test_convert_to_python(
            'Exif.GPSInfo.GPSVersionID', 'Byte', valid=[
                ('D', 'D'),
            ]
        )

    def test_convert_to_string_byte(self):
        self.do_test_convert_to_string(
            'Exif.GPSInfo.GPSVersionID',
            'Byte',
            valid=[
                ('D', b'D'),
            ],
            invalid=[
                None,
                -57,
                3.14,
            ]
        )

    def test_convert_to_python_sbyte(self):
        self.do_test_convert_to_python(
            'Exif.Pentax.Temperature', 'SByte', valid=[
                ('15', '15'),
            ]
        )

    def test_convert_to_string_sbyte(self):
        self.do_test_convert_to_string(
            'Exif.Pentax.Temperature',
            'SByte',
            valid=[
                ('13', b'13'),
                ('-57', b'-57'),
            ],
            invalid=[
                None,
            ]
        )

    def test_convert_to_python_comment(self):
        self.do_test_convert_to_python(
            'Exif.Photo.UserComment',
            'Comment',
            valid=[
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
            ]
        )

    def test_convert_to_string_comment(self):
        self.do_test_convert_to_string(
            'Exif.Photo.UserComment',
            'Comment',
            valid=[
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
            ]
        )

    def test_convert_to_python_short(self):
        self.do_test_convert_to_python(
            'Exif.Image.BitsPerSample',
            'Short',
            valid=[
                ('8', 8),
                ('+5628', 5628),
            ],
            invalid=[
                'abc',
                '5,64',
                '47.0001',
                '1E3',
            ]
        )

    def test_convert_to_string_short(self):
        # Valid values
        self.do_test_convert_to_string(
            'Exif.Image.BitsPerSample',
            'Short',
            valid=[
                (123, '123'),
            ],
            invalid=[
                -57,
                'invalid',
                3.14,
            ]
        )

    def test_convert_to_python_sshort(self):
        # Valid values
        self.do_test_convert_to_python(
            'Exif.Image.TimeZoneOffset',
            'SShort',
            valid=[
                ('8', 8),
                ('+5', 5),
                ('-6', -6),
            ],
            invalid=[
                'abc',
                '5,64',
                '47.0001',
                '1E3',
            ]
        )

    def test_convert_to_string_sshort(self):
        # Valid values
        self.do_test_convert_to_string(
            'Exif.Image.TimeZoneOffset',
            'SShort',
            valid=[
                (12, '12'),
                (-3, '-3'),
            ],
            invalid=[
                'invalid',
                3.14,
            ]
        )

    def test_convert_to_python_long(self):
        self.do_test_convert_to_python(
            'Exif.Image.ImageWidth',
            'Long',
            valid=[
                ('8', 8),
                ('+5628', 5628),
            ],
            invalid=[
                'abc',
                '5,64',
                '47.0001',
                '1E3',
            ]
        )

    def test_convert_to_string_long(self):
        # Valid values
        self.do_test_convert_to_string(
            'Exif.Image.ImageWidth',
            'Long',
            valid=[
                (123, '123'),
                (678024, '678024'),
            ],
            invalid=[
                -57,
                'invalid',
                3.14,
            ]
        )

    def test_convert_to_python_slong(self):
        # Valid values
        self.do_test_convert_to_python(
            'Exif.OlympusCs.ManometerReading',
            'SLong',
            valid=[
                ('23', 23),
                ('+5628', 5628),
                ('-437', -437),
            ],
            invalid=[
                'abc',
                '5,64',
                '47.0001',
                '1E3',
            ]
        )

    def test_convert_to_string_slong(self):
        # Valid values
        self.do_test_convert_to_string(
            'Exif.OlympusCs.ManometerReading',
            'SLong',
            valid=[
                (123, '123'),
                (678024, '678024'),
                (-437, '-437'),
            ],
            invalid=[
                'invalid',
                3.14,
            ]
        )

    def test_convert_to_python_rational(self):
        # Valid values
        self.do_test_convert_to_python(
            'Exif.Image.XResolution',
            'Rational',
            valid=[
                ('5/3', FR(5, 3)),
            ],
            invalid=[
                'invalid',
                '-5/3',
                '5 / 3',
                '5/-3',
            ]
        )

    def test_convert_to_string_rational(self):
        self.do_test_convert_to_string(
            'Exif.Image.XResolution',
            'Rational',
            valid=[(FR(5, 3), '5/3')],
            invalid=[
                'invalid',
                FR(-5, 3),
            ]
        )

    def test_convert_to_python_srational(self):
        self.do_test_convert_to_python(
            'Exif.Image.BaselineExposure',
            'SRational',
            valid=[
                ('5/3', FR(5, 3)),
                ('-5/3', FR(-5, 3)),
            ],
            invalid=[
                'invalid',
                '5 / 3',
                '5/-3',
            ]
        )

    def test_convert_to_string_srational(self):
        self.do_test_convert_to_string(
            'Exif.Image.BaselineExposure',
            'SRational',
            valid=[
                (FR(5, 3), '5/3'),
                (FR(-5, 3), '-5/3'),
            ],
            invalid=[
                'invalid',
            ]
        )

    def test_convert_to_python_undefined(self):
        self.do_test_convert_to_python(
            'Exif.Photo.ExifVersion',
            'Undefined',
            valid=[
                ('48 49 48 48', '0100'),
            ]
        )

    def test_convert_to_string_undefined(self):
        # Valid values
        self.do_test_convert_to_string(
            'Exif.Photo.ExifVersion',
            'Undefined',
            valid=[
                ('0100', '48 49 48 48'),
            ],
            invalid=[
                3,
            ]
        )

    def test_set_value(self):
        tag = ExifTag('Exif.Thumbnail.Orientation', 1)  # top, left
        old_value = tag.value
        tag.value = 2
        self.assertNotEqual(tag.value, old_value)

    def test_set_raw_value_invalid(self):
        tag = ExifTag('Exif.GPSInfo.GPSVersionID')
        value = '2 0 0 foo'
        self.assertRaises(ValueError, setattr, tag, 'raw_value', value)

    def test_makernote_types(self):
        # Makernote tags not attached to an image have an Undefined type by
        # default. When read from an existing image though, their type should be
        # correctly set (see https://bugs.launchpad.net/pyexiv2/+bug/781464).
        tag1 = ExifTag('Exif.Pentax.PreviewResolution')
        tag1.raw_value = '640 480'
        self.assertEqual(tag1.type, 'Undefined')
        tag2 = ExifTag('Exif.Pentax.CameraInfo')
        tag2.raw_value = '76830 20070527 2 1 4228109'
        self.assertEqual(tag2.type, 'Undefined')
        self.assertRaises(ValueError, getattr, tag2, 'value')

        filepath = get_absolute_file_path('data', 'pentax-makernote.jpg')
        checksum = '646804b309a4a2d31feafe9bffc5d7f0'
        self.assertEqual(md5sum_file(filepath), checksum)
        metadata = ImageMetadata(filepath)
        metadata.read()
        tag1 = metadata[tag1.key]
        self.assertEqual(tag1.type, 'Short')
        self.assertEqual(tag1.value, [640, 480])
        tag2 = metadata[tag2.key]
        self.assertEqual(tag2.type, 'Long')
        self.assertEqual(tag2.value, [76830, 20070527, 2, 1, 4228109])
