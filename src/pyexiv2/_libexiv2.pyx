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
# Maintainer: Zack Weinberg <zackw@panix.com>
#
# ******************************************************************************

# Cython wrapper module for libexiv2.

# cython: language_level = 3
# distutils: language = c++

from libcpp.string cimport string as cxstr
from libcpp.vector cimport vector
from libcpp.map cimport map as cxmap
from libcpp.memory cimport unique_ptr
from cython.operator cimport dereference as deref
from cython.operator cimport preincrement as preinc

from . cimport _libexiv2_if
from ._libexiv2_if cimport (
    ExifData, IptcData, XmpData,
    PreviewManager, PreviewProperties, PreviewPropertiesList
)

#
# Internal utility functions
#
cdef bytes to_bytes(object s):
    """If S is already a byte string, return it unchanged.
       If S is a unicode string, encode it in UTF-8."""
    if isinstance(s, unicode):
        return s.encode("utf-8")
    elif isinstance(s, bytes):
        return s
    else:
        # FIXME: Might be nice to accept byte memoryviews here as well?
        raise TypeError("a unicode or byte string is required")

ctypedef const char *cstr
ctypedef fused cxstr_or_cstr:
    cxstr
    cstr


cdef unicode to_pystr(cxstr_or_cstr s):
    return s.decode("utf-8")

#
# Public interfaces
#
exiv2_version_info = (
    _libexiv2_if.EXIV2_MAJOR_VERSION,
    _libexiv2_if.EXIV2_MINOR_VERSION,
    _libexiv2_if.EXIV2_PATCH_VERSION,
)


cdef class _Image


cdef class _ExifTag:
    cdef _libexiv2_if.ExifTag _inner

    def __init__(self, key=None):
        if key is not None:
            self._inner.init(to_bytes(key))

    def _getKey(self):
        return to_pystr(self._inner.getKey())

    def _setParentImage(self, _Image img not None):
        return self._inner.setParentImage(img._inner)

    def _getRawValue(self):
        return <bytes>self._inner.getRawValue()

    def _setRawValue(self, value):
        self._inner.setRawValue(to_bytes(value))

    def _getHumanValue(self):
        return to_pystr(self._inner.getHumanValue())

    def _getByteOrder(self):
        return self._inner.getByteOrder()

    def _getType(self):
        return to_pystr(self._inner.getType())

    def _getName(self):
        return to_pystr(self._inner.getName())

    def _getLabel(self):
        return to_pystr(self._inner.getLabel())

    def _getDescription(self):
        return to_pystr(self._inner.getDescription())

    def _getSectionName(self):
        return to_pystr(self._inner.getSectionName())

    def _getSectionDescription(self):
        # The section description is not exposed in the API any longer
        # (see https://dev.exiv2.org/issues/744). For want of anything
        # better, fall back on the section’s name.
        return to_pystr(self._inner.getSectionName())


cdef class _IptcTag:
    cdef _libexiv2_if.IptcTag _inner

    def __init__(self, key=None):
        if key is not None:
            self._inner.init(to_bytes(key))

    def _getKey(self):
        return to_pystr(self._inner.getKey())

    def _setParentImage(self, _Image image not None):
        return self._inner.setParentImage(image._inner)

    def _getRawValues(self):
        cdef list rv
        cdef cxstr val
        cdef unsigned int record, tag
        cdef IptcData.iterator beg, end, p

        record = self._inner.getRecord()
        tag = self._inner.getTag()
        p = beg = self._inner.getData().begin()
        end = self._inner.getData().end()
        rv = []

        while p != end:
            if deref(p).record() == record and deref(p).tag() == tag:
                rv.append(<bytes>(deref(p).toString()))
            preinc(p)

        return rv

    def _setRawValues(self, values):
        # FIXME: The old values are cleared before all of the checks
        # on the new values are complete.  We would ideally do all the
        # checks up front before starting to replace the old values.
        # This would involve exposing Exiv2::Iptcdatum to this level.
        if self._inner.isRepeatable():
            self._inner.clearRawValues()
            for val in values:
                self._inner.addRawValue(to_bytes(val))
        else:
            vi = iter(values)
            first = next(vi)
            try:
                next(vi)
                raise KeyError("Tag not repeatable: " +
                               to_pystr(self._inner.getKey()))
            except StopIteration:
                pass
            self._inner.clearRawValues()
            self._inner.addRawValue(to_bytes(first))

    def _getType(self):
        return to_pystr(self._inner.getType())

    def _isRepeatable(self):
        return self._inner.isRepeatable()

    def _getName(self):
        return to_pystr(self._inner.getName())

    def _getTitle(self):
        return to_pystr(self._inner.getTitle())

    def _getDescription(self):
        return to_pystr(self._inner.getDescription())

    def _getPhotoshopName(self):
        return to_pystr(self._inner.getPhotoshopName())

    def _getRecordName(self):
        return to_pystr(self._inner.getRecordName())

    def _getRecordDescription(self):
        return to_pystr(self._inner.getRecordDescription())


cdef class _XmpTag:
    cdef _libexiv2_if.XmpTag _inner

    def __init__(self, key=None):
        if key is not None:
            self._inner.init(to_bytes(key))

    def _getKey(self):
        return to_pystr(self._inner.getKey())

    def _setParentImage(self, _Image image not None):
        return self._inner.setParentImage(image._inner)

    def _getTextValue(self):
        return to_pystr(self._inner.getTextValue())

    def _setTextValue(self, value):
        cdef cxstr cxvalue = to_bytes(value)
        self._inner.resetValue()
        self._inner.appendValue(cxvalue)

    def _getArrayValue(self):
        cdef list rv = []
        cdef const _libexiv2_if.XmpArrayValue* \
            xav = self._inner.getArrayValue()
        for i in range(xav.count()):
            rv.append(to_pystr(xav.toString(i)))
        return rv

    def _setArrayValue(self, values):
        # Do all conversions before discarding the old value set.
        # FIXME: This still loses data if _inner.appendValue() throws.
        cdef vector[cxstr] cxvalues
        cdef object v1
        cdef cxstr v2
        for v1 in values:
            cxvalues.push_back(to_bytes(v1))

        self._inner.resetValue()
        for v2 in cxvalues:
            self._inner.appendValue(v2)

    def _getLangAltValue(self):
        cdef dict rv = {}
        cdef const _libexiv2_if.XmpLangAltValue* \
            xlav = self._inner.getLangAltValue()

        # Working around two different cython bugs here:
        # We can't use 'for v in xlav[0]' because then cython will
        # incorrectly use a plain iterator instead of a
        # const_iterator.
        # We can't say '_libexiv2_if.XmpLangAltValue.const_iterator'
        # because then cython will try to interpret XmpLangAltValue as a
        # module rather than a class.
        cdef cxmap[cxstr,cxstr].const_iterator beg, end, p
        p = beg = xlav[0].const_begin()
        end = xlav[0].const_end()
        while p != end:
            rv[to_pystr(deref(p).first)] = to_pystr(deref(p).second)
            preinc(p)
        return rv

    def _setLangAltValue(self, values):
        # Do all conversions before discarding the old value set.
        # FIXME: This still loses data if _inner.appendValue() throws.
        cdef vector[cxstr] cxvalues
        cdef cxstr val
        cdef bytes lang, text
        for lang_, text_ in values.items():
            lang = to_bytes(lang_)
            text = to_bytes(text_)
            val = b'lang="' + lang + b'" ' + text
            cxvalues.push_back(val)

        self._inner.resetValue()
        for val in cxvalues:
            self._inner.appendValue(val)

    def _getType(self):
        return to_pystr(self._inner.getType())

    def _getExiv2Type(self):
        return to_pystr(self._inner.getExiv2Type())

    def _getName(self):
        return to_pystr(self._inner.getName())

    def _getTitle(self):
        return to_pystr(self._inner.getTitle())

    def _getDescription(self):
        return to_pystr(self._inner.getDescription())


cdef class _Preview:
    cdef readonly str mime_type
    cdef readonly str extension
    cdef readonly int size
    cdef readonly tuple dimensions
    cdef readonly bytes data

    # Working around a cython limitation: __init__ and __cinit__ can't
    # take arguments that aren't Python objects.
    @staticmethod
    cdef _Preview from_pi(const _libexiv2_if.PreviewImage& img):
        cdef _Preview this = _Preview.__new__(_Preview)
        this.mime_type = to_pystr(img.mimeType())
        this.extension = to_pystr(img.extension())
        this.dimensions = (img.width(), img.height())
        this.size = img.size()
        this.data = img.pData()[:this.size]
        return this

    def write_to_file(self, path):
        if isinstance(path, str) and not path.endswith(self.extension):
            path += self.extension
        with open(path, "wb") as fp:
            fp.write(self.data)


cdef class _Image:
    cdef _libexiv2_if.Image _inner

    def __init__(self, buffer_or_filename not None, size=None):
        cdef const unsigned char[:] buf
        if size is None:
            self._inner.init(to_bytes(buffer_or_filename))
        else:
            buf = buffer_or_filename
            self._inner.init(&buf[:size][0], size)

    def _readMetadata(self):
        self._inner.readMetadata()

    def _writeMetadata(self):
        self._inner.writeMetadata()

    def _copyMetadata(self, _Image other not None,
                      exif=True, iptc=True, xmp=True):
        self._inner.copyMetadata(other._inner, exif, iptc, xmp)

    def _getMimeType(self):
        return to_pystr(self._inner.mimeType())

    def _getPixelWidth(self):
        return self._inner.pixelWidth()

    def _getPixelHeight(self):
        return self._inner.pixelHeight()

    def _getDataBuffer(self):
        return self._inner.getDataBuffer()

    def _exifKeys(self):
        cdef list rv = []
        cdef ExifData* data = self._inner.getExifData()
        # 'for datum in data[0]' will attempt to declare 'datum' with type
        # Exifdatum, which doesn't work because Exifdatum has no nullary
        # constructor.
        cdef ExifData.iterator beg, end, p;
        p = beg = data[0].begin()
        end = data[0].end()
        while p != end:
            rv.append(to_pystr(deref(p).key()))
            preinc(p)
        return rv

    def _getExifTag(self, key):
        cdef _ExifTag tag = _ExifTag()
        self._inner.getExifTag(to_bytes(key), tag._inner)
        return tag

    def _deleteExifTag(self, key):
        self._inner.deleteExifTag(to_bytes(key))

    def _iptcKeys(self):
        cdef list rv = []
        cdef set seen = set()
        cdef str pkey
        cdef IptcData* data = self._inner.getIptcData()
        # 'for datum in data[0]' will attempt to declare 'datum' with type
        # Iptcdatum, which doesn't work because Iptcdatum has no nullary
        # constructor.
        cdef IptcData.iterator beg, end, p;

        p = beg = data[0].begin()
        end = data[0].end()
        while p != end:
            pkey = to_pystr(deref(p).key())
            # The key is appended to the list if and only if it is not
            # already present.  We track "already present" with a separate
            # set so we can preserve the image's order of keys.
            if pkey not in seen:
                rv.append(pkey)
                seen.add(pkey)
            preinc(p)
        return rv

    def _getIptcTag(self, key):
        cdef _IptcTag tag = _IptcTag()
        self._inner.getIptcTag(to_bytes(key), tag._inner)
        return tag

    def _deleteIptcTag(self, key):
        self._inner.deleteIptcTag(to_bytes(key))

    def _getIptcCharset(self):
        return to_pystr(self._inner.getIptcCharset())

    def _xmpKeys(self):
        cdef list rv = []
        cdef XmpData* data = self._inner.getXmpData()
        # 'for datum in data[0]' will attempt to declare 'datum' with type
        # Xmpdatum, which doesn't work because Xmpdatum has no nullary
        # constructor.
        cdef XmpData.iterator beg, end, p;
        p = beg = data[0].begin()
        end = data[0].end()
        while p != end:
            rv.append(to_pystr(deref(p).key()))
            preinc(p)
        return rv

    def _getXmpTag(self, key):
        cdef _XmpTag tag = _XmpTag()
        self._inner.getXmpTag(to_bytes(key), tag._inner)
        return tag

    def _deleteXmpTag(self, key):
        self._inner.deleteXmpTag(to_bytes(key))

    def _getComment(self):
        return to_pystr(self._inner.getComment())

    def _setComment(self, comment):
        self._inner.setComment(to_bytes(comment))

    def _clearComment(self):
        self._inner.clearComment()

    def _previews(self):
        # This is the Cython half of a kludge around the fact that
        # Cython doesn't support local variables with C++ class types
        # that have no default or copy constructor.
        cdef unique_ptr[PreviewManager] pm;
        pm.reset(self._inner.getPreviewManager())

        cdef list rv = []
        cdef PreviewPropertiesList props = deref(pm).getPreviewProperties()
        cdef vector[PreviewProperties].const_iterator beg, end, p

        p = beg = props.const_begin()
        end = props.const_end()
        while p != end:
            rv.append(_Preview.from_pi(
                deref(pm).getPreviewImage(deref(p))
            ))
            preinc(p)

        return rv

    def _getExifThumbnailMimeType(self):
        return to_pystr(self._inner.getExifThumbnailMimeType())

    def _getExifThumbnailExtension(self):
        return to_pystr(self._inner.getExifThumbnailExtension())

    def _writeExifThumbnailToFile(self, path):
        self._inner.writeExifThumbnailToFile(to_bytes(path))

    def _getExifThumbnailData(self):
        return self._inner.getExifThumbnailData()

    def _eraseExifThumbnail(self):
        self._inner.eraseExifThumbnail()

    def _setExifThumbnailFromFile(self, path):
        self._inner.setExifThumbnailFromFile(to_bytes(path))

    def _setExifThumbnailFromData(self, data):
        cdef const unsigned char[:] buf = data
        self._inner.setExifThumbnailFromData(&buf[0], buf.shape[0])


def _initialiseXmpParser():
    return _libexiv2_if.initialiseXmpParser()


def _closeXmpParser():
    return _libexiv2_if.closeXmpParser()


def _registerXmpNs(name_, prefix_):
    cdef cxstr name = to_bytes(name_)
    cdef cxstr prefix = to_bytes(prefix_)
    _libexiv2_if.registerXmpNs(name, prefix)


def _unregisterXmpNs(name_):
    cdef cxstr name = to_bytes(name_)
    _libexiv2_if.unregisterXmpNs(name)


def _unregisterAllXmpNs():
    _libexiv2_if.unregisterAllXmpNs()
