# -*- coding: utf-8 -*-

# ******************************************************************************
#
# Copyright (C) 2009-2011 Olivier Tilloy <olivier@tilloy.net>
# Copyright (C) 2015 Vincent Vande Vyvre <vincent.vandevyvre@oqapy.eu>
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

from pyexiv2.metadata import ImageMetadata
from pyexiv2.xmp import (
    XmpTag, XmpValueError, register_namespace, unregister_namespace,
    unregister_namespaces
)

from .testutils import EMPTY_JPG_DATA, D, DT, FR


class TestXmpTag(unittest.TestCase):
    def do_test_convert_to_python(
        self, name, tagtype, convtype=None, valid=[], invalid=[]
    ):
        if convtype is None:
            convtype = tagtype

        tag = XmpTag(name)
        self.assertEqual(tag.type, tagtype)

        for inp, exp in valid:
            self.assertEqual(tag._convert_to_python(inp, convtype), exp)

        for inp in invalid:
            try:
                self.assertRaises(
                    XmpValueError, tag._convert_to_python, inp, convtype
                )
            except AssertionError as e:
                e.args = (e.args[0] + " (inp=%s)" % repr(inp), )
                raise

    def do_test_convert_to_string(
        self, name, tagtype, convtype=None, valid=[], invalid=[]
    ):
        if convtype is None:
            convtype = tagtype

        tag = XmpTag(name)
        self.assertEqual(tag.type, tagtype)

        for inp, exp in valid:
            self.assertEqual(tag._convert_to_string(inp, convtype), exp)

        for inp in invalid:
            try:
                self.assertRaises(
                    XmpValueError, tag._convert_to_string, inp, convtype
                )
            except AssertionError as e:
                e.args = (e.args[0] + " (inp=%s)" % repr(inp), )
                raise

    def test_convert_to_python_bag(self):
        self.do_test_convert_to_python(
            'Xmp.dc.Subject',
            tagtype='',
            convtype='Text',
            valid=[
                ('', ''),
                ('One value only', 'One value only'),
            ]
        )

    def test_convert_to_string_bag(self):
        self.do_test_convert_to_string(
            'Xmp.dc.Subject',
            tagtype='',
            convtype='Text',
            valid=[
                ('', b''),
                ('One value only', b'One value only'),
            ],
            invalid=[
                [1, 2, 3],
            ]
        )

    def test_convert_to_python_boolean(self):
        self.do_test_convert_to_python(
            'Xmp.xmpRights.Marked',
            'Boolean',
            valid=[
                ('True', True),
                ('False', False),
            ],
            invalid=[
                'invalid',
                None,
            ]
        )

    def test_convert_to_string_boolean(self):
        self.do_test_convert_to_string(
            'Xmp.xmpRights.Marked',
            'Boolean',
            valid=[
                (True, 'True'),
                (False, 'False'),
            ],
            invalid=[
                'invalid',
                None,
            ]
        )

    def test_convert_to_python_date(self):
        self.do_test_convert_to_python(
            'Xmp.xmp.CreateDate',
            'Date',
            valid=[
                ('1999', D(1999, 1, 1)),
                ('1999-10', D(1999, 10, 1)),
                ('1999-10-13', D(1999, 10, 13)),
                ('1999-10-13T05:03Z', DT(1999, 10, 13, 5, 3)),
                (
                    '1999-10-13T05:03+06:00',
                    DT(1999, 10, 13, 5, 3, tz=('+', 6, 0))
                ),
                (
                    '1999-10-13T05:03-06:00',
                    DT(1999, 10, 13, 5, 3, tz=('-', 6, 0))
                ),
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
            ],
            invalid=[
                'invalid',
                '11/10/1983',
                '-1000',
                '2009-13',
                '2009-10-32',
                '2009-10-30T25:12Z',
                '2009-10-30T23:67Z',
                '2009-01-22T21',
            ]
        )

    def test_convert_to_string_date(self):
        self.do_test_convert_to_string(
            'Xmp.xmp.CreateDate',
            'Date',
            valid=[
                (D(2009, 2, 4), '2009-02-04'),
                (D(1899, 12, 31), '1899-12-31'),
                (D(1999, 10, 13), '1999-10-13'),
                (DT(1999, 10, 13, 5, 3), '1999-10-13T05:03Z'),
                (DT(1899, 12, 31, 23, 59), '1899-12-31T23:59Z'),
                (DT(1999, 10, 13, 5, 3), '1999-10-13T05:03Z'),
                (DT(1899, 12, 31, 23, 59), '1899-12-31T23:59Z'),
                (
                    DT(1999, 10, 13, 5, 3,
                       tz=('+', 5, 30)), '1999-10-13T05:03+05:30'
                ),
                (
                    DT(1999, 10, 13, 5, 3,
                       tz=('-', 11, 30)), '1999-10-13T05:03-11:30'
                ),
                (
                    DT(1899, 12, 31, 23, 59,
                       tz=('+', 5, 30)), '1899-12-31T23:59+05:30'
                ),
                (DT(1999, 10, 13, 5, 3, 27), '1999-10-13T05:03:27Z'),
                (DT(1899, 12, 31, 23, 59, 59), '1899-12-31T23:59:59Z'),
                (DT(1999, 10, 13, 5, 3, 27), '1999-10-13T05:03:27Z'),
                (DT(1899, 12, 31, 23, 59, 59), '1899-12-31T23:59:59Z'),
                (
                    DT(1999, 10, 13, 5, 3, 27,
                       tz=('+', 5, 30)), '1999-10-13T05:03:27+05:30'
                ),
                (
                    DT(1999, 10, 13, 5, 3, 27,
                       tz=('-', 11, 30)), '1999-10-13T05:03:27-11:30'
                ),
                (
                    DT(1899, 12, 31, 23, 59, 59,
                       tz=('+', 5, 30)), '1899-12-31T23:59:59+05:30'
                ),
                (
                    DT(1999, 10, 13, 5, 3, 27,
                       124300), '1999-10-13T05:03:27.1243Z'
                ),
                (
                    DT(1899, 12, 31, 23, 59, 59,
                       124300), '1899-12-31T23:59:59.1243Z'
                ),
                (
                    DT(1999, 10, 13, 5, 3, 27,
                       124300), '1999-10-13T05:03:27.1243Z'
                ),
                (
                    DT(1899, 12, 31, 23, 59, 59,
                       124300), '1899-12-31T23:59:59.1243Z'
                ),
                (
                    DT(1999, 10, 13, 5, 3, 27, 124300,
                       tz=('+', 5, 30)), '1999-10-13T05:03:27.1243+05:30'
                ),
                (
                    DT(1999, 10, 13, 5, 3, 27, 124300,
                       tz=('-', 11, 30)), '1999-10-13T05:03:27.1243-11:30'
                ),
                (
                    DT(1899, 12, 31, 23, 59, 59, 124300,
                       tz=('+', 5, 30)), '1899-12-31T23:59:59.1243+05:30'
                ),
            ],
            invalid=[
                'invalid',
                None,
            ]
        )

    def test_convert_to_python_integer(self):
        self.do_test_convert_to_python(
            'Xmp.xmpMM.SaveID',
            'Integer',
            valid=[
                ('23', 23),
                ('+5628', 5628),
                ('-4', -4),
            ],
            invalid=[
                # Invalid values
                'abc',
                '5,64',
                '47.0001',
                '1E3',
            ]
        )

    def test_convert_to_string_integer(self):
        self.do_test_convert_to_string(
            'Xmp.xmpMM.SaveID',
            'Integer',
            valid=[(123, '123'), (-57, '-57')],
            invalid=['invalid', 3.14],
        )

    def test_convert_to_python_mimetype(self):
        self.do_test_convert_to_python(
            'Xmp.dc.format',
            'MIMEType',
            valid=[
                ('image/jpeg', ('image', 'jpeg')),
                ('video/ogg', ('video', 'ogg')),
            ],
            invalid=[
                'invalid',
                'image-jpeg',
            ]
        )

    def test_convert_to_string_mimetype(self):
        self.do_test_convert_to_string(
            'Xmp.dc.format',
            'MIMEType',
            valid=[
                (('image', 'jpeg'), 'image/jpeg'),
                (('video', 'ogg'), 'video/ogg'),
            ],
            invalid=[
                'invalid',
                ('image', ),
            ]
        )

    def test_convert_to_python_propername(self):
        self.do_test_convert_to_python(
            'Xmp.photoshop.CaptionWriter',
            'ProperName',
            valid=[
                ('Gérard', 'Gérard'),
                ('Python Software Foundation', 'Python Software Foundation'),
            ],
            invalid=[
                None,
            ]
        )

    def test_convert_to_string_propername(self):
        self.do_test_convert_to_string(
            'Xmp.photoshop.CaptionWriter',
            'ProperName',
            valid=[
                ('Gérard', b'G\xc3\xa9rard'),
                ('Python Software Foundation', b'Python Software Foundation'),
            ],
            invalid=[
                None,
            ]
        )

    def test_convert_to_python_text(self):
        self.do_test_convert_to_python(
            'Xmp.dc.source',
            'Text',
            valid=[
                ('Some text.', 'Some text.'),
                ((
                    b'Some text with exotic '
                    b'ch\xc3\xa0r\xc3\xa4ct\xc3\xa9r\xca\x90.'
                ), 'Some text with exotic chàräctérʐ.'),
            ],
            invalid=[
                None,
            ]
        )

    def test_convert_to_string_text(self):
        self.do_test_convert_to_string(
            'Xmp.dc.source',
            'Text',
            valid=[
                ('Some text', b'Some text'),
                (
                    'Some text with exotic chàräctérʐ.', (
                        b'Some text with exotic '
                        b'ch\xc3\xa0r\xc3\xa4ct\xc3\xa9r\xca\x90.'
                    )
                ),
            ],
            invalid=[
                None,
            ]
        )

    def test_convert_to_python_uri(self):
        self.do_test_convert_to_python(
            'Xmp.xmpMM.DocumentID',
            'URI',
            valid=[
                ('http://example.com', 'http://example.com'),
                ('https://example.com', 'https://example.com'),
                (
                    'http://localhost:8000/resource',
                    'http://localhost:8000/resource'
                ),
                (
                    'uuid:9A3B7F52214211DAB6308A7391270C13',
                    'uuid:9A3B7F52214211DAB6308A7391270C13'
                ),
            ],
            invalid=[
                None,
            ]
        )

    def test_convert_to_string_uri(self):
        self.do_test_convert_to_string(
            'Xmp.xmpMM.DocumentID',
            'URI',
            valid=[
                ('http://example.com', b'http://example.com'),
                ('https://example.com', b'https://example.com'),
                (
                    'http://localhost:8000/resource',
                    b'http://localhost:8000/resource'
                ),
                (
                    'uuid:9A3B7F52214211DAB6308A7391270C13',
                    b'uuid:9A3B7F52214211DAB6308A7391270C13'
                ),
            ],
            invalid=[
                None,
            ]
        )

    def test_convert_to_python_url(self):
        self.do_test_convert_to_python(
            'Xmp.xmp.BaseURL',
            'URL',
            valid=[
                ('http://example.com', 'http://example.com'),
                ('https://example.com', 'https://example.com'),
                (
                    'http://localhost:8000/resource',
                    'http://localhost:8000/resource'
                ),
            ],
            invalid=[
                None,
            ]
        )

    def test_convert_to_string_url(self):
        self.do_test_convert_to_string(
            'Xmp.xmp.BaseURL',
            'URL',
            valid=[
                ('http://example.com', b'http://example.com'),
                ('https://example.com', b'https://example.com'),
                (
                    'http://localhost:8000/resource',
                    b'http://localhost:8000/resource'
                ),
            ],
            invalid=[
                None,
            ]
        )

    def test_convert_to_python_rational(self):
        self.do_test_convert_to_python(
            'Xmp.xmpDM.videoPixelAspectRatio',
            'Rational',
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

    def test_convert_to_string_rational(self):
        self.do_test_convert_to_string(
            'Xmp.xmpDM.videoPixelAspectRatio',
            'Rational',
            valid=[
                (FR(5, 3), '5/3'),
                (FR(-5, 3), '-5/3'),
            ],
            invalid=[
                'invalid',
                5 / 3,  # float
            ]
        )

    # TODO: other types

    def test_set_value(self):
        tag = XmpTag(
            'Xmp.xmp.ModifyDate', DT(2005, 9, 7, 15, 9, 51, tz=('-', 7, 0))
        )
        old_value = tag.value
        tag.value = DT(2009, 4, 22, 8, 30, 27)
        self.assertNotEqual(tag.value, old_value)

    def test_set_value_empty(self):
        tag = XmpTag('Xmp.dc.creator')
        self.assertEqual(tag.type, 'seq ProperName')
        self.assertRaises(ValueError, setattr, tag, 'value', [])
        tag = XmpTag('Xmp.dc.title')
        self.assertEqual(tag.type, 'Lang Alt')
        self.assertRaises(ValueError, setattr, tag, 'value', {})

    def test_set_value_incorrect_type(self):
        # Expecting a list of values
        tag = XmpTag('Xmp.dc.publisher')
        self.assertEqual(tag.type, 'bag ProperName')
        self.assertRaises(TypeError, setattr, tag, 'value', None)
        self.assertRaises(TypeError, setattr, tag, 'value', 'bleh')
        # Expecting a dictionary mapping language codes to values
        tag = XmpTag('Xmp.dc.description')
        self.assertEqual(tag.type, 'Lang Alt')
        self.assertRaises(TypeError, setattr, tag, 'value', None)
        self.assertRaises(TypeError, setattr, tag, 'value', ['bleh'])

    def test_set_value_basestring_for_langalt(self):
        tag = XmpTag('Xmp.dc.Description')
        tag.value = 'bleh'
        self.assertEqual(tag.value, 'bleh')


class TestXmpNamespaces(unittest.TestCase):
    def setUp(self):
        self.metadata = ImageMetadata.from_buffer(EMPTY_JPG_DATA)
        self.metadata.read()

    def test_not_registered(self):
        self.assertEqual(len(self.metadata.xmp_keys), 0)
        key = 'Xmp.foo.bar'
        value = 'foobar'
        self.assertRaises(KeyError, self.metadata.__setitem__, key, value)

    def test_name_must_end_with_slash(self):
        self.assertRaises(ValueError, register_namespace, 'foobar', 'foo')
        self.assertRaises(ValueError, unregister_namespace, 'foobar')

    def test_cannot_register_builtin(self):
        self.assertRaises(KeyError, register_namespace, 'foobar/', 'dc')

    def test_cannot_register_twice(self):
        name = 'foobar/'
        prefix = 'boo'
        register_namespace(name, prefix)
        self.assertRaises(KeyError, register_namespace, name, prefix)

    def test_register_and_set(self):
        register_namespace('foobar/', 'bar')
        key = 'Xmp.bar.foo'
        value = 'foobar'
        self.metadata[key] = value
        self.assertTrue(key in self.metadata.xmp_keys)

    def test_can_only_set_text_values(self):
        # At the moment custom namespaces only support setting simple text
        # values.
        register_namespace('foobar/', 'far')
        key = 'Xmp.far.foo'
        value = D.today()
        dt = '%04d-%02d-%02d' % (value.year, value.month, value.day)
        self.metadata[key] = value
        self.assertEqual(self.metadata[key].raw_value, dt)
        value = ['foo', 'bar']
        self.assertRaises(
            NotImplementedError, self.metadata.__setitem__, key, value
        )
        value = {'x-default': 'foo', 'fr-FR': 'bar'}
        self.assertRaises(
            NotImplementedError, self.metadata.__setitem__, key, value
        )
        value = 'simple text value'
        self.metadata[key] = value

    def test_cannot_unregister_builtin(self):
        name = 'http://purl.org/dc/elements/1.1/'  # DC builtin namespace
        self.assertRaises(KeyError, unregister_namespace, name)

    def test_cannot_unregister_inexistent(self):
        name = 'boofar/'
        self.assertRaises(KeyError, unregister_namespace, name)

    def test_cannot_unregister_twice(self):
        name = 'bleh/'
        prefix = 'ble'
        register_namespace(name, prefix)
        unregister_namespace(name)
        self.assertRaises(KeyError, unregister_namespace, name)

    def test_unregister(self):
        name = 'blah/'
        prefix = 'bla'
        register_namespace(name, prefix)
        unregister_namespace(name)

    def test_unregister_invalidates_keys_in_ns(self):
        name = 'blih/'
        prefix = 'bli'
        register_namespace(name, prefix)
        key = 'Xmp.%s.blu' % prefix
        self.metadata[key] = 'foobar'
        self.assertTrue(key in self.metadata.xmp_keys)
        unregister_namespace(name)
        self.assertRaises(KeyError, self.metadata.write)

    def test_unregister_all_ns(self):
        # Unregistering all custom namespaces will always succeed,
        # even if there are no custom namespaces registered.
        unregister_namespaces()

        name = 'blop/'
        prefix = 'blo'
        register_namespace(name, prefix)
        self.metadata['Xmp.%s.bar' % prefix] = 'foobar'
        name2 = 'blup/'
        prefix2 = 'blu'
        register_namespace(name2, prefix2)
        self.metadata['Xmp.%s.bar' % prefix2] = 'foobar'
        unregister_namespaces()
        self.assertRaises(
            KeyError, self.metadata.__setitem__, 'Xmp.%s.baz' % prefix,
            'foobaz'
        )
        self.assertRaises(
            KeyError, self.metadata.__setitem__, 'Xmp.%s.baz' % prefix2,
            'foobaz'
        )
