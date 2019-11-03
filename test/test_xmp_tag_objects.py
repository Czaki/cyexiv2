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

from pyexiv2.xmp import XmpTag, XmpValueError
from .helpers import D, DT, FR, LazyTagCreator, expand_conversions

TAG_TEMPLATES = {
    'Boolean': 'Xmp.xmpRights.Marked',
    'Date': 'Xmp.xmp.CreateDate',
    'Integer': 'Xmp.xmpMM.SaveID',
    'MIMEType': 'Xmp.dc.format',
    'ProperName': 'Xmp.photoshop.CaptionWriter',
    'Text': 'Xmp.dc.source',
    'URI': 'Xmp.xmpMM.DocumentID',
    'URL': 'Xmp.xmp.BaseURL',
    'Rational': 'Xmp.xmpDM.videoPixelAspectRatio',
    'Subject': ('Xmp.dc.Subject', ''),
}
TAG_CACHE = LazyTagCreator(XmpTag, TAG_TEMPLATES)
INVALID = XmpValueError


@pytest.mark.parametrize("tag, to_what, inp, exp", expand_conversions([
    ('Boolean', 'python', [
        ('True', True),
        ('False', False),
        ('invalid', INVALID),
        (None, INVALID),
    ]),
    ('Boolean', 'string', [
        (True, 'True'),
        (False, 'False'),
        ('invalid', INVALID),
        (None, INVALID),
    ]),
    ('Date', 'python', [
        ('1999', D(1999, 1, 1)),
        ('1999-10', D(1999, 10, 1)),
        ('1999-10-13', D(1999, 10, 13)),
        ('1999-10-13T05:03Z', DT(1999, 10, 13, 5, 3)),
        ('1999-10-13T05:03+06:00', DT(1999, 10, 13, 5, 3, tz=('+', 6, 0))),
        ('1999-10-13T05:03-06:00', DT(1999, 10, 13, 5, 3, tz=('-', 6, 0))),
        ('1999-10-13T05:03:54Z', DT(1999, 10, 13, 5, 3, 54)),
        (
            '1999-10-13T05:03:54+06:00',
            DT(1999, 10, 13, 5, 3, 54, tz=('+', 6, 0))
        ),
        (
            '1999-10-13T05:03:54-06:00',
            DT(1999, 10, 13, 5, 3, 54, tz=('-', 6, 0))
        ),
        (
            '1999-10-13T05:03:54.721Z',
            DT(1999, 10, 13, 5, 3, 54, 721000, ())
        ),
        (
            '1999-10-13T05:03:54.721+06:00',
            DT(1999, 10, 13, 5, 3, 54, 721000, ('+', 6, 0))
        ),
        (
            '1999-10-13T05:03:54.721-06:00',
            DT(1999, 10, 13, 5, 3, 54, 721000, ('-', 6, 0))
        ),
        ('invalid', INVALID),
        ('11/10/1983', INVALID),
        ('-1000', INVALID),
        ('2009-13', INVALID),
        ('2009-10-32', INVALID),
        ('2009-10-30T25:12Z', INVALID),
        ('2009-10-30T23:67Z', INVALID),
        ('2009-01-22T21', INVALID),
    ]),
    ('Date', 'string', [
        (D(2009, 2, 4), '2009-02-04'),
        (D(1899, 12, 31), '1899-12-31'),
        (D(1999, 10, 13), '1999-10-13'),
        (DT(1999, 10, 13, 5, 3), '1999-10-13T05:03Z'),
        (DT(1899, 12, 31, 23, 59), '1899-12-31T23:59Z'),
        (DT(1999, 10, 13, 5, 3), '1999-10-13T05:03Z'),
        (DT(1899, 12, 31, 23, 59), '1899-12-31T23:59Z'),
        (DT(1999, 10, 13, 5, 3, tz=('+', 5, 30)), '1999-10-13T05:03+05:30'),
        (DT(1999, 10, 13, 5, 3, tz=('-', 11, 30)), '1999-10-13T05:03-11:30'),
        (DT(1899, 12, 31, 23, 59, tz=('+', 5, 30)), '1899-12-31T23:59+05:30'),
        (DT(1999, 10, 13, 5, 3, 27), '1999-10-13T05:03:27Z'),
        (DT(1899, 12, 31, 23, 59, 59), '1899-12-31T23:59:59Z'),
        (DT(1999, 10, 13, 5, 3, 27), '1999-10-13T05:03:27Z'),
        (DT(1899, 12, 31, 23, 59, 59), '1899-12-31T23:59:59Z'),
        (
            DT(1999, 10, 13, 5, 3, 27, tz=('+', 5, 30)),
            '1999-10-13T05:03:27+05:30'
        ),
        (
            DT(1999, 10, 13, 5, 3, 27, tz=('-', 11, 30)),
            '1999-10-13T05:03:27-11:30'
        ),
        (
            DT(1899, 12, 31, 23, 59, 59, tz=('+', 5, 30)),
            '1899-12-31T23:59:59+05:30'
        ),
        (DT(1999, 10, 13, 5, 3, 27, 124300), '1999-10-13T05:03:27.1243Z'),
        (DT(1899, 12, 31, 23, 59, 59, 124300), '1899-12-31T23:59:59.1243Z'),
        (DT(1999, 10, 13, 5, 3, 27, 124300), '1999-10-13T05:03:27.1243Z'),
        (DT(1899, 12, 31, 23, 59, 59, 124300), '1899-12-31T23:59:59.1243Z'),
        (
            DT(1999, 10, 13, 5, 3, 27, 124300, tz=('+', 5, 30)),
            '1999-10-13T05:03:27.1243+05:30'
        ),
        (
            DT(1999, 10, 13, 5, 3, 27, 124300, tz=('-', 11, 30)),
            '1999-10-13T05:03:27.1243-11:30'
        ),
        (
            DT(1899, 12, 31, 23, 59, 59, 124300, tz=('+', 5, 30)),
            '1899-12-31T23:59:59.1243+05:30'
        ),
        ('invalid', INVALID),
        (None, INVALID),
    ]),
    ('Integer', 'python', [
        ('23', 23),
        ('+5628', 5628),
        ('-4', -4),
        ('abc', INVALID),
        ('5,64', INVALID),
        ('47.0001', INVALID),
        ('1E3', INVALID),
    ]),
    ('Integer', 'string', [
        (123, '123'),
        (-57, '-57'),
        ('invalid', INVALID),
        (3.14, INVALID),
    ]),
    ('MIMEType', 'python', [
        ('image/jpeg', ('image', 'jpeg')),
        ('video/ogg', ('video', 'ogg')),
        ('invalid', INVALID),
        ('image-jpeg', INVALID),
    ]),
    ('MIMEType', 'string', [
        (('image', 'jpeg'), 'image/jpeg'),
        (('video', 'ogg'), 'video/ogg'),
        ('invalid', INVALID),
        (('image', ), INVALID),
    ]),
    ('ProperName', 'python', [
        ('Gérard', 'Gérard'),
        ('Python Software Foundation', 'Python Software Foundation'),
        (None, INVALID),
    ]),
    ('ProperName', 'string', [
        ('Gérard', b'G\xc3\xa9rard'),
        ('Python Software Foundation', b'Python Software Foundation'),
        (None, INVALID),
    ]),
    ('Text', 'python', [
        ('Some text.', 'Some text.'),
        (
            b'Some text with exotic ch\xc3\xa0r\xc3\xa4ct\xc3\xa9r\xca\x90.',
            'Some text with exotic chàräctérʐ.'
        ),
        (None, INVALID),
    ]),
    ('Text', 'string', [
        ('Some text', b'Some text'),
        (
            'Some text with exotic chàräctérʐ.',
            b'Some text with exotic ch\xc3\xa0r\xc3\xa4ct\xc3\xa9r\xca\x90.'
        ),
        (None, INVALID),
    ]),
    ('URI', 'python', [
        ('http://example.com', 'http://example.com'),
        ('https://example.com', 'https://example.com'),
        ('http://localhost:8000/resource', 'http://localhost:8000/resource'),
        (
            'uuid:9A3B7F52214211DAB6308A7391270C13',
            'uuid:9A3B7F52214211DAB6308A7391270C13'
        ),
        (None, INVALID),
    ]),
    ('URI', 'string', [
        ('http://example.com', b'http://example.com'),
        ('https://example.com', b'https://example.com'),
        ('http://localhost:8000/resource', b'http://localhost:8000/resource'),
        (
            'uuid:9A3B7F52214211DAB6308A7391270C13',
            b'uuid:9A3B7F52214211DAB6308A7391270C13'
        ),
        (None, INVALID),
    ]),
    ('URL', 'python', [
        ('http://example.com', 'http://example.com'),
        ('https://example.com', 'https://example.com'),
        (
            'http://localhost:8000/resource',
            'http://localhost:8000/resource'
        ),
        (None, INVALID),
    ]),
    ('URL', 'string', [
        ('http://example.com', b'http://example.com'),
        ('https://example.com', b'https://example.com'),
        ('http://localhost:8000/resource', b'http://localhost:8000/resource'),
        (None, INVALID),
    ]),
    ('Rational', 'python', [
        ('5/3', FR(5, 3)),
        ('-5/3', FR(-5, 3)),
        ('invalid', INVALID),
        ('5 / 3', INVALID),
        ('5/-3', INVALID),
    ]),
    ('Rational', 'string', [
        (FR(5, 3), '5/3'),
        (FR(-5, 3), '-5/3'),
        ('invalid', INVALID),
        (5 / 3, INVALID),  # float
    ]),
    # TODO: other types
]))
def test_simple_conversion(tag, to_what, inp, exp):
    tag = TAG_CACHE[tag]
    if to_what == 'python':
        conv = tag._convert_to_python
    else:
        conv = tag._convert_to_string
    if exp is INVALID:
        with pytest.raises(INVALID):
            conv(inp, tag.type)
    else:
        assert conv(inp, tag.type) == exp


@pytest.mark.parametrize("tag, to_what, inp, exp", expand_conversions([
    ('Subject', 'python', [
        ('', ''),
        ('One value only', 'One value only'),
    ]),
    ('Subject', 'string', [
        ('', b''),
        ('One value only', b'One value only'),
        ([1, 2, 3], INVALID),
    ]),
]))
def test_bag_conversion(tag, to_what, inp, exp):
    # The difference between simple conversion and bag conversion is that
    # the second argument to conv() is not the same as tag.type.  Currently
    # we only test bag conversion cases where the second argument is 'Text'.
    tag = TAG_CACHE[tag]
    if to_what == 'python':
        conv = tag._convert_to_python
    else:
        conv = tag._convert_to_string
    if exp is INVALID:
        with pytest.raises(INVALID):
            conv(inp, 'Text')
    else:
        assert conv(inp, 'Text') == exp


def test_set_value():
    tag = XmpTag(
        'Xmp.xmp.ModifyDate', DT(2005, 9, 7, 15, 9, 51, tz=('-', 7, 0))
    )
    old_value = tag.value
    tag.value = DT(2009, 4, 22, 8, 30, 27)
    assert tag.value != old_value


def test_set_value_empty():
    tag = XmpTag('Xmp.dc.creator')
    assert tag.type == 'seq ProperName'
    with pytest.raises(ValueError):
        tag.value = []
    tag = XmpTag('Xmp.dc.title')
    assert tag.type == 'Lang Alt'
    with pytest.raises(ValueError):
        tag.value = {}


def test_set_value_incorrect_type():
    # Expecting a list of values
    tag = XmpTag('Xmp.dc.publisher')
    assert tag.type == 'bag ProperName'
    with pytest.raises(TypeError):
        tag.value = None
    with pytest.raises(TypeError):
        tag.value = 'bleh'

    # Expecting a dictionary mapping language codes to values
    tag = XmpTag('Xmp.dc.description')
    assert tag.type == 'Lang Alt'
    with pytest.raises(TypeError):
        tag.value = None
    with pytest.raises(TypeError):
        tag.value = ['bleh']


def test_set_value_basestring_for_langalt():
    tag = XmpTag('Xmp.dc.Description')
    tag.value = 'bleh'
    assert tag.value == 'bleh'
