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

from pyexiv2.metadata import ImageMetadata
from pyexiv2.xmp import (
    register_namespace, unregister_namespace, unregister_namespaces
)
from .helpers import D, EMPTY_JPG_DATA

# Dublin Core XML namespace, which is built-in as the 'dc' prefix
DC_NAME = 'http://purl.org/dc/elements/1.1/'


@pytest.fixture
def metadata():
    m = ImageMetadata.from_buffer(EMPTY_JPG_DATA)
    m.read()
    return m


def test_name_must_end_with_slash():
    with pytest.raises(ValueError):
        register_namespace('foobar', 'foo')
    with pytest.raises(ValueError):
        unregister_namespace('foobar')


def test_register_and_unregister():
    name = 'blah/'
    prefix = 'bla'
    register_namespace(name, prefix)
    unregister_namespace(name)


def test_cannot_register_builtin():
    # Cannot overwrite the built-in .dc. prefix
    with pytest.raises(KeyError):
        register_namespace('foobar/', 'dc')

    # _Can_ give another prefix the same meaning
    register_namespace(DC_NAME, 'notdc')
    # unregistration will zap the most recent prefix associated with the name
    unregister_namespace(DC_NAME)


def test_cannot_register_twice():
    name = 'foobar/'
    prefix = 'boo'
    register_namespace(name, prefix)
    try:
        with pytest.raises(KeyError):
            register_namespace(name, prefix)
    finally:
        unregister_namespace(name)


def test_cannot_unregister_builtin():
    with pytest.raises(KeyError):
        # Dublin Core builtin namespace
        unregister_namespace(DC_NAME)


def test_cannot_unregister_nonexistent():
    with pytest.raises(KeyError):
        unregister_namespace('boofar/')


def test_cannot_unregister_twice():
    name = 'bleh/'
    prefix = 'ble'
    register_namespace(name, prefix)
    unregister_namespace(name)
    with pytest.raises(KeyError):
        unregister_namespace(name)


def test_cannot_set_unregistered(metadata):
    assert len(metadata.xmp_keys) == 0
    key = 'Xmp.foo.bar'
    value = 'foobar'
    with pytest.raises(KeyError):
        metadata[key] = value


def test_register_and_set(metadata):
    register_namespace('foobar/', 'bar')
    try:
        key = 'Xmp.bar.foo'
        value = 'foobar'
        metadata[key] = value
        assert key in metadata.xmp_keys
    finally:
        unregister_namespace('foobar/')


def test_can_only_set_text_values(metadata):
    # At the moment custom namespaces only support setting simple text
    # values.
    key = 'Xmp.far.foo'
    register_namespace('foobar/', 'far')
    try:
        # array value not supported
        with pytest.raises(NotImplementedError):
            metadata[key] = ['foo', 'bar']

        # lang alt value not supported
        with pytest.raises(NotImplementedError):
            metadata[key] = {'x-default': 'foo', 'fr-FR': 'bar'}

        # simple text value is supported
        metadata[key] = 'simple text value'
        assert metadata[key].raw_value == b'simple text value'

        # python objects stored as simple text values are supported
        value = D.today()
        dt = '%04d-%02d-%02d' % (value.year, value.month, value.day)
        metadata[key] = value
        assert metadata[key].raw_value == dt

    finally:
        unregister_namespace('foobar/')


def test_unregister_invalidates_keys_in_ns(metadata):
    name = 'blih/'
    prefix = 'bli'
    key = 'Xmp.' + prefix + '.blu'
    register_namespace(name, prefix)
    try:
        metadata[key] = 'foobar'
        assert key in metadata.xmp_keys
    finally:
        unregister_namespace(name)

    with pytest.raises(KeyError):
        metadata.write()


def test_unregister_all_ns(metadata):
    # Unregistering all custom namespaces will always succeed,
    # even if there are no custom namespaces registered.
    unregister_namespaces()

    name = 'blop/'
    prefix = 'blo'
    register_namespace(name, prefix)
    metadata['Xmp.%s.bar' % prefix] = 'foobar'
    name2 = 'blup/'
    prefix2 = 'blu'
    register_namespace(name2, prefix2)
    metadata['Xmp.%s.bar' % prefix2] = 'foobar'
    unregister_namespaces()
    with pytest.raises(KeyError):
        metadata['Xmp.%s.baz' % prefix] = 'foobaz'
    with pytest.raises(KeyError):
        metadata['Xmp.%s.baz' % prefix2] = 'foobaz'
