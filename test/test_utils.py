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

from pyexiv2.utils import (
    undefined_to_string, string_to_undefined, Fraction, is_fraction,
    make_fraction, fraction_to_string
)


# For many pairs of inputs, undefined_to_string and string_to_undefined are
# inverse functions.
@pytest.mark.parametrize("uval, sval", [
    ("", ""),
    ("48 50 50 49", "0221"),
    (" ".join(str(i) for i in range(256)),
     "".join(chr(i) for i in range(256))),
])
def test_undefined_to_string_invertible(uval, sval):
    sxval = undefined_to_string(uval)
    uxval = string_to_undefined(sval)
    assert sval == sxval
    assert uval == uxval
    # these imply u2s(s2u(s)) == s and s2u(u2s(u)) == u


# However, undefined_to_string is many-to-one; for some inputs,
# it will produce a string that does not map back to the original.
@pytest.mark.parametrize("uval, sval", [
    ("48 50 50 49 ", "0221"),
    ("48 50 50 49\t", "0221"),
])
def test_undefined_to_string_oneway(uval, sval):
    assert undefined_to_string(uval) == sval


# undefined_to_string also has inputs for which it will raise ValueError.
@pytest.mark.parametrize("uval", [
    "foo",
    "48 50  50 49",
])
def test_undefined_to_string_invalid(uval):
    with pytest.raises(ValueError):
        undefined_to_string(uval)


@pytest.mark.parametrize("is_f, obj", [
    (True, Fraction()),
    (True, Fraction(3, 5)),
    (True, Fraction(Fraction(4, 5))),
    (True, Fraction('3/2')),
    (True, Fraction('-4/5')),
    (False, 3 / 5),
    (False, '3/5'),
    (False, '2.7'),
    (False, 2.7),
    (False, 'notafraction'),
    (False, None),
])
def test_is_fraction(is_f, obj):
    assert is_fraction(obj) == is_f


@pytest.mark.parametrize("args, frac", [
    ((3, 5), (3, 5)),
    ((-3, 5), (-3, 5)),
    (('3/2',), (3, 2)),
    (('-3/4',), (-3, 4)),
    (('0/0',), (0, 1)),
])
def test_make_fraction_valid(args, frac):
    assert make_fraction(*args) == Fraction(*frac)


@pytest.mark.parametrize("exc, args", [
    (ZeroDivisionError, (3, 0)),
    (ZeroDivisionError, ('3/0',)),
    (TypeError, (5, 3, 2)),
    (TypeError, (None,)),
])
def test_make_fraction_invalid(exc, args):
    with pytest.raises(exc):
        make_fraction(*args)


@pytest.mark.parametrize("frac, as_str", [
    ((3, 5), '3/5'),
    ((-3, 5), '-3/5'),
    ((0, 1), '0/1'),
])
def test_fraction_to_string_valid(frac, as_str):
    assert fraction_to_string(Fraction(*frac)) == as_str


@pytest.mark.parametrize("bad_args", [
    (None,),
    ("invalid",),
    (0.5,),
    (1, 2),
])
def test_fraction_to_string_invalid(bad_args):
    with pytest.raises(TypeError):
        fraction_to_string(*bad_args)
