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

from pyexiv2.utils import Fraction as FRt, GPSCoordinate as GPS
from .helpers import load_image, FR, D, Dt, DT


def check_type_and_value(tag, etype, evalue):
    assert isinstance(tag.value, etype)
    assert tag.value == evalue


def check_type_and_values(tag, etype, evalues):
    for value in tag.value:
        assert isinstance(value, etype)
    assert tag.value == evalues


@pytest.fixture(scope='module')
def testImage1():
    return load_image('DSCF_0273.JPG', 'af48f3889f68369e5e3ab75f42a21234')


@pytest.fixture(scope='module')
def testImage2():
    return load_image('exiv2-bug540.jpg', '64d4b7eab1e78f1f6bfb3c966e99eef2')


@pytest.mark.parametrize("key, ktype, value", [
    ('Exif.Image.XResolution', FRt, FR(72, 1)),
    ('Exif.Image.YResolution', FRt, FR(72, 1)),
    ('Exif.Image.ResolutionUnit', int, 2),
    ('Exif.Image.Software', str, 'Digital Camera FinePix S4800 Ver1.00'),
    ('Exif.Image.DateTime', Dt, DT(2015, 1, 17, 13, 53, 3, tz=None)),
    ('Exif.Image.Artist', str, 'Vincent Vande Vyvre'),
    ('Exif.Photo.ApertureValue', FRt, FR(6, 1)),
    ('Exif.Photo.FNumber', FRt, FR(8, 1)),
    ('Exif.Photo.PixelXDimension', int, 250),
    ('Exif.Photo.PixelYDimension', int, 140),
])
def test_read_metadata_exif(key, ktype, value, testImage1):
    check_type_and_value(testImage1[key], ktype, value)


@pytest.mark.parametrize("key, ktype, values", [
    ('Iptc.Application2.Caption', str, ['S']),
    ('Iptc.Application2.Byline', str, ['Vincent Vande Vyvre']),
    ('Iptc.Application2.0x00d7', str, ['www.oqapy.eu']),
    ('Iptc.Application2.Keywords', str, ['bruxelles botanique']),
    ('Iptc.Application2.Copyright', str, ['2013 Vincent Vande Vyvre']),
])
def test_read_metadata_iptc(key, ktype, values, testImage1):
    check_type_and_values(testImage1[key], ktype, values)


@pytest.mark.parametrize("key, ktype, value", [
    ('Xmp.dc.creator', list, ['Ian Britton']),
    ('Xmp.dc.description', dict, {
        'x-default': 'Communications'
    }),
    (
        'Xmp.dc.rights', dict, {
            'x-default': 'ian Britton - FreeFoto.com'
        }
    ),
    ('Xmp.dc.source', str, 'FreeFoto.com'),
    ('Xmp.dc.subject', list, ['Communications']),
    ('Xmp.dc.title', dict, {
        'x-default': 'Communications'
    }),
    ('Xmp.exif.ApertureValue', FRt, FR(8, 1)),
    ('Xmp.exif.BrightnessValue', FRt, FR(333, 1280)),
    ('Xmp.exif.ColorSpace', int, 1),
    ('Xmp.exif.DateTimeOriginal', Dt, DT(2002, 7, 13, 15, 58, 28)),
    ('Xmp.exif.ExifVersion', str, '0200'),
    ('Xmp.exif.ExposureBiasValue', FRt, FR(-13, 20)),
    ('Xmp.exif.ExposureProgram', int, 4),
    ('Xmp.exif.FNumber', FRt, FR(3, 5)),
    ('Xmp.exif.FileSource', int, 0),
    ('Xmp.exif.FlashpixVersion', str, '0100'),
    ('Xmp.exif.FocalLength', FRt, FR(0, 1)),
    ('Xmp.exif.FocalPlaneResolutionUnit', int, 2),
    ('Xmp.exif.FocalPlaneXResolution', FRt, FR(3085, 256)),
    ('Xmp.exif.FocalPlaneYResolution', FRt, FR(3085, 256)),
    ('Xmp.exif.GPSLatitude', GPS, GPS.from_string('54,59.380000N')),
    ('Xmp.exif.GPSLongitude', GPS, GPS.from_string('1,54.850000W')),
    ('Xmp.exif.GPSMapDatum', str, 'WGS84'),
    ('Xmp.exif.GPSTimeStamp', Dt, DT(2002, 7, 13, 14, 58, 24)),
    ('Xmp.exif.GPSVersionID', str, '2.0.0.0'),
    ('Xmp.exif.ISOSpeedRatings', list, [0]),
    ('Xmp.exif.MeteringMode', int, 5),
    ('Xmp.exif.PixelXDimension', int, 2400),
    ('Xmp.exif.PixelYDimension', int, 1600),
    ('Xmp.exif.SceneType', int, 0),
    ('Xmp.exif.SensingMethod', int, 2),
    ('Xmp.exif.ShutterSpeedValue', FRt, FR(30827, 3245)),
    ('Xmp.pdf.Keywords', str, 'Communications'),
    ('Xmp.photoshop.AuthorsPosition', str, 'Photographer'),
    ('Xmp.photoshop.CaptionWriter', str, 'Ian Britton'),
    ('Xmp.photoshop.Category', str, 'BUS'),
    ('Xmp.photoshop.City', str, ' '),
    ('Xmp.photoshop.Country', str, 'Ubited Kingdom'),
    ('Xmp.photoshop.Credit', str, 'Ian Britton'),
    ('Xmp.photoshop.DateCreated', D, D(2002, 6, 20)),
    ('Xmp.photoshop.Headline', str, 'Communications'),
    ('Xmp.photoshop.State', str, ' '),
    ('Xmp.photoshop.SupplementalCategories', list, ['Communications']),
    ('Xmp.photoshop.Urgency', int, 5),
    ('Xmp.tiff.Artist', str, 'Ian Britton'),
    ('Xmp.tiff.BitsPerSample', list, [8]),
    ('Xmp.tiff.Compression', int, 6),
    (
        'Xmp.tiff.Copyright', dict, {
            'x-default': 'ian Britton - FreeFoto.com'
        }
    ),
    (
        'Xmp.tiff.ImageDescription', dict, {
            'x-default': 'Communications'
        }
    ),
    ('Xmp.tiff.ImageLength', int, 400),
    ('Xmp.tiff.ImageWidth', int, 600),
    ('Xmp.tiff.Make', str, 'FUJIFILM'),
    ('Xmp.tiff.Model', str, 'FinePixS1Pro'),
    ('Xmp.tiff.Orientation', int, 1),
    ('Xmp.tiff.ResolutionUnit', int, 2),
    ('Xmp.tiff.Software', str, 'Adobe Photoshop 7.0'),
    ('Xmp.tiff.XResolution', FRt, FR(300, 1)),
    ('Xmp.tiff.YCbCrPositioning', int, 2),
    ('Xmp.tiff.YResolution', FRt, FR(300, 1)),
    ('Xmp.xmp.CreateDate', Dt, DT(2002, 7, 13, 15, 58, 28)),
    ('Xmp.xmp.ModifyDate', Dt, DT(2002, 7, 19, 13, 28, 10)),
    ('Xmp.xmpBJ.JobRef', list, []),
    ('Xmp.xmpBJ.JobRef[1]', str, ''),
    ('Xmp.xmpBJ.JobRef[1]/stJob:name', str, 'Photographer'),
    (
        'Xmp.xmpMM.DocumentID', str,
        'adobe:docid:photoshop:84d4dba8-9b11-11d6-895d-c4d063a70fb0'
    ),
    ('Xmp.xmpRights.Marked', bool, True),
    ('Xmp.xmpRights.WebStatement', str, 'www.freefoto.com'),
])
def test_read_metadata_xmp(key, ktype, value, testImage2):
    check_type_and_value(testImage2[key], ktype, value)
