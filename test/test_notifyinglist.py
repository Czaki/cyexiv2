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

from pyexiv2.utils import ListenerInterface, NotifyingList


class SimpleListener(ListenerInterface):
    def __init__(self):
        self.changes = 0

    def contents_changed(self):
        self.changes += 1


@pytest.fixture
def values():
    return NotifyingList([5, 7, 9, 14, 57, 3, 2])


def test_no_listener(values):
    # No listener is registered, so none is called, but the list
    # should still be modified as expected.
    values[3] = 13
    assert values == [5, 7, 9, 13, 57, 3, 2]

    del values[5]
    assert values == [5, 7, 9, 13, 57, 2]

    values.append(17)
    assert values == [5, 7, 9, 13, 57, 2, 17]

    values.extend([11, 22])
    assert values == [5, 7, 9, 13, 57, 2, 17, 11, 22]

    values.insert(4, 24)
    assert values == [5, 7, 9, 13, 24, 57, 2, 17, 11, 22]

    x = values.pop()
    assert x == 22
    assert values == [5, 7, 9, 13, 24, 57, 2, 17, 11]

    values.remove(9)
    assert values == [5, 7, 13, 24, 57, 2, 17, 11]

    values.reverse()
    assert values == [11, 17, 2, 57, 24, 13, 7, 5]

    values.sort()
    assert values == [2, 5, 7, 11, 13, 17, 24, 57]

    values += [8, 4]
    assert values == [2, 5, 7, 11, 13, 17, 24, 57, 8, 4]

    values[3:4] = [8, 4]
    assert values == [2, 5, 7, 8, 4, 13, 17, 24, 57, 8, 4]

    del values[3:5]
    assert values == [2, 5, 7, 13, 17, 24, 57, 8, 4]

    values *= 3
    assert values == [
        2, 5, 7, 13, 17, 24, 57, 8, 4,
        2, 5, 7, 13, 17, 24, 57, 8, 4,
        2, 5, 7, 13, 17, 24, 57, 8, 4
    ]


def test_listener_interface(values):
    # None of the listener methods are implemented, so they will all
    # throw, but this happens _after_ the modification, which still
    # sticks.
    values.register_listener(ListenerInterface())

    with pytest.raises(NotImplementedError):
        values[3] = 13
    assert values == [5, 7, 9, 13, 57, 3, 2]

    with pytest.raises(NotImplementedError):
        del values[5]
    assert values == [5, 7, 9, 13, 57, 2]

    with pytest.raises(NotImplementedError):
        values.append(17)
    assert values == [5, 7, 9, 13, 57, 2, 17]

    with pytest.raises(NotImplementedError):
        values.extend([11, 22])
    assert values == [5, 7, 9, 13, 57, 2, 17, 11, 22]

    with pytest.raises(NotImplementedError):
        values.insert(4, 24)
    assert values == [5, 7, 9, 13, 24, 57, 2, 17, 11, 22]

    x = None
    with pytest.raises(NotImplementedError):
        x = values.pop()
    # the assignment to x did not happen, but the list mutation did
    assert x is None
    assert values == [5, 7, 9, 13, 24, 57, 2, 17, 11]

    with pytest.raises(NotImplementedError):
        values.remove(9)
    assert values == [5, 7, 13, 24, 57, 2, 17, 11]

    with pytest.raises(NotImplementedError):
        values.reverse()
    assert values == [11, 17, 2, 57, 24, 13, 7, 5]

    with pytest.raises(NotImplementedError):
        values.sort()
    assert values == [2, 5, 7, 11, 13, 17, 24, 57]

    with pytest.raises(NotImplementedError):
        values += [8, 4]
    assert values == [2, 5, 7, 11, 13, 17, 24, 57, 8, 4]

    with pytest.raises(NotImplementedError):
        values[3:4] = [8, 4]
    assert values == [2, 5, 7, 8, 4, 13, 17, 24, 57, 8, 4]

    with pytest.raises(NotImplementedError):
        del values[3:5]
    assert values == [2, 5, 7, 13, 17, 24, 57, 8, 4]

    with pytest.raises(NotImplementedError):
        values *= 3
    assert values == [
        2, 5, 7, 13, 17, 24, 57, 8, 4,
        2, 5, 7, 13, 17, 24, 57, 8, 4,
        2, 5, 7, 13, 17, 24, 57, 8, 4
    ]


def register_listeners(values, n):
    listeners = [SimpleListener() for _ in range(n)]
    for l in listeners:
        values.register_listener(l)
    return listeners


def check_listeners(listeners, expected_changes):
    for l in listeners:
        assert l.changes == expected_changes


def test_setitem(values):
    listeners = register_listeners(values, 3)
    values[3] = 13
    assert values == [5, 7, 9, 13, 57, 3, 2]
    check_listeners(listeners, 1)

    with pytest.raises(IndexError):
        values[9] = 27
    assert values == [5, 7, 9, 13, 57, 3, 2]
    check_listeners(listeners, 1)


def test_delitem(values):
    listeners = register_listeners(values, 3)
    del values[5]
    assert values == [5, 7, 9, 14, 57, 2]
    check_listeners(listeners, 1)

    with pytest.raises(IndexError):
        del values[9]
    assert values == [5, 7, 9, 14, 57, 2]
    check_listeners(listeners, 1)


def test_append(values):
    listeners = register_listeners(values, 3)
    values.append(17)
    assert values == [5, 7, 9, 14, 57, 3, 2, 17]
    check_listeners(listeners, 1)


def test_extend(values):
    listeners = register_listeners(values, 3)
    values.extend([11, 22])
    assert values == [5, 7, 9, 14, 57, 3, 2, 11, 22]
    check_listeners(listeners, 1)

    with pytest.raises(TypeError):
        values.extend(26)
    assert values == [5, 7, 9, 14, 57, 3, 2, 11, 22]
    check_listeners(listeners, 1)


def test_insert(values):
    listeners = register_listeners(values, 3)
    values.insert(4, 24)
    assert values == [5, 7, 9, 14, 24, 57, 3, 2]
    check_listeners(listeners, 1)


def test_pop(values):
    listeners = register_listeners(values, 3)
    values.pop()
    assert values == [5, 7, 9, 14, 57, 3]
    check_listeners(listeners, 1)

    values.pop(4)
    assert values == [5, 7, 9, 14, 3]
    check_listeners(listeners, 2)

    values.pop(-2)
    assert values == [5, 7, 9, 3]
    check_listeners(listeners, 3)

    with pytest.raises(IndexError):
        values.pop(33)
    assert values == [5, 7, 9, 3]
    check_listeners(listeners, 3)


def test_remove(values):
    listeners = register_listeners(values, 3)
    values.remove(9)
    assert values == [5, 7, 14, 57, 3, 2]
    check_listeners(listeners, 1)

    with pytest.raises(ValueError):
        values.remove(33)
    assert values == [5, 7, 14, 57, 3, 2]
    check_listeners(listeners, 1)


def test_reverse(values):
    listeners = register_listeners(values, 3)
    values.reverse()
    assert values == [2, 3, 57, 14, 9, 7, 5]
    check_listeners(listeners, 1)


def test_sort(values):
    listeners = register_listeners(values, 3)
    values.sort()
    assert values == [2, 3, 5, 7, 9, 14, 57]
    check_listeners(listeners, 1)

    values.sort(key=lambda x: x * x)
    assert values == [2, 3, 5, 7, 9, 14, 57]
    check_listeners(listeners, 2)

    values.sort(reverse=True)
    assert values == [57, 14, 9, 7, 5, 3, 2]
    check_listeners(listeners, 3)


def test_iadd(values):
    listeners = register_listeners(values, 3)
    values += [44, 31, 19]
    assert values == [5, 7, 9, 14, 57, 3, 2, 44, 31, 19]
    check_listeners(listeners, 1)


def test_imul(values):
    listeners = register_listeners(values, 3)
    values *= 3
    assert values == [
        5, 7, 9, 14, 57, 3, 2,
        5, 7, 9, 14, 57, 3, 2,
        5, 7, 9, 14, 57, 3, 2
    ]
    check_listeners(listeners, 1)


def test_setslice(values):
    listeners = register_listeners(values, 3)

    # Basic slicing (of the form [i:j])
    values[2:4] = [3, 4]
    assert values == [5, 7, 3, 4, 57, 3, 2]
    check_listeners(listeners, 1)

    values[3:5] = [77, 8, 12]
    assert values == [5, 7, 3, 77, 8, 12, 3, 2]
    check_listeners(listeners, 2)

    values[2:5] = [1, 0]
    assert values == [5, 7, 1, 0, 12, 3, 2]
    check_listeners(listeners, 3)

    values[0:2] = []
    assert values == [1, 0, 12, 3, 2]
    check_listeners(listeners, 4)

    values[2:2] = [7, 5]
    assert values == [1, 0, 7, 5, 12, 3, 2]
    check_listeners(listeners, 5)

    # With negative indexes
    values[4:-2] = [9]
    assert values == [1, 0, 7, 5, 9, 3, 2]
    check_listeners(listeners, 6)

    values[-2:1] = [6, 4]
    assert values == [1, 0, 7, 5, 9, 6, 4, 3, 2]
    check_listeners(listeners, 7)

    values[-5:-2] = [8]
    assert values == [1, 0, 7, 5, 8, 3, 2]
    check_listeners(listeners, 8)

    # With missing (implicit) indexes
    values[:2] = [4]
    assert values == [4, 7, 5, 8, 3, 2]
    check_listeners(listeners, 9)

    values[4:] = [1]
    assert values == [4, 7, 5, 8, 1]
    check_listeners(listeners, 10)

    values[:] = [5, 7, 9, 14, 57, 3, 2]
    assert values == [5, 7, 9, 14, 57, 3, 2]
    check_listeners(listeners, 11)


def test_delslice(values):
    listeners = register_listeners(values, 3)

    # Basic slicing (of the form [i:j])
    del values[2:3]
    assert values == [5, 7, 14, 57, 3, 2]
    check_listeners(listeners, 1)

    del values[2:2]
    assert values == [5, 7, 14, 57, 3, 2]
    check_listeners(listeners, 2)

    # With negative indexes
    del values[4:-1]
    assert values == [5, 7, 14, 57, 2]
    check_listeners(listeners, 3)

    del values[-1:5]
    assert values == [5, 7, 14, 57]
    check_listeners(listeners, 4)

    del values[-2:-1]
    assert values == [5, 7, 57]
    check_listeners(listeners, 5)

    # With missing (implicit) indexes
    del values[:1]
    assert values == [7, 57]
    check_listeners(listeners, 6)

    del values[1:]
    assert values == [7]
    check_listeners(listeners, 7)

    del values[:]
    assert values == []
    check_listeners(listeners, 8)
