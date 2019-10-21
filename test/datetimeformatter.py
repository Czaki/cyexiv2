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

import unittest

from pyexiv2.utils import DateTimeFormatter as DTF

from .testutils import D, T, DT, TD


class TestDateTimeFormatter(unittest.TestCase):
    def test_timedelta_to_offset(self):
        cases = [
            ('+05:00', {'hours': 5}),
            ('+05:00', {'minutes': 300}),
            ('+05:12', {'hours': 5, 'minutes': 12}),
            ('+03:00', {'seconds': 10800}),
            ('-04:00', {'hours': -4}),
            ('-04:18', {'minutes': -258}),
            ('-02:12', {'hours': -2, 'minutes': -12}),
            ('-02:46', {'seconds': -10000}),
        ]  # yapf: disable
        for s, kwargs in cases:
            self.assertEqual(DTF.timedelta_to_offset(TD(**kwargs)), s)

    def test_exif(self):
        valid_cases = [
            # datetime
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
        ]
        for s, d in valid_cases:
            self.assertEqual(DTF.exif(d), s)

        invalid_cases = [
            None,
            3.14,
        ]
        for d in invalid_cases:
            self.assertRaises(TypeError, DTF.exif, d)

    def test_iptc_date(self):
        valid_cases = [
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
        ]
        for s, d in valid_cases:
            self.assertEqual(DTF.iptc_date(d), s)

        invalid_cases = [
            None,
            3.14,
        ]
        for d in invalid_cases:
            self.assertRaises(TypeError, DTF.iptc_date, d)

    def test_iptc_time(self):
        valid_cases = [
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
        ]
        for s, d in valid_cases:
            self.assertEqual(DTF.iptc_time(d), s)

        invalid_cases = [
            None,
            3.14,
        ]
        for d in invalid_cases:
            self.assertRaises(TypeError, DTF.iptc_time, d)

    def test_xmp(self):
        valid_cases = [
            # datetime
            ('1899-12-31', DT(1899, 12, 31)),
            ('1899-12-31', DT(1899, 12, 31, tz=None)),
            ('1899-12-31T23:59Z', DT(1899, 12, 31, 23, 59)),
            ('1899-12-31T23:59Z', DT(1899, 12, 31, 23, 59, tz=None)),
            ('1899-12-31T23:59+03:00', DT(1899, 12, 31, 23, 59, tz=('+', 3))),
            ('1899-12-31T23:59:59Z', DT(1899, 12, 31, 23, 59, 59)),
            ('1899-12-31T23:59:59Z', DT(1899, 12, 31, 23, 59, 59, tz=None)),
            (
                '1899-12-31T23:59:59+03:00',
                DT(1899, 12, 31, 23, 59, 59, tz=('+', 3))
            ),
            (
                '1899-12-31T23:59:59.999999Z',
                DT(1899, 12, 31, 23, 59, 59, 999999)
            ),
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
        ]
        for s, d in valid_cases:
            self.assertEqual(DTF.xmp(d), s)

        invalid_cases = [
            None,
            3.14,
        ]
        for d in invalid_cases:
            self.assertRaises(TypeError, DTF.xmp, d)
