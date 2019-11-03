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

from collections import namedtuple
import datetime
import hashlib
import os.path

from pyexiv2.metadata import ImageMetadata
from pyexiv2.utils import FixedOffset, make_fraction

#: A 1x1 JPG image with no tags.
EMPTY_JPG_DATA = (
    b'\xff\xd8\xff\xe0\x00\x10\x4a\x46\x49\x46\x00\x01\x01\x01\x00\x48\x00\x48'
    b'\x00\x00\xff\xdb\x00\x43\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
    b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
    b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
    b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
    b'\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00'
    b'\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02'
    b'\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03'
    b'\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01\x7d\x01\x02\x03\x00\x04\x11'
    b'\x05\x12\x21\x31\x41\x06\x13\x51\x61\x07\x22\x71\x14\x32\x81\x91\xa1\x08'
    b'\x23\x42\xb1\xc1\x15\x52\xd1\xf0\x24\x33\x62\x72\x82\x09\x0a\x16\x17\x18'
    b'\x19\x1a\x25\x26\x27\x28\x29\x2a\x34\x35\x36\x37\x38\x39\x3a\x43\x44\x45'
    b'\x46\x47\x48\x49\x4a\x53\x54\x55\x56\x57\x58\x59\x5a\x63\x64\x65\x66\x67'
    b'\x68\x69\x6a\x73\x74\x75\x76\x77\x78\x79\x7a\x83\x84\x85\x86\x87\x88\x89'
    b'\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9'
    b'\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9'
    b'\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8'
    b'\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01'
    b'\x00\x00\x3f\x00\x92\xbf\xff\xd9'
)

#: A JPG wrapper around a TIFF image.  Not all common tools can handle this,
#: but libexiv2 can.
UNUSUAL_JPG_DATA = (
    b'\xff\xd8\xff\xe0\x00\x10\x4a\x46\x49\x46\x00\x01\x01\x01\x00\x48\x00\x48'
    b'\x00\x00\xff\xe1\x00\x36\x45\x78\x69\x66\x00\x00\x49\x49\x2a\x00\x08\x00'
    b'\x00\x00\x01\x00\x32\x01\x02\x00\x14\x00\x00\x00\x1a\x00\x00\x00\x00\x00'
    b'\x00\x00\x32\x30\x31\x30\x3a\x30\x33\x3a\x31\x38\x20\x31\x33\x3a\x33\x39'
    b'\x3a\x35\x38\x00\xff\xdb\x00\x43\x00\x05\x03\x04\x04\x04\x03\x05\x04\x04'
    b'\x04\x05\x05\x05\x06\x07\x0c\x08\x07\x07\x07\x07\x0f\x0b\x0b\x09\x0c\x11'
    b'\x0f\x12\x12\x11\x0f\x11\x11\x13\x16\x1c\x17\x13\x14\x1a\x15\x11\x11\x18'
    b'\x21\x18\x1a\x1d\x1d\x1f\x1f\x1f\x13\x17\x22\x24\x22\x1e\x24\x1c\x1e\x1f'
    b'\x1e\xff\xdb\x00\x43\x01\x05\x05\x05\x07\x06\x07\x0e\x08\x08\x0e\x1e\x14'
    b'\x11\x14\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e'
    b'\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e\x1e'
    b'\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01\x22\x00\x02\x11\x01\x03\x11'
    b'\x01\xff\xc4\x00\x15\x00\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00'
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x14\x01\x01\x00\x00'
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xc4\x00\x14'
    b'\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    b'\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xb2\xc0\x07\xff'
    b'\xd9'
)

#: The value of the Exif.Image.DateTime tag of UNUSUAL_JPG_DATA.
UNUSUAL_JPG_DATETIME = '2010-03-18T13:39:58'


def get_absolute_file_path(*filepath):
    """
    Return the absolute file path for the file path given in argument,
    considering it is relative to the caller script's directory.
    """
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *filepath)


def md5sum_file(filename):
    """
    Compute the MD5 hash of the file FILENAME.
    """
    with open(filename, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


FileInfo = namedtuple('FileInfo', ('filepath', 'filedata', 'md5sum'))


def load_data_file(name, md5sum):
    filepath = get_absolute_file_path("data", name)
    with open(filepath, 'rb') as fp:
        filedata = fp.read()
    assert hashlib.md5(filedata).hexdigest() == md5sum
    return FileInfo(filepath, filedata, md5sum)


def load_image(name, md5sum):
    fi = load_data_file(name, md5sum)
    m = ImageMetadata.from_buffer(fi.filedata)
    m.read()
    return m


class LazyTagCreator(dict):
    """Cache for {Exif,Iptc,Xmp}Tag objects.
    """
    def __init__(self, tagcons, tmpl):
        dict.__init__(self)
        self._tagcons = tagcons
        self._tmpl = tmpl

    def __missing__(self, key):
        tmpl = self._tmpl[key]
        if isinstance(tmpl, tuple):
            tagkey = tmpl[0]
            tagtype = tmpl[1]
        else:
            tagkey = tmpl
            tagtype = key
        tag = self._tagcons(tagkey)
        assert tag.type == tagtype
        return tag


def expand_conversions(conversions):
    """Expand a table of conversions as used to parametrize
       e.g. test_exif.py::test_conversion."""
    for tag, to_what, cases in conversions:
        for inp, exp in cases:
            yield (tag, to_what, inp, exp)


# Shorthand for fraction, date, and datetime constructors.
FR = make_fraction
D = datetime.date
Dt = datetime.datetime
TD = datetime.timedelta


def T(h=0, mi=0, s=0, us=0, tz=()):
    if tz is None:
        return datetime.time(h, mi, s, us)
    else:
        return datetime.time(h, mi, s, us, tzinfo=FixedOffset(*tz))


def DT(y, mo, d, h=0, mi=0, s=0, us=0, tz=()):
    if tz is None:
        return datetime.datetime(y, mo, d, h, mi, s, us)
    else:
        return datetime.datetime(
            y, mo, d, h, mi, s, us, tzinfo=FixedOffset(*tz)
        )
