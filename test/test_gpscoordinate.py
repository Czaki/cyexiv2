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

from pyexiv2.utils import GPSCoordinate as GPS


@pytest.mark.parametrize("deg, min, sec, dir, as_str", [
    (62, 58, 2, 'W', '62,58,2W'),
    (92, 58, 2, 'W', '92,58,2W'),
    (54, 59, 23, 'N', '54,59,23N'),
])
def test_constructor_valid(deg, min, sec, dir, as_str):
    r = GPS(deg, min, sec, dir)
    assert r.degrees == deg
    assert r.minutes == min
    assert r.seconds == sec
    assert r.direction == dir
    assert str(r) == as_str


@pytest.mark.parametrize("degrees, minutes, seconds, direction", [
    (-23, 58, 2, 'W'),
    (91, 58, 2, 'S'),
    (62, -23, 2, 'W'),
    (62, 61, 2, 'W'),
    (62, 58, -23, 'W'),
    (62, 58, 61, 'W'),
    (62, 58, 2, 'A'),
])
def test_constructor_invalid(degrees, minutes, seconds, direction):
    with pytest.raises(ValueError):
        GPS(degrees, minutes, seconds, direction)


@pytest.mark.parametrize("str, deg, min, sec, dir", [
    ('54,59.3800N', 54, 59, 23, 'N'),
    ('1,54.850000W', 1, 54, 51, 'W'),
])
def test_from_string_valid(str, deg, min, sec, dir):
    assert GPS.from_string(str) == GPS(deg, min, sec, dir)


@pytest.mark.parametrize("bad_str", [
    '51N',
    '48 24 3 S',
    '48°24\'3"S',
    'invalid',
])
def test_from_string_invalid(bad_str):
    with pytest.raises(ValueError):
        GPS.from_string(bad_str)


@pytest.mark.parametrize("attr, val", [
    ('degrees', 5),
    ('minutes', 5),
    ('seconds', 5),
    ('direction', 'S'),
])
def test_read_only(attr, val):
    r = GPS(62, 58, 2, 'W')
    with pytest.raises(AttributeError):
        setattr(r, attr, val)
