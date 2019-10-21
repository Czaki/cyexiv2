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
# version 3 as published by the Free Software Foundation.
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

"""
Manipulation of EXIF, IPTC and XMP metadata and thumbnails embedded in images.

The ImageMetadata class provides read/write access to all the metadata and
the various thumbnails embedded in an image file such as JPEG and TIFF files.

Metadata is accessed through tag classes (ExifTag, IptcTag, XmpTag)
and the tag values are conveniently wrapped in python objects.
For example, a tag containing a date/time information for the image
(e.g. Exif.Photo.DateTimeOriginal) will be represented by a python
datetime.datetime object.

A typical use of this binding would be:

>>> import pyexiv2
>>> metadata = pyexiv2.ImageMetadata('test/smiley.jpg')
>>> metadata.read()
>>> print(metadata.exif_keys)
['Exif.Image.ImageDescription', 'Exif.Image.XResolution',
 'Exif.Image.YResolution', 'Exif.Image.ResolutionUnit', 'Exif.Image.Software',
 'Exif.Image.DateTime', 'Exif.Image.Artist', 'Exif.Image.Copyright',
 'Exif.Image.ExifTag', 'Exif.Photo.Flash', 'Exif.Photo.PixelXDimension',
 'Exif.Photo.PixelYDimension']
>>> print(metadata['Exif.Image.DateTime'].value)
2004-07-13 21:23:44
>>> import datetime
>>> metadata['Exif.Image.DateTime'].value = datetime.datetime.today()
>>> metadata.write()
"""

from . import _libexiv2
from .exif import ExifValueError, ExifTag, ExifThumbnail
from .iptc import IptcValueError, IptcTag
from .metadata import ImageMetadata
from .preview import Preview
from .utils import (
    FixedOffset, NotifyingList, undefined_to_string, string_to_undefined,
    GPSCoordinate
)
from .xmp import (
    XmpValueError, XmpTag, register_namespace, unregister_namespace,
    unregister_namespaces
)


def _make_version(version_info):
    return '.'.join(str(i) for i in version_info)


#: A tuple containing the three components of the version number:
#: major, minor, micro.
version_info = (0, 8, 0, "dev0")

#: The version of the module as a string (major.minor.micro).
__version__ = _make_version(version_info)

#: A tuple containing the three components of the version number of libexiv2:
#: major, minor, micro.
exiv2_version_info = _libexiv2.exiv2_version_info

#: The version of libexiv2 as a string (major.minor.micro).
__exiv2_version__ = _make_version(exiv2_version_info)

__all__ = [
    'ExifTag',
    'ExifThumbnail',
    'ExifValueError',
    'FixedOffset',
    'GPSCoordinate',
    'ImageMetadata',
    'IptcTag',
    'IptcValueError',
    'NotifyingList',
    'Preview',
    'XmpTag',
    'XmpValueError',
    '__exiv2_version__',
    '__version__',
    'exif',
    'exiv2_version_info',
    'iptc',
    'metadata',
    'preview',
    'register_namespace',
    'string_to_undefined',
    'undefined_to_string',
    'unregister_namespace',
    'unregister_namespaces',
    'utils',
    'version_info',
    'xmp',
]
