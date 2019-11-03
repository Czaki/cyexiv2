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

from pyexiv2.iptc import IptcTag, IptcValueError
from .helpers import D, T, DT, LazyTagCreator, expand_conversions

# The Iptc.Application2.Preview tag contains raw binary data (normally
# a thumbnail image) which, for historical reasons, gets stuffed into
# a Unicode string by this library.  This is the (nonsensical)
# sequence of Unicode codepoints used to test that behavior.
#
# FIXME: Tags whose content type is "Undefined" should probably be
# treated as byte strings instead, but that is a potentially breaking
# change and requires further investigation.
BINARY_TAG_CONTENTS = (
    '\ufffd\u006c\u006a\u0031\ufffd\u0065\u007f\u0045\u03df\ufffd\u0075\ufffd'
    '\ufffd\ufffd\u0006\ufffd\u0004\u14bb\u037e\u0043\u0028\ufffd\u0053\u0070'
    '\u0049\u005d\ufffd\u001c\ufffd\ufffd\u0051\u0049\ufffd\u007d'
)

TAG_TEMPLATES = {
    'Short': 'Iptc.Envelope.FileFormat',
    'String': 'Iptc.Application2.Subject',
    'Date': 'Iptc.Envelope.DateSent',
    'Time': 'Iptc.Envelope.TimeSent',
    'Undefined': 'Iptc.Application2.Preview',
}
TAG_CACHE = LazyTagCreator(IptcTag, TAG_TEMPLATES)
INVALID = IptcValueError


@pytest.mark.parametrize("tag, to_what, inp, exp", expand_conversions([
    ("Short", "python", [
        ('23', 23),
        ('+5628', 5628),
        ('-4', -4),
        ('abc', INVALID),
        ('5,64', INVALID),
        ('47.0001', INVALID),
        ('1E3', INVALID),
    ]),
    ("Short", "string", [
        (123, '123'),
        (-57, '-57'),
        ('invalid', INVALID),
        (3.14, INVALID),
    ]),

    ("String", "python", [
        ('Some text', 'Some text'),
        (
            'Some text with exotic chàräctérʐ.',
            'Some text with exotic chàräctérʐ.'
        ),
    ]),
    ("String", "string", [
        ('Some text', b'Some text'),
        (
            'Some text with exotic chàräctérʐ.',
            b'Some text with exotic '
            b'ch\xc3\xa0r\xc3\xa4ct\xc3\xa9r\xca\x90.'
        ),
        (None, INVALID),
    ]),
    ("Date", "python", [
        ('1999-10-13', D(1999, 10, 13)),
        ('invalid', INVALID),
        ('11/10/1983', INVALID),
        ('-1000', INVALID),
        ('2009-02', INVALID),
        ('2009-10-32', INVALID),
        ('2009-02-24T22:12:54', INVALID),
    ]),
    ("Date", "string", [
        (D(2009, 2, 4), '2009-02-04'),
        (D(1899, 12, 31), '1899-12-31'),
        (D(1999, 10, 13), '1999-10-13'),
        (DT(2009, 2, 4), '2009-02-04'),
        (DT(1899, 12, 31), '1899-12-31'),
        (DT(2009, 2, 4, 10, 52, 37), '2009-02-04'),
        (DT(1899, 12, 31, 23, 59, 59), '1899-12-31'),
        ('invalid', INVALID),
        (None, INVALID),
    ]),

    ("Time", "python", [
        ('05:03:54+00:00', T(5, 3, 54)),
        ('05:03:54+06:00', T(5, 3, 54, tz=('+', 6, 0))),
        ('05:03:54-10:30', T(5, 3, 54, tz=('-', 10, 30))),
        ('invalid', INVALID),
        ('23:12:42', INVALID),
        ('25:12:42+00:00', INVALID),
        ('21:77:42+00:00', INVALID),
        ('21:12:98+00:00', INVALID),
        ('081242+0000', INVALID),
    ]),
    ("Time", "string", [
        (T(10, 52, 4), '10:52:04+00:00'),
        (T(10, 52, 4, 574), '10:52:04+00:00'),
        (T(10, 52, 4, tz=None), '10:52:04+00:00'),
        (T(10, 52, 4, tz=('+', 5, 30)), '10:52:04+05:30'),
        (T(10, 52, 4, tz=('-', 4, 0)), '10:52:04-04:00'),
        (DT(1899, 12, 31, 23, 59, 59), '23:59:59+00:00'),
        (DT(2007, 2, 7, 10, 52, 4), '10:52:04+00:00'),
        (DT(1899, 12, 31, 23, 59, 59, 999), '23:59:59+00:00'),
        (DT(2007, 2, 7, 10, 52, 4, 478), '10:52:04+00:00'),
        (DT(1899, 12, 31, 23, 59, 59, tz=None), '23:59:59+00:00'),
        (DT(2007, 2, 7, 10, 52, 4, tz=None), '10:52:04+00:00'),
        (
            DT(1899, 12, 31, 23, 59, 59,
               tz=('+', 5, 30)), '23:59:59+05:30'
        ),
        (DT(2007, 2, 7, 10, 52, 4, tz=('+', 5, 30)), '10:52:04+05:30'),
        (
            DT(1899, 12, 31, 23, 59, 59,
               tz=('-', 4, 0)), '23:59:59-04:00'
        ),
        (DT(2007, 2, 7, 10, 52, 4, tz=('-', 4, 0)), '10:52:04-04:00'),
        ('invalid', INVALID),
    ]),

    ("Undefined", "python", [
        ('Some binary data.', 'Some binary data.'),
        (BINARY_TAG_CONTENTS, BINARY_TAG_CONTENTS),
    ]),
    ("Undefined", "string", [
        ('Some binary data.', 'Some binary data.'),
        (BINARY_TAG_CONTENTS, BINARY_TAG_CONTENTS),
        (None, INVALID),
    ]),
]))
def test_conversion(tag, to_what, inp, exp):
    tag = TAG_CACHE[tag]
    if to_what == 'python':
        conv = tag._convert_to_python
    else:
        conv = tag._convert_to_string
    if exp is IptcValueError:
        with pytest.raises(IptcValueError):
            conv(inp)
    else:
        assert conv(inp) == exp


def test_set_single_value_raises():
    tag = IptcTag('Iptc.Application2.City', ['Seattle'])
    with pytest.raises(TypeError):
        tag.value = 'Barcelona'


def test_set_value():
    tag = IptcTag('Iptc.Application2.City', ['Seattle'])
    old_value = tag.value
    tag.value = ['Barcelona']
    assert tag.value != old_value


def test_set_raw_value_invalid():
    tag = IptcTag('Iptc.Envelope.DateSent')
    with pytest.raises(ValueError):
        tag.raw_value = ['foo']


def test_set_value_non_repeatable():
    tag = IptcTag('Iptc.Application2.ReleaseDate')
    value = [D.today(), D.today()]
    with pytest.raises(KeyError):
        tag.value = value
