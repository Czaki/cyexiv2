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

from pyexiv2.utils import DateTimeFormatter
from .helpers import D, T, DT, TD


@pytest.mark.parametrize("offset, timedelta", [
    ('+05:00', {'hours': 5}),
    ('+05:00', {'minutes': 300}),
    ('+05:12', {'hours': 5, 'minutes': 12}),
    ('+03:00', {'seconds': 10800}),
    ('-04:00', {'hours': -4}),
    ('-04:18', {'minutes': -258}),
    ('-02:12', {'hours': -2, 'minutes': -12}),
    ('-02:46', {'seconds': -10000}),
])
def test_timedelta_to_offset(offset, timedelta):
    assert DateTimeFormatter.timedelta_to_offset(TD(**timedelta)) == offset


@pytest.mark.parametrize("formatted, ts", [
    ('1899:12:31 00:00:00', DT(1899, 12, 31)),
    ('1899:12:31 23:00:00', DT(1899, 12, 31, 23)),
    ('1899:12:31 23:59:00', DT(1899, 12, 31, 23, 59)),
    ('1899:12:31 23:59:59', DT(1899, 12, 31, 23, 59, 59)),
    ('1899:12:31 23:59:59', DT(1899, 12, 31, 23, 59, 59, 999999)),
    ('1899:12:31 23:59:59', DT(1899, 12, 31, 23, 59, 59, tz=None)),
    ('1899:12:31 23:59:59', DT(1899, 12, 31, 23, 59, 59, tz=('+', 5))),
    ('2011:08:08 19:03:37', DT(2011, 8, 8, 19, 3, 37)),
    # date
    ('1899:12:31', D(1899, 12, 31)),
    ('2011:08:08', D(2011, 8, 8)),
])
def test_exif_valid(formatted, ts):
    assert DateTimeFormatter.exif(ts) == formatted


@pytest.mark.parametrize("bad_ts", [
    None,
    3.14,
])
def test_exif_invalid(bad_ts):
    with pytest.raises(TypeError):
        DateTimeFormatter.exif(bad_ts)


@pytest.mark.parametrize("formatted, ts", [
    # datetime
    ('1899-12-31', DT(1899, 12, 31)),
    ('1899-12-31', DT(1899, 12, 31, 23)),
    ('1899-12-31', DT(1899, 12, 31, 23, 59)),
    ('1899-12-31', DT(1899, 12, 31, 23, 59, 59)),
    ('1899-12-31', DT(1899, 12, 31, 23, 59, 59, 999999)),
    ('1899-12-31', DT(1899, 12, 31, 23, 59, 59, tz=None)),
    ('1899-12-31', DT(1899, 12, 31, 23, 59, 59, tz=('+', 5))),
    # date
    ('1899-12-31', D(1899, 12, 31)),
    ('2011-08-08', D(2011, 8, 8)),
])
def test_iptc_date_valid(formatted, ts):
    assert DateTimeFormatter.iptc_date(ts) == formatted


@pytest.mark.parametrize("bad_ts", [
    None,
    3.14,
])
def test_iptc_date_invalid(bad_ts):
    with pytest.raises(TypeError):
        DateTimeFormatter.iptc_date(bad_ts)


@pytest.mark.parametrize("formatted, ts", [
    # datetime
    ('00:00:00+00:00', DT(1899, 12, 31)),
    ('23:00:00+00:00', DT(1899, 12, 31, 23)),
    ('23:59:00+00:00', DT(1899, 12, 31, 23, 59)),
    ('23:59:59+00:00', DT(1899, 12, 31, 23, 59, 59)),
    ('23:59:59+00:00', DT(1899, 12, 31, 23, 59, 59, 999999)),
    ('23:59:59+00:00', DT(1899, 12, 31, 23, 59, 59, tz=None)),
    ('23:59:59+05:00', DT(1899, 12, 31, 23, 59, 59, tz=('+', 5))),
    ('19:03:37+00:00', DT(2011, 8, 8, 19, 3, 37)),

    # time
    ('23:00:00+00:00', T(23)),
    ('23:59:00+00:00', T(23, 59)),
    ('23:59:59+00:00', T(23, 59, 59)),
    ('23:59:59+00:00', T(23, 59, 59, 999999)),
    ('23:59:59+00:00', T(23, 59, 59, tz=None)),
    ('23:59:59+05:00', T(23, 59, 59, tz=('+', 5))),
    ('19:03:37+00:00', T(19, 3, 37)),
])
def test_iptc_time_valid(formatted, ts):
    assert DateTimeFormatter.iptc_time(ts) == formatted


@pytest.mark.parametrize("bad_ts", [
    None,
    3.14,
])
def test_iptc_time_invalid(bad_ts):
    with pytest.raises(TypeError):
        DateTimeFormatter.iptc_time(bad_ts)


@pytest.mark.parametrize("formatted, ts", [
    # datetime
    ('1899-12-31', DT(1899, 12, 31)),
    ('1899-12-31', DT(1899, 12, 31, tz=None)),
    ('1899-12-31T23:59Z', DT(1899, 12, 31, 23, 59)),
    ('1899-12-31T23:59Z', DT(1899, 12, 31, 23, 59, tz=None)),
    ('1899-12-31T23:59+03:00', DT(1899, 12, 31, 23, 59, tz=('+', 3))),
    ('1899-12-31T23:59:59Z', DT(1899, 12, 31, 23, 59, 59)),
    ('1899-12-31T23:59:59Z', DT(1899, 12, 31, 23, 59, 59, tz=None)),
    ('1899-12-31T23:59:59+03:00', DT(1899, 12, 31, 23, 59, 59, tz=('+', 3))),
    ('1899-12-31T23:59:59.999999Z', DT(1899, 12, 31, 23, 59, 59, 999999)),
    (
        '1899-12-31T23:59:59.999999Z',
        DT(1899, 12, 31, 23, 59, 59, 999999, tz=None)
    ),
    (
        '1899-12-31T23:59:59.999999+03:00',
        DT(1899, 12, 31, 23, 59, 59, 999999, tz=('+', 3))
    ),
    ('2011-08-11T09:23:44Z', DT(2011, 8, 11, 9, 23, 44)),

    # date
    ('1899-12-31', D(1899, 12, 31)),
    ('2011-08-08', D(2011, 8, 8)),
])
def test_xmp_valid(formatted, ts):
    assert DateTimeFormatter.xmp(ts) == formatted


@pytest.mark.parametrize("bad_ts", [
    None,
    3.14,
])
def test_xmp_invalid(bad_ts):
    with pytest.raises(TypeError):
        DateTimeFormatter.xmp(bad_ts)
