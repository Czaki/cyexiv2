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

# These Cython interface definitions correspond to an intermediate
# shim layer, defined in _libexiv2_if.hpp, that wraps the libexiv2
# API and makes it a little easier to expose to Python.

# Style note: _libexiv2_if.hpp consistently uses
# French type qualifiers (e.g. 'char const*') but Cython accepts only
# English type qualifiers (e.g. 'const char*').  Stars cuddle left.

from libcpp cimport bool
from libcpp.map cimport map as cxmap
from libcpp.string cimport string as cxstr
from libcpp.vector cimport vector

cdef extern from "_libexiv2_if.hpp":
    int EXIV2_MAJOR_VERSION
    int EXIV2_MINOR_VERSION
    int EXIV2_PATCH_VERSION

    int SIZEOF_PREVIEW_MANAGER

    void TX "exception_to_pyerr" ()

    bool initialiseXmpParser() except +TX
    bool closeXmpParser() except +TX
    void registerXmpNs(const cxstr& name, const cxstr& prefix) except +TX
    void unregisterXmpNs(const cxstr& name) except +TX
    void unregisterAllXmpNs() except +TX

    cdef cppclass Image

    cdef cppclass Exifdatum:
        cxstr key() except +TX

    cdef cppclass Iptcdatum:
        cxstr key() except +TX
        cxstr toString() except +TX
        unsigned int record() except +TX
        unsigned int tag() except +TX

    cdef cppclass Xmpdatum:
        cxstr key() except +TX

    cdef cppclass ExifData:
        cppclass iterator:
            iterator()
            iterator(iterator &)
            Exifdatum& operator*()
            iterator operator++()
            iterator operator--()
            bint operator==(iterator)
            bint operator!=(iterator)

        iterator begin()
        iterator end()

    cdef cppclass IptcData:
        cppclass iterator:
            iterator()
            iterator(iterator &)
            Iptcdatum& operator*()
            iterator operator++()
            iterator operator--()
            bint operator==(iterator)
            bint operator!=(iterator)

        iterator begin()
        iterator end()

    cdef cppclass XmpData:
        cppclass iterator:
            iterator()
            iterator(iterator &)
            Xmpdatum& operator*()
            iterator operator++()
            iterator operator--()
            bint operator==(iterator)
            bint operator!=(iterator)

        iterator begin()
        iterator end()

    cdef cppclass ExifTag:
        ExifTag()
        void init(const cxstr&) except +TX
        cxstr getKey() except +TX
        void setParentImage(Image) except +TX
        cxstr getRawValue() except +TX
        void setRawValue(const cxstr&) except +TX
        cxstr getHumanValue() except +TX
        int getByteOrder()
        const char* getType() except +TX
        cxstr getName() except +TX
        cxstr getLabel() except +TX
        cxstr getDescription() except +TX
        const char* getSectionName() except +TX

    cdef cppclass IptcTag:
        IptcTag()
        void init(const cxstr&) except +TX
        cxstr getKey() except +TX
        void setParentImage(Image) except +TX
        void clearRawValues() except +TX
        void addRawValue(const cxstr&) except +TX
        bool firstRawValue(cxstr&, IptcData.iterator&) except +TX
        bool nextRawValue(cxstr&, IptcData.iterator&) except +TX
        const char* getType() except +TX
        bool isRepeatable()
        unsigned int getTag()
        unsigned int getRecord()
        IptcData* getData()
        cxstr getName() except +TX
        const char* getTitle() except +TX
        const char* getDescription() except +TX
        const char* getPhotoshopName() except +TX
        cxstr getRecordName() except +TX
        const char* getRecordDescription() except +TX

    cdef cppclass XmpArrayValue:
        int count()
        cxstr toString(int)

    ctypedef cxmap[cxstr,cxstr] XmpLangAltValue

    cdef cppclass XmpTag:
        XmpTag()
        void init(const cxstr&) except +TX
        cxstr getKey() except +TX
        void setParentImage(Image) except +TX
        void resetValue() except +TX
        void appendValue(const cxstr&) except +TX
        cxstr getTextValue() except +TX
        const XmpArrayValue* getArrayValue() except +TX
        const XmpLangAltValue* getLangAltValue() except +TX
        const char* getType() except +TX
        const char* getExiv2Type() except +TX
        const char* getName() except +TX
        const char* getTitle() except +TX
        const char* getDescription() except +TX

    cdef cppclass PreviewImage:
        cxstr mimeType() except +TX
        cxstr extension() except +TX
        unsigned int size() except +TX
        unsigned int width() except +TX
        unsigned int height() except +TX
        const unsigned char *pData() except +TX

    cdef cppclass PreviewProperties
    ctypedef vector[PreviewProperties] PreviewPropertiesList

    cdef cppclass PreviewManager:
        PreviewPropertiesList getPreviewProperties() except +TX
        const PreviewImage& getPreviewImage(const PreviewProperties&) except +TX

    cdef cppclass Image:
        Image()
        void init(const cxstr&) except +TX
        void init(const void*, int) except +TX
        void readMetadata() except +TX
        void writeMetadata() except +TX
        void copyMetadata(Image&, bool, bool, bool) except +TX

        int pixelWidth() except +TX
        int pixelHeight() except +TX
        cxstr mimeType() except +TX
        bytes getDataBuffer()

        cxstr getComment() except +TX
        void setComment(const cxstr&) except +TX
        void clearComment() except +TX

        ExifData* getExifData() except +TX
        void getExifTag(const cxstr& key, ExifTag& tag) except +TX
        void deleteExifTag(const cxstr& key) except +TX

        IptcData* getIptcData() except +TX
        void getIptcTag(const cxstr& key, IptcTag& tag) except +TX
        void deleteIptcTag(const cxstr& key) except +TX

        XmpData* getXmpData() except +TX
        void getXmpTag(const cxstr& key, XmpTag& tag) except +TX
        void deleteXmpTag(const cxstr& key) except +TX

        const char* getIptcCharset() except +TX

        const char* getExifThumbnailMimeType() except +TX
        const char* getExifThumbnailExtension() except +TX
        void writeExifThumbnailToFile(const cxstr&) except +TX
        void eraseExifThumbnail() except +TX
        void setExifThumbnailFromFile(const cxstr&) except +TX
        bytes getExifThumbnailData()
        void setExifThumbnailFromData(const unsigned char *data,
                                      size_t len) except +TX

        PreviewManager* getPreviewManager() except +TX
