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

from pyexiv2.utils import GPSCoordinate as GPS


class TestGPSCoordinate(unittest.TestCase):
    def test_constructor(self):
        r = GPS(62, 58, 2, 'W')
        self.assertEqual(r.degrees, 62)
        self.assertEqual(r.minutes, 58)
        self.assertEqual(r.seconds, 2)
        self.assertEqual(r.direction, 'W')
        r = GPS(92, 58, 2, 'W')
        self.assertEqual(r.degrees, 92)
        self.assertEqual(r.minutes, 58)
        self.assertEqual(r.seconds, 2)
        self.assertEqual(r.direction, 'W')
        self.assertRaises(ValueError, GPS, -23, 58, 2, 'W')
        self.assertRaises(ValueError, GPS, 91, 58, 2, 'S')
        self.assertRaises(ValueError, GPS, 62, -23, 2, 'W')
        self.assertRaises(ValueError, GPS, 62, 61, 2, 'W')
        self.assertRaises(ValueError, GPS, 62, 58, -23, 'W')
        self.assertRaises(ValueError, GPS, 62, 58, 61, 'W')
        self.assertRaises(ValueError, GPS, 62, 58, 2, 'A')

    def test_read_only(self):
        r = GPS(62, 58, 2, 'W')
        trials = [
            ('degrees', 5),
            ('minutes', 5),
            ('seconds', 5),
            ('direction', 'S'),
        ]
        for attr, val in trials:
            self.assertRaises(AttributeError, setattr, r, attr, val)

    def test_from_string(self):
        self.assertEqual(GPS.from_string('54,59.3800N'), GPS(54, 59, 23, 'N'))
        self.assertEqual(GPS.from_string('1,54.850000W'), GPS(1, 54, 51, 'W'))
        self.assertRaises(ValueError, GPS.from_string, '51N')
        self.assertRaises(ValueError, GPS.from_string, '48 24 3 S')
        self.assertRaises(ValueError, GPS.from_string, '48°24\'3"S')
        self.assertRaises(ValueError, GPS.from_string, 'invalid')

    def test_to_string(self):
        self.assertEqual(str(GPS(54, 59, 23, 'N')), '54,59,23N')
