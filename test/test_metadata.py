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

import collections
import datetime
import itertools
import os
import shutil
import stat
import tempfile
import time

import pytest

from pyexiv2.metadata import ImageMetadata
from pyexiv2.exif import ExifTag
from pyexiv2.iptc import IptcTag
from pyexiv2.xmp import XmpTag
from pyexiv2.utils import make_fraction
from .helpers import EMPTY_JPG_DATA

# If these don't have the usual values, the octal permissions
# constants in various os.chmod() calls below are wrong.
assert stat.S_IREAD == 0o0400
assert stat.S_IWRITE == 0o0200
assert stat.S_IEXEC == 0o0100


@pytest.fixture(scope='module')
def scratch_directory():
    """A user-writable scratch directory which will be deleted after
       tests complete.  Used by the fixtures below.
    """
    with tempfile.TemporaryDirectory(prefix="cyexiv2-test-") as tdir:
        os.chmod(tdir, 0o0700)  # rwx------
        yield tdir


@pytest.fixture(scope='module')
def empty_directory(scratch_directory):
    """An empty, read-only directory.  The point of this fixture is that
       any pathname starting with 'tdir' is guaranteed not to exist.
    """
    emptydir = os.path.join(scratch_directory, 'empty')
    os.mkdir(emptydir)
    os.chmod(emptydir, 0o0500)  # r-x------
    return emptydir


@pytest.fixture(scope='module')
def jpg_with_tags(scratch_directory):
    """A JPEG file with several tags, used by a bunch of tests.
       This fixture creates the file itself and returns its pathname.
       The file is made read-only for safety.
       N.B. we use NamedTemporaryFile(delete=False) because we want to be
       able to close the initial file descriptor, to avoid tripping
       over Windows' exclusive file access rules.  Cleanup is handled
       by the teardown of the scratch_directory fixture.
    """
    with tempfile.NamedTemporaryFile(
        dir=scratch_directory, suffix='.jpg', delete=False
    ) as fp:
        fp.write(EMPTY_JPG_DATA)
        name = fp.name

    # Write some metadata
    m = ImageMetadata(name)
    m.read()
    m['Exif.Image.Make'] = 'EASTMAN KODAK COMPANY'
    m['Exif.Image.DateTime'] = datetime.datetime(2009, 2, 9, 13, 33, 20)
    m['Iptc.Application2.Caption'] = ['blabla']
    m['Iptc.Application2.DateCreated'] = [datetime.date(2004, 7, 13)]
    m['Xmp.dc.format'] = ('image', 'jpeg')
    m['Xmp.dc.subject'] = ['image', 'test', 'pyexiv2']
    m.comment = 'Hello World!'
    m.write()
    del m

    os.chmod(name, 0o0400)  # r--------
    return name


MetadataWithPath = collections.namedtuple(
    "MetadataWithPath", ("pathname", "metadata")
)


@pytest.fixture(scope='function')
def metadata_ro(jpg_with_tags):
    """A fresh *read-only* ImageMetadata object for the jpg_with_tags.
       Returns a 2-tuple (pathname, ImageMetadata).
       read() has not yet been called.  write() will fail.
    """
    return MetadataWithPath(jpg_with_tags, ImageMetadata(jpg_with_tags))


@pytest.fixture(scope='function')
def metadata_rw(jpg_with_tags, scratch_directory):
    """A fresh *writable* ImageMetadata object for a *copy* of the
       jpg_with_tags.  Returns a 2-tuple (pathname, ImageMetadata).
       read() has not yet been called.
    """
    (nfd, nname) = tempfile.mkstemp(suffix='.jpg', dir=scratch_directory)
    # create ofp first so that nfd is closed even if the second open throws
    with open(nfd, "wb") as ofp, open(jpg_with_tags, "rb") as ifp:
        shutil.copyfileobj(ifp, ofp)
    # nfd is now closed
    os.chmod(nname, 0o0600)  # rw-------
    return MetadataWithPath(nname, ImageMetadata(nname))


######################
# Test general methods
######################
@pytest.mark.parametrize("suite", [
    "metadata.write()",
    "metadata.dimensions",
    "metadata.mime_type",
    "metadata.exif_keys",
    "metadata.iptc_keys",
    "metadata.xmp_keys",
    "metadata.previews",
    "metadata.iptc_charset",
    "metadata.comment",
    "metadata.comment = 'foobar'",
    "del metadata.comment",

    "metadata._get_exif_tag('Exif.Image.Make')",
    "metadata._get_iptc_tag('Iptc.Application2.Caption')",
    "metadata._get_xmp_tag('Xmp.dc.format')",
    "metadata._set_exif_tag('Exif.Image.Make', 'foobar')",
    "metadata._set_iptc_tag('Iptc.Application2.Caption', ['foobar'])",
    "metadata._set_xmp_tag('Xmp.dc.format', ('foo', 'bar'))",
    "metadata._delete_exif_tag('Exif.Image.Make')",
    "metadata._delete_iptc_tag('Iptc.Application2.Caption')",
    "metadata._delete_xmp_tag('Xmp.dc.format')",
    "metadata.copy(other)",

    "metadata.exif_thumbnail.mime_type",
    "metadata.exif_thumbnail.extension",
    "metadata.exif_thumbnail.erase()",
    "metadata.exif_thumbnail.write_to_file(nonexistent_jpg)",
    "metadata.exif_thumbnail.set_from_file(empty_jpg)"
])
def test_not_read_raises(metadata_ro, scratch_directory, suite):
    # http://bugs.launchpad.net/pyexiv2/+bug/687373

    locals = {
        'metadata': metadata_ro.metadata,
    }
    if 'other' in suite:
        other = ImageMetadata.from_buffer(EMPTY_JPG_DATA)
        other.read()
        locals['other'] = other

    if 'nonexistent_jpg' in suite:
        # tempfile.mktemp would actually be safe here because we are
        # the only process that can write to the scratch_directory,
        # but then we'd have to suppress warnings.  This can be
        # cleaned up if and when thumb.write_to_file grows the ability
        # to write to a filelike.
        fd, pathname = tempfile.mkstemp(dir=scratch_directory, suffix='.jpg')
        os.close(fd)
        os.remove(pathname)
        locals['nonexistent_jpg'] = pathname

    if 'empty_jpg' in suite:
        with tempfile.NamedTemporaryFile(
            dir=scratch_directory, suffix='.jpg', delete=False
        ) as fp:
            fp.write(EMPTY_JPG_DATA)
            locals['empty_jpg'] = fp.name

    with pytest.raises(OSError):
        exec(suite, {}, locals)


def test_read(metadata_ro):
    m = metadata_ro.metadata
    with pytest.raises(OSError):
        m._image
    m.read()
    assert m._image is not None


def test_read_nonexistent_file(empty_directory):
    non_jpg = os.path.join(empty_directory, 'non.jpg')
    m = ImageMetadata(non_jpg)
    with pytest.raises(OSError):
        m.read()


def test_write_preserve_timestamps(metadata_rw):
    path = metadata_rw.pathname
    m = metadata_rw.metadata
    st = os.stat(path)

    m.read()
    m.comment = 'Yellow Submarine'
    time.sleep(1.1)
    m.write(preserve_timestamps=True)
    st2 = os.stat(path)

    # It may not have been possible to preserve the _exact_ timestamp.
    # Round to the nearest second before comparison.
    assert round(st.st_atime) == round(st2.st_atime)
    assert round(st.st_mtime) == round(st2.st_mtime)


def test_write_dont_preserve_timestamps(metadata_rw):
    path = metadata_rw.pathname
    m = metadata_rw.metadata
    st = os.stat(path)

    m.read()
    m.comment = 'Yellow Submarine'
    time.sleep(1.1)
    m.write(preserve_timestamps=False)
    st2 = os.stat(path)

    # m.write should have modified the mtime, and may or may not
    # have modified the atime, depending on mount options
    # (e.g. noatime, relatime).  See discussion at
    # <http://bugs.launchpad.net/pyexiv2/+bug/624999>.
    assert st.st_mtime != st2.st_mtime

    m.comment = 'Yesterday'
    time.sleep(1.1)
    m.write(preserve_timestamps=True)

    # metadata.write(preserve_timestamps=True) should not have
    # modified either the mtime or the atime, relative to what
    # they were at point 2.
    st3 = os.stat(path)
    assert round(st3.st_mtime) == round(st2.st_mtime)
    assert round(st3.st_atime) == round(st2.st_atime)


###########################
# Test EXIF-related methods
###########################


def test_exif_keys(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._keys['exif'] is None
    keys = m.exif_keys
    assert len(keys) == 2
    assert m._keys['exif'] == keys


def test_get_exif_tag(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._tags['exif'] == {}
    # Get an existing tag
    key = 'Exif.Image.Make'
    tag = m._get_exif_tag(key)
    assert isinstance(tag, ExifTag)
    assert m._tags['exif'][key] == tag
    # Try to get an nonexistent tag
    key = 'Exif.Photo.Sharpness'
    with pytest.raises(KeyError):
        m._get_exif_tag(key)


def test_set_exif_tag_wrong(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._tags['exif'] == {}
    # Try to set a tag with wrong type
    tag = 'Not an exif tag'
    with pytest.raises(TypeError):
        m._set_exif_tag(tag)
    assert m._tags['exif'] == {}


def test_set_exif_tag_create(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._tags['exif'] == {}
    # Create a new tag
    tag = ExifTag('Exif.Thumbnail.Orientation', 1)
    assert tag.key not in m.exif_keys
    m._set_exif_tag(tag.key, tag)
    assert tag.key in m.exif_keys
    assert m._tags['exif'] == {tag.key: tag}
    assert tag.key in m._image._exifKeys()
    assert (
        m._image._getExifTag(tag.key)._getRawValue().decode('ascii')
        == tag.raw_value
    )


def test_set_exif_tag_overwrite(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._tags['exif'] == {}
    # Overwrite an existing tag
    tag = ExifTag(
        'Exif.Image.DateTime', datetime.datetime(2009, 3, 20, 20, 32, 0)
    )
    m._set_exif_tag(tag.key, tag)
    assert m._tags['exif'] == {tag.key: tag}
    assert tag.key in m._image._exifKeys()
    assert (
        m._image._getExifTag(tag.key)._getRawValue().decode('ascii')
        == tag.raw_value
    )


def test_set_exif_tag_overwrite_already_cached(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._tags['exif'] == {}
    # Overwrite an existing tag already cached
    key = 'Exif.Image.Make'
    tag = m._get_exif_tag(key)
    assert m._tags['exif'][key] == tag
    new_tag = ExifTag(key, 'World Company')
    m._set_exif_tag(key, new_tag)
    assert m._tags['exif'] == {key: new_tag}
    assert key in m._image._exifKeys()
    assert (
        m._image._getExifTag(key)._getRawValue().decode('ascii')
        == new_tag.raw_value
    )


def test_set_exif_tag_direct_value_assignment(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._tags['exif'] == {}
    # Direct value assignment: pass a value instead of a fully-formed tag
    key = 'Exif.Thumbnail.Orientation'
    value = 1
    m._set_exif_tag(key, value)
    assert key in m.exif_keys
    assert key in m._image._exifKeys()
    tag = m._get_exif_tag(key)
    assert tag.value == value
    assert m._tags['exif'] == {key: tag}
    assert (
        m._image._getExifTag(key)._getRawValue().decode('ascii')
        == tag.raw_value
    )


def test_delete_exif_tag_inexistent(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    key = 'Exif.Image.Artist'
    with pytest.raises(KeyError):
        m._delete_exif_tag(key)


def test_delete_exif_tag_not_cached(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    key = 'Exif.Image.DateTime'
    assert m._tags['exif'] == {}
    assert key in m.exif_keys
    m._delete_exif_tag(key)
    assert m._tags['exif'] == {}
    assert key not in m.exif_keys


def test_delete_exif_tag_cached(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    key = 'Exif.Image.DateTime'
    assert key in m.exif_keys
    tag = m._get_exif_tag(key)
    assert m._tags['exif'][key] == tag
    m._delete_exif_tag(key)
    assert m._tags['exif'] == {}
    assert key not in m.exif_keys


###########################
# Test IPTC-related methods
###########################


def test_iptc_keys(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._keys['iptc'] is None
    keys = m.iptc_keys
    assert len(keys) == 2
    assert m._keys['iptc'] == keys


def test_get_iptc_tag(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._tags['iptc'] == {}
    # Get an existing tag
    key = 'Iptc.Application2.DateCreated'
    tag = m._get_iptc_tag(key)
    assert isinstance(tag, IptcTag)
    assert m._tags['iptc'][key] == tag
    # Try to get an nonexistent tag
    key = 'Iptc.Application2.Copyright'
    with pytest.raises(KeyError):
        m._get_iptc_tag(key)


def test_set_iptc_tag_wrong(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._tags['iptc'] == {}
    # Try to set a tag with wrong type
    tag = 'Not an iptc tag'
    with pytest.raises(TypeError):
        m._set_iptc_tag(tag)
    assert m._tags['iptc'] == {}


def test_set_iptc_tag_create(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._tags['iptc'] == {}
    # Create a new tag
    tag = IptcTag('Iptc.Application2.Writer', ['Nobody'])
    assert tag.key not in m.iptc_keys
    m._set_iptc_tag(tag.key, tag)
    assert tag.key in m.iptc_keys
    assert m._tags['iptc'] == {tag.key: tag}
    assert tag.key in m._image._iptcKeys()
    assert m._image._getIptcTag(tag.key)._getRawValues() == [b'Nobody']


def test_set_iptc_tag_overwrite(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._tags['iptc'] == {}
    # Overwrite an existing tag
    tag = IptcTag('Iptc.Application2.Caption', ['A picture.'])
    m._set_iptc_tag(tag.key, tag)
    assert m._tags['iptc'] == {tag.key: tag}
    assert tag.key in m._image._iptcKeys()
    assert m._image._getIptcTag(tag.key)._getRawValues() == [b'A picture.']


def test_set_iptc_tag_overwrite_already_cached(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._tags['iptc'] == {}
    # Overwrite an existing tag already cached
    key = 'Iptc.Application2.Caption'
    tag = m._get_iptc_tag(key)
    assert m._tags['iptc'][key] == tag
    new_tag = IptcTag(key, ['A picture.'])
    m._set_iptc_tag(key, new_tag)
    assert m._tags['iptc'] == {key: new_tag}
    assert key in m._image._iptcKeys()
    assert m._image._getIptcTag(key)._getRawValues() == [b'A picture.']


def test_set_iptc_tag_direct_value_assignment(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._tags['iptc'] == {}
    # Direct value assignment: pass a value instead of a fully-formed tag
    key = 'Iptc.Application2.Writer'
    values = ['Nobody']
    m._set_iptc_tag(key, values)
    assert key in m.iptc_keys
    assert key in m._image._iptcKeys()
    tag = m._get_iptc_tag(key)
    assert tag.value == values
    assert m._tags['iptc'] == {key: tag}
    assert m._image._getIptcTag(key)._getRawValues() == [b'Nobody']


def test_delete_iptc_tag_inexistent(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    key = 'Iptc.Application2.LocationCode'
    with pytest.raises(KeyError):
        m._delete_iptc_tag(key)


def test_delete_iptc_tag_not_cached(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    key = 'Iptc.Application2.Caption'
    assert m._tags['iptc'] == {}
    assert key in m.iptc_keys
    m._delete_iptc_tag(key)
    assert m._tags['iptc'] == {}
    assert key not in m.iptc_keys


def test_delete_iptc_tag_cached(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    key = 'Iptc.Application2.Caption'
    assert key in m.iptc_keys
    tag = m._get_iptc_tag(key)
    assert m._tags['iptc'][key] == tag
    m._delete_iptc_tag(key)
    assert m._tags['iptc'] == {}
    assert key not in m.iptc_keys


##########################
# Test XMP-related methods
##########################


def test_xmp_keys(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._keys['xmp'] is None
    keys = m.xmp_keys
    assert len(keys) == 2
    assert m._keys['xmp'] == keys


def test_get_xmp_tag(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._tags['xmp'] == {}
    # Get an existing tag
    key = 'Xmp.dc.subject'
    tag = m._get_xmp_tag(key)
    assert isinstance(tag, XmpTag)
    assert m._tags['xmp'][key] == tag
    # Try to get an nonexistent tag
    key = 'Xmp.xmp.Label'
    with pytest.raises(KeyError):
        m._get_xmp_tag(key)


def test_set_xmp_tag_wrong(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._tags['xmp'] == {}
    # Try to set a tag with wrong type
    tag = 'Not an xmp tag'
    with pytest.raises(TypeError):
        m._set_xmp_tag(tag)
    assert m._tags['xmp'] == {}


def test_set_xmp_tag_create(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._tags['xmp'] == {}
    # Create a new tag
    tag = XmpTag(
        'Xmp.dc.title', {
            'x-default': 'This is not a title',
            'fr-FR': "Ceci n'est pas un titre"
        }
    )
    assert tag.key not in m.xmp_keys
    m._set_xmp_tag(tag.key, tag)
    assert tag.key in m.xmp_keys
    assert m._tags['xmp'] == {tag.key: tag}
    assert tag.key in m._image._xmpKeys()
    assert m._image._getXmpTag(tag.key)._getLangAltValue() == {
        'x-default': 'This is not a title',
        'fr-FR': "Ceci n'est pas un titre"
    }


def test_set_xmp_tag_overwrite(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._tags['xmp'] == {}
    # Overwrite an existing tag
    tag = XmpTag('Xmp.dc.format', ('image', 'png'))
    m._set_xmp_tag(tag.key, tag)
    assert m._tags['xmp'] == {tag.key: tag}
    assert tag.key in m._image._xmpKeys()
    assert m._image._getXmpTag(tag.key)._getTextValue() == tag.raw_value


def test_set_xmp_tag_overwrite_already_cached(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._tags['xmp'] == {}
    # Overwrite an existing tag already cached
    key = 'Xmp.dc.subject'
    tag = m._get_xmp_tag(key)
    assert m._tags['xmp'][key] == tag
    new_tag = XmpTag(key, ['hello', 'world'])
    m._set_xmp_tag(key, new_tag)
    assert m._tags['xmp'] == {key: new_tag}
    assert key in m._image._xmpKeys()
    assert m._image._getXmpTag(key)._getArrayValue() == ['hello', 'world']


def test_set_xmp_tag_direct_value_assignment(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m._tags['xmp'] == {}
    # Direct value assignment: pass a value instead of a fully-formed tag
    key = 'Xmp.dc.title'
    value = {'x-default': 'Landscape', 'fr-FR': "Paysage"}
    m._set_xmp_tag(key, value)
    assert key in m.xmp_keys
    assert key in m._image._xmpKeys()
    tag = m._get_xmp_tag(key)
    assert tag.value == value
    assert m._tags['xmp'] == {key: tag}
    assert m._image._getXmpTag(key)._getLangAltValue() == {
        'x-default': 'Landscape',
        'fr-FR': "Paysage"
    }


def test_delete_xmp_tag_inexistent(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    key = 'Xmp.xmp.CreatorTool'
    with pytest.raises(KeyError):
        m._delete_xmp_tag(key)


def test_delete_xmp_tag_not_cached(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    key = 'Xmp.dc.subject'
    assert m._tags['xmp'] == {}
    assert key in m.xmp_keys
    m._delete_xmp_tag(key)
    assert m._tags['xmp'] == {}
    assert key not in m.xmp_keys


def test_delete_xmp_tag_cached(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    key = 'Xmp.dc.subject'
    assert key in m.xmp_keys
    tag = m._get_xmp_tag(key)
    assert m._tags['xmp'][key] == tag
    m._delete_xmp_tag(key)
    assert m._tags['xmp'] == {}
    assert key not in m.xmp_keys


###########################
# Test dictionary interface
###########################


def test_getitem(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    # Get existing tags
    key = 'Exif.Image.DateTime'
    tag = m[key]
    assert isinstance(tag, ExifTag)
    key = 'Iptc.Application2.Caption'
    tag = m[key]
    assert isinstance(tag, IptcTag)
    key = 'Xmp.dc.format'
    tag = m[key]
    assert isinstance(tag, XmpTag)
    # Try to get nonexistent tags
    keys = (
        'Exif.Image.SamplesPerPixel', 'Iptc.Application2.FixtureId',
        'Xmp.xmp.Rating', 'Wrong.Noluck.Raise'
    )
    for key in keys:
        with pytest.raises(KeyError):
            m[key]


def test_setitem(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    # Set new tags
    key = 'Exif.Photo.ExposureBiasValue'
    tag = ExifTag(key, make_fraction(0, 3))
    m[key] = tag
    assert key in m._tags['exif']
    assert m._tags['exif'][key] == tag
    key = 'Iptc.Application2.City'
    tag = IptcTag(key, ['Barcelona'])
    m[key] = tag
    assert key in m._tags['iptc']
    assert m._tags['iptc'][key] == tag
    key = 'Xmp.dc.description'
    tag = XmpTag(key, {'x-default': 'Sunset picture.'})
    m[key] = tag
    assert key in m._tags['xmp']
    assert m._tags['xmp'][key] == tag
    # Replace existing tags
    key = 'Exif.Photo.ExifVersion'
    tag = ExifTag(key, '0220')
    m[key] = tag
    assert key in m._tags['exif']
    assert m._tags['exif'][key] == tag
    key = 'Iptc.Application2.Caption'
    tag = IptcTag(key, ['Sunset on Barcelona.'])
    m[key] = tag
    assert key in m._tags['iptc']
    assert m._tags['iptc'][key] == tag
    key = 'Xmp.dc.subject'
    tag = XmpTag(key, ['sunset', 'Barcelona', 'beautiful', 'beach'])
    m[key] = tag
    assert key in m._tags['xmp']
    assert m._tags['xmp'][key] == tag


def test_delitem(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    # Delete existing tags
    key = 'Exif.Image.Make'
    del m[key]
    assert key not in m._keys['exif']
    assert key not in m._tags['exif']
    key = 'Iptc.Application2.Caption'
    del m[key]
    assert key not in m._keys['iptc']
    assert key not in m._tags['iptc']
    key = 'Xmp.dc.subject'
    del m[key]
    assert key not in m._keys['xmp']
    assert key not in m._tags['xmp']
    # Try to delete nonexistent tags
    keys = (
        'Exif.Image.SamplesPerPixel', 'Iptc.Application2.FixtureId',
        'Xmp.xmp.Rating', 'Wrong.Noluck.Raise'
    )
    for key in keys:
        with pytest.raises(KeyError):
            del m[key]


def test_replace_tag_by_itself(metadata_ro):
    # Test that replacing an existing tag by itself
    # doesn’t result in an ugly segmentation fault
    # (see https://bugs.launchpad.net/pyexiv2/+bug/622739).
    m = metadata_ro.metadata
    m.read()
    for key in itertools.chain(m.exif_keys, m.iptc_keys, m.xmp_keys):
        m[key] = m[key]


def test_nonexistent_tag_family(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    key = 'Bleh.Image.DateTime'
    with pytest.raises(KeyError):
        m[key]
    with pytest.raises(KeyError):
        m[key] = datetime.date.today()
    with pytest.raises(KeyError):
        del m[key]


##########################
# Test the image comment #
##########################


def test_get_comment(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert m.comment == 'Hello World!'


def test_set_comment(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    comment = 'Welcome to the real world.'
    m.comment = comment
    assert m.comment == comment
    m.comment = None
    assert m.comment == ''


def test_delete_comment(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    del m.comment
    assert m.comment == ''


####################
# Test metadata copy
####################


def test_copy_metadata(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    other = ImageMetadata.from_buffer(EMPTY_JPG_DATA)
    other.read()
    families = ('exif', 'iptc', 'xmp')

    for family in families:
        assert getattr(other, '%s_keys' % family) == []

    m.copy(other)

    for family in ('exif', 'iptc', 'xmp'):
        assert other._keys[family] is None
        assert other._tags[family] == {}
        keys = getattr(m, '%s_keys' % family)
        assert getattr(other._image, '_%sKeys' % family)() == keys
        assert getattr(other, '%s_keys' % family) == keys

    for key in m.exif_keys:
        assert m[key].value == other[key].value

    for key in m.iptc_keys:
        assert m[key].value == other[key].value

    for key in m.xmp_keys:
        assert m[key].value == other[key].value

    assert m.comment == other.comment


#############################
# Test MutableMapping methods
#############################


def test_mutablemapping():
    clean = ImageMetadata.from_buffer(EMPTY_JPG_DATA)
    clean.read()

    assert len(clean) == 0
    assert 'Exif.Image.DateTimeOriginal' not in clean

    key = 'Exif.Image.DateTimeOriginal'
    correctDate = datetime.datetime(2007, 3, 11)
    incorrectDate = datetime.datetime(2009, 3, 25)
    tag_date = ExifTag(key, correctDate)
    false_tag_date = ExifTag(key, incorrectDate)
    clean[key] = tag_date

    assert len(clean) == 1
    assert 'Exif.Image.DateTimeOriginal' in clean
    assert clean.get('Exif.Image.DateTimeOriginal', false_tag_date) == tag_date
    assert clean.get('Exif.Image.DateTime', tag_date) == tag_date

    key = 'Exif.Photo.UserComment'
    tag = ExifTag(key, 'UserComment')
    clean[key] = tag
    key = 'Iptc.Application2.Caption'
    tag = IptcTag(key, ['Caption'])
    clean[key] = tag
    key = 'Xmp.dc.subject'
    tag = XmpTag(key, ['subject', 'values'])
    clean[key] = tag

    assert 'Exif.Photo.UserComment' in clean
    assert 'Iptc.Application2.Caption' in clean
    assert 'Xmp.dc.subject' in clean

    clean.clear()
    assert len(clean) == 0

    assert 'Exif.Photo.UserComment' not in clean
    assert 'Iptc.Application2.Caption' not in clean
    assert 'Xmp.dc.subject' not in clean


###########################
# Test the EXIF thumbnail #
###########################


def _test_thumbnail_tags(m, present):
    keys = (
        'Exif.Thumbnail.Compression',
        'Exif.Thumbnail.JPEGInterchangeFormat',
        'Exif.Thumbnail.JPEGInterchangeFormatLength',
    )
    for key in keys:
        assert (key in m.exif_keys) == present


def test_no_exif_thumbnail(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    thumb = m.exif_thumbnail
    assert thumb.mime_type == ''
    assert thumb.extension == ''
    # ExifThumbnail._get_data not yet implemented
    # assert thumb.data == ''
    _test_thumbnail_tags(m, False)


def test_set_exif_thumbnail_from_data(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    _test_thumbnail_tags(m, False)
    thumb = m.exif_thumbnail
    thumb.data = EMPTY_JPG_DATA
    assert thumb.mime_type == 'image/jpeg'
    assert thumb.extension == '.jpg'
    # ExifThumbnail._get_data not yet implemented
    # assert thumb.data == EMPTY_JPG_DATA
    _test_thumbnail_tags(m, True)


def test_set_exif_thumbnail_from_file(metadata_ro, scratch_directory):
    m = metadata_ro.metadata
    m.read()
    thumb = m.exif_thumbnail
    _test_thumbnail_tags(m, False)

    with tempfile.NamedTemporaryFile(
        dir=scratch_directory, suffix='.jpg'
    ) as fp:
        fp.write(EMPTY_JPG_DATA)
        fp.flush()
        thumb.set_from_file(fp.name)

    assert thumb.mime_type == 'image/jpeg'
    assert thumb.extension == '.jpg'
    # ExifThumbnail._get_data not yet implemented
    # assert thumb.data == EMPTY_JPG_DATA
    _test_thumbnail_tags(m, True)


def test_write_exif_thumbnail_to_file(metadata_ro, scratch_directory):
    m = metadata_ro.metadata
    m.read()
    _test_thumbnail_tags(m, False)
    thumb = m.exif_thumbnail
    thumb.data = EMPTY_JPG_DATA

    # tempfile.mktemp would actually be safe here because we are the
    # only process that can write to the scratch_directory, but then
    # we'd have to suppress warnings.  This can be cleaned up if and
    # when thumb.write_to_file grows the ability to write to a filelike.
    fd, pathname = tempfile.mkstemp(dir=scratch_directory)
    os.close(fd)

    # This actually writes to pathname + thumb.extension.
    thumb.write_to_file(pathname)
    with open(pathname + thumb.extension, 'rb') as fp:
        assert fp.read() == EMPTY_JPG_DATA


def test_erase_exif_thumbnail(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    _test_thumbnail_tags(m, False)
    thumb = m.exif_thumbnail
    thumb.data = EMPTY_JPG_DATA
    assert thumb.mime_type == 'image/jpeg'
    assert thumb.extension == '.jpg'
    # ExifThumbnail._get_data not yet implemented
    # assert thumb.data == EMPTY_JPG_DATA
    _test_thumbnail_tags(m, True)
    thumb.erase()
    assert thumb.mime_type == ''
    assert thumb.extension == ''
    # assert thumb.data == ''
    _test_thumbnail_tags(m, False)


def test_set_exif_thumbnail_from_invalid_data(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    _test_thumbnail_tags(m, False)
    thumb = m.exif_thumbnail

    # No check on the format of the buffer is performed, so this will
    # succeed.
    thumb.data = b'invalid'
    assert thumb.mime_type == 'image/jpeg'
    _test_thumbnail_tags(m, True)


def test_set_exif_thumbnail_from_nonexistent_file(
    metadata_ro, empty_directory
):
    m = metadata_ro.metadata
    m.read()
    _test_thumbnail_tags(m, False)

    non_jpg = os.path.join(empty_directory, 'non.jpg')
    with pytest.raises(OSError):
        m.exif_thumbnail.set_from_file(non_jpg)

    _test_thumbnail_tags(m, False)


def test_exif_thumbnail_is_preview(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    _test_thumbnail_tags(m, False)
    assert len(m.previews) == 0
    thumb = m.exif_thumbnail
    thumb.data = EMPTY_JPG_DATA
    _test_thumbnail_tags(m, True)
    assert len(m.previews) == 1
    preview = m.previews[0]
    assert thumb.mime_type == preview.mime_type
    assert thumb.extension == preview.extension


#########################
# Test the IPTC charset #
#########################


def test_guess_iptc_charset(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    # If no charset is defined, exiv2 guesses it from the encoding of the
    # metadata.
    assert m.iptc_charset == 'ascii'
    m['Iptc.Application2.City'] = [u'Córdoba']
    assert m.iptc_charset == 'utf-8'


def test_set_iptc_charset_utf8(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert 'Iptc.Envelope.CharacterSet' not in m.iptc_keys
    assert m.iptc_charset == 'ascii'
    values = ('utf-8', 'utf8', 'u8', 'utf', 'utf_8')
    for value in values:
        m.iptc_charset = value
        assert m.iptc_charset == 'utf-8'
        m.iptc_charset = value.upper()
        assert m.iptc_charset == 'utf-8'


def test_set_invalid_iptc_charset(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    assert 'Iptc.Envelope.CharacterSet' not in m.iptc_keys
    values = ('invalid', 'utf-9', '3.14')
    for value in values:
        with pytest.raises(ValueError):
            m.iptc_charset = value


def test_set_unhandled_iptc_charset(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    # At the moment, the only charset handled is UTF-8.
    assert 'Iptc.Envelope.CharacterSet' not in m.iptc_keys
    values = ('ascii', 'iso8859_15', 'shift_jis')
    for value in values:
        with pytest.raises(ValueError):
            m.iptc_charset = value


def test_delete_iptc_charset(metadata_ro):
    m = metadata_ro.metadata
    m.read()
    key = 'Iptc.Envelope.CharacterSet'

    assert m.iptc_charset == 'ascii'
    assert key not in m.iptc_keys
    del m.iptc_charset
    assert m.iptc_charset == 'ascii'
    assert key not in m.iptc_keys

    m.iptc_charset = 'utf-8'
    assert m.iptc_charset == 'utf-8'
    assert key in m.iptc_keys
    del m.iptc_charset
    assert m.iptc_charset == 'ascii'
    assert key not in m.iptc_keys

    m.iptc_charset = 'utf-8'
    assert m.iptc_charset == 'utf-8'
    assert key in m.iptc_keys
    m.iptc_charset = None
    assert m.iptc_charset == 'ascii'
    assert key not in m.iptc_keys
