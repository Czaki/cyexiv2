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

import pyexiv2
from pyexiv2.utils import is_fraction, GPSCoordinate as GPS

from .testutils import get_absolute_file_path, md5sum_file, FR, D, Dt, DT

FRACTION = 'fraction'


class ReadMetadataTestCase(unittest.TestCase):
    """
    Test case on reading the metadata contained in a file.
    """
    def check_type_and_value(self, tag, etype, evalue):
        if etype == FRACTION:
            self.assertTrue(is_fraction(tag.value))
        else:
            self.assertTrue(isinstance(tag.value, etype))
        self.assertEqual(tag.value, evalue)

    def check_type_and_values(self, tag, etype, evalues):
        for value in tag.value:
            self.assertTrue(isinstance(value, etype))
        self.assertEqual(tag.value, evalues)

    def assertCorrectFile(self, filename, md5sum):
        """
        Ensure that the filename and the MD5 checksum match up.
        """
        self.assertEqual(md5sum_file(filename), md5sum)

    def testReadMetadata(self):
        """
        Perform various tests on reading the metadata contained in a file.
        """
        # Check that the reference file is not corrupted
        filepath = get_absolute_file_path('data', 'DSCF_0273.JPG')
        md5sum = 'af48f3889f68369e5e3ab75f42a21234'
        self.assertCorrectFile(filepath, md5sum)

        # Read the image metadata
        image = pyexiv2.ImageMetadata(filepath)
        image.read()

        # Exhaustive tests on the values of EXIF metadata
        exifTags = [
            ('Exif.Image.XResolution', FRACTION, FR(72, 1)),
            ('Exif.Image.YResolution', FRACTION, FR(72, 1)),
            ('Exif.Image.ResolutionUnit', int, 2),
            (
                'Exif.Image.Software', str,
                'Digital Camera FinePix S4800 Ver1.00'
            ),
            ('Exif.Image.DateTime', Dt, DT(2015, 1, 17, 13, 53, 3, tz=None)),
            ('Exif.Image.Artist', str, 'Vincent Vande Vyvre'),
            ('Exif.Photo.ApertureValue', FRACTION, FR(6, 1)),
            ('Exif.Photo.FNumber', FRACTION, FR(8, 1)),
            ('Exif.Photo.PixelXDimension', int, 250),
            ('Exif.Photo.PixelYDimension', int, 140),
        ]
        for key, ktype, value in exifTags:
            self.check_type_and_value(image[key], ktype, value)

        # Exhaustive tests on the values of IPTC metadata
        iptcTags = [
            ('Iptc.Application2.Caption', str, ['S']),
            ('Iptc.Application2.Byline', str, ['Vincent Vande Vyvre']),
            ('Iptc.Application2.0x00d7', str, ['www.oqapy.eu']),
            ('Iptc.Application2.Keywords', str, ['bruxelles botanique']),
            ('Iptc.Application2.Copyright', str, ['2013 Vincent Vande Vyvre']),
        ]
        for key, ktype, values in iptcTags:
            self.check_type_and_values(image[key], ktype, values)

    def testReadMetadataXMP(self):
        filepath = get_absolute_file_path('data', 'exiv2-bug540.jpg')
        md5sum = '64d4b7eab1e78f1f6bfb3c966e99eef2'
        self.assertCorrectFile(filepath, md5sum)

        # Read the image metadata
        image = pyexiv2.ImageMetadata(filepath)
        image.read()

        xmpTags = [
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
            ('Xmp.exif.ApertureValue', FRACTION, FR(8, 1)),
            ('Xmp.exif.BrightnessValue', FRACTION, FR(333, 1280)),
            ('Xmp.exif.ColorSpace', int, 1),
            ('Xmp.exif.DateTimeOriginal', Dt, DT(2002, 7, 13, 15, 58, 28)),
            ('Xmp.exif.ExifVersion', str, '0200'),
            ('Xmp.exif.ExposureBiasValue', FRACTION, FR(-13, 20)),
            ('Xmp.exif.ExposureProgram', int, 4),
            ('Xmp.exif.FNumber', FRACTION, FR(3, 5)),
            ('Xmp.exif.FileSource', int, 0),
            ('Xmp.exif.FlashpixVersion', str, '0100'),
            ('Xmp.exif.FocalLength', FRACTION, FR(0, 1)),
            ('Xmp.exif.FocalPlaneResolutionUnit', int, 2),
            ('Xmp.exif.FocalPlaneXResolution', FRACTION, FR(3085, 256)),
            ('Xmp.exif.FocalPlaneYResolution', FRACTION, FR(3085, 256)),
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
            ('Xmp.exif.ShutterSpeedValue', FRACTION, FR(30827, 3245)),
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
            ('Xmp.tiff.XResolution', FRACTION, FR(300, 1)),
            ('Xmp.tiff.YCbCrPositioning', int, 2),
            ('Xmp.tiff.YResolution', FRACTION, FR(300, 1)),
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
        ]
        for key, ktype, value in xmpTags:
            self.check_type_and_value(image[key], ktype, value)
