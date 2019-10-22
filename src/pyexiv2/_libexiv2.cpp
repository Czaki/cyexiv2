// *****************************************************************************
/*
 * Copyright (C) 2006-2012 Olivier Tilloy <olivier@tilloy.net>
 * Copyright (C) 2015-2019 Vincent Vande Vyvre <vincent.vandevyvre@oqapy.eu>
 * Copyright (C) 2019      Zack Weinberg <zackw@panix.com>
 *
 * This file is part of the pyexiv2 distribution.
 *
 * pyexiv2 is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * version 3 as published by the Free Software Foundation.
 *
 * pyexiv2 is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with pyexiv2.  If not, see <https://www.gnu.org/licenses/>.
 *
 * Maintainer: Vincent Vande Vyvre <vincent.vandevyvre@oqapy.eu>
 */
// *****************************************************************************

#include <string>
#include <fstream>
#include <iostream>

#include "exiv2/exiv2.hpp"

#include "boost/python.hpp"
#include "boost/python/stl_iterator.hpp"

#if EXIV2_MAJOR_VERSION == 0 && EXIV2_MINOR_VERSION < 27
# error "libexiv2 is too old (version 0.27 or later required)"
#endif

namespace {

// RAII class to release and re-acquire the GIL.
class release_gil
{
    PyThreadState *state;
public:
    release_gil() : state(PyEval_SaveThread()) {}
    ~release_gil() { PyEval_RestoreThread(state); }
};

// RAII class to save and restore an Exiv2::BasicIo seek position
// (if the file is already open) or open the file and close it again
// (if it wasn't already open).
class preserve_read_state
{
    Exiv2::BasicIo& io;
    long pos;
public:
    preserve_read_state(Exiv2::BasicIo& io)
        : io(io), pos(-1)
    {
        if (io.isopen())
        {
            // Remember the current position in the stream
            pos = io.tell();
            // Go to the beginning of the stream
            io.seek(0, Exiv2::BasicIo::beg);
        }
        else
        {
            io.open();
        }
    }

    ~preserve_read_state()
    {
        if (pos == -1)
        {
            // The stream was initially closed
            io.close();
        }
        else
        {
            // Reset to the previous position in the stream
            io.seek(pos, Exiv2::BasicIo::beg);
        }
    }
};

class Image;

class ExifTag
{
public:
    // Constructor
    ExifTag(const std::string& key,
            Exiv2::Exifdatum* datum=0, Exiv2::ExifData* data=0,
            Exiv2::ByteOrder byteOrder=Exiv2::invalidByteOrder);

    ~ExifTag();

    void setRawValue(const std::string& value);
    void setParentImage(Image& image);

    const std::string getKey();
    const std::string getType();
    const std::string getName();
    const std::string getLabel();
    const std::string getDescription();
    const std::string getSectionName();
    const std::string getSectionDescription();
    const std::string getRawValue();
    const std::string getHumanValue();
    int getByteOrder();

private:
    Exiv2::ExifKey _key;
    Exiv2::Exifdatum* _datum;
    Exiv2::ExifData* _data;
    std::string _type;
    std::string _name;
    std::string _label;
    std::string _description;
    std::string _sectionName;
    std::string _sectionDescription;
    int _byteOrder;
};


class IptcTag
{
public:
    // Constructor
    IptcTag(const std::string& key, Exiv2::IptcData* data=0);

    ~IptcTag();

    void setRawValues(const boost::python::list& values);
    void setParentImage(Image& image);

    const std::string getKey();
    const std::string getType();
    const std::string getName();
    const std::string getTitle();
    const std::string getDescription();
    const std::string getPhotoshopName();
    const bool isRepeatable();
    const std::string getRecordName();
    const std::string getRecordDescription();
    const boost::python::list getRawValues();

private:
    Exiv2::IptcKey _key;
    bool _from_data; // whether the tag is built from an existing IptcData
    Exiv2::IptcData* _data;
    std::string _type;
    std::string _name;
    std::string _title;
    std::string _description;
    std::string _photoshopName;
    bool _repeatable;
    std::string _recordName;
    std::string _recordDescription;
};


class XmpTag
{
public:
    // Constructor
    XmpTag(const std::string& key, Exiv2::Xmpdatum* datum=0);

    ~XmpTag();

    void setTextValue(const std::string& value);
    void setArrayValue(const boost::python::list& values);
    void setLangAltValue(const boost::python::dict& values);
    void setParentImage(Image& image);

    const std::string getKey();
    const std::string getExiv2Type();
    const std::string getType();
    const std::string getName();
    const std::string getTitle();
    const std::string getDescription();
    const std::string getTextValue();
    const boost::python::list getArrayValue();
    const boost::python::dict getLangAltValue();

private:
    Exiv2::XmpKey _key;
    bool _from_datum; // whether the tag is built from an existing Xmpdatum
    Exiv2::Xmpdatum* _datum;
    std::string _exiv2_type;
    std::string _type;
    std::string _name;
    std::string _title;
    std::string _description;
};


class Preview
{
public:
    Preview(const Exiv2::PreviewImage& previewImage);

    boost::python::object getData() const;
    void writeToFile(const std::string& path) const;

    std::string _mimeType;
    std::string _extension;
    unsigned int _size;
    boost::python::tuple _dimensions;
    std::string _data;
    const Exiv2::byte* pData;
};


class Image
{
public:
    // Constructors
    Image(const std::string& filename);
    Image(const std::string& buffer, unsigned long size);
    Image(const Image& image);

    ~Image();

    void readMetadata();
    void writeMetadata();

    // Read-only access to the dimensions of the picture.
    unsigned int pixelWidth() const;
    unsigned int pixelHeight() const;

    // Read-only access to the MIME type of the image.
    std::string mimeType() const;

    // Read and write access to the EXIF tags.
    // For a complete list of the available EXIF tags, see
    // libexiv2's documentation (http://exiv2.org/tags.html).

    // Return a list of all the keys of available EXIF tags set in the
    // image.
    boost::python::list exifKeys();

    // Return the required EXIF tag.
    // Throw an exception if the tag is not set.
    const ExifTag getExifTag(std::string key);

    // Delete the required EXIF tag.
    // Throw an exception if the tag was not set.
    void deleteExifTag(std::string key);

    // Read and write access to the IPTC tags.
    // For a complete list of the available IPTC tags, see
    // libexiv2's documentation (http://exiv2.org/iptc.html).

    // Returns a list of all the keys of available IPTC tags set in the
    // image. This list has no duplicates: each of its items is unique,
    // even if a tag is present more than once.
    boost::python::list iptcKeys();

    // Return the required IPTC tag.
    // Throw an exception if the tag is not set.
    const IptcTag getIptcTag(std::string key);

    // Delete (all the repetitions of) the required IPTC tag.
    // Throw an exception if the tag was not set.
    void deleteIptcTag(std::string key);

    boost::python::list xmpKeys();

    // Return the required XMP tag.
    // Throw an exception if the tag is not set.
    const XmpTag getXmpTag(std::string key);

    // Delete the required XMP tag.
    // Throw an exception if the tag was not set.
    void deleteXmpTag(std::string key);

    // Comment
    const std::string getComment() const;
    void setComment(const std::string& comment);
    void clearComment();

    // Read access to the thumbnail embedded in the image.
    boost::python::list previews();

    // Manipulate the JPEG/TIFF thumbnail embedded in the EXIF data.
    const std::string getExifThumbnailMimeType();
    const std::string getExifThumbnailExtension();
    void writeExifThumbnailToFile(const std::string& path);
    boost::python::list getExifThumbnailData();
    void eraseExifThumbnail();
    void setExifThumbnailFromFile(const std::string& path);
    void setExifThumbnailFromData(const std::string& data);

    // Copy the metadata to another image.
    void copyMetadata(Image& other, bool exif=true, bool iptc=true, bool xmp=true) const;

    // Return the image data buffer.
    boost::python::object getDataBuffer() const;

    // Accessors
    Exiv2::ExifData* getExifData() { return _exifData; };
    Exiv2::IptcData* getIptcData() { return _iptcData; };
    Exiv2::XmpData* getXmpData() { return _xmpData; };

    Exiv2::ByteOrder getByteOrder() const;

    const std::string getIptcCharset() const;

private:
    std::string _filename;
    Exiv2::byte* _data;
    long _size;
    Exiv2::Image::AutoPtr _image;
    Exiv2::ExifData* _exifData;
    Exiv2::IptcData* _iptcData;
    Exiv2::XmpData* _xmpData;
    Exiv2::ExifThumb* _exifThumbnail;
    Exiv2::ExifThumb* _getExifThumbnail();

    // true if the image's internal metadata has already been read,
    // false otherwise
    bool _dataRead;

    void check_metadata_read() const
    {
        if (!_dataRead)
        {
            throw Exiv2::Error(Exiv2::kerErrorMessage, "metadata not read");
        }
    }

    void _instantiate_image();
};


// Translate an Exiv2 generic exception into a Python exception
void translateExiv2Error(Exiv2::Error const& error);


// Functions to manipulate custom XMP namespaces
bool initialiseXmpParser();
bool closeXmpParser();
void registerXmpNs(const std::string& name, const std::string& prefix);
void unregisterXmpNs(const std::string& name);
void unregisterAllXmpNs();


void Image::_instantiate_image()
{
    _exifThumbnail = 0;

    // Release the GIL to allow other python threads to run
    // while opening the file.
    {
        release_gil in_this_block;

        if (_data != 0)
        {
            _image = Exiv2::ImageFactory::open(_data, _size);
        }
        else
        {
            _image = Exiv2::ImageFactory::open(_filename);
        }
    }

    assert(_image.get() != 0);
    _dataRead = false;
}

// Base constructor
Image::Image(const std::string& filename)
{
    _filename = filename;
    _data = 0;
    _instantiate_image();
}

// From buffer constructor
Image::Image(const std::string& buffer, unsigned long size)
{
    // Deep copy of the data buffer
    _data = new Exiv2::byte[size];
    for (unsigned long i = 0; i < size; ++i)
    {
        _data[i] = buffer[i];
    }

    _size = size;
    _instantiate_image();
}

// Copy constructor
Image::Image(const Image& image)
{
    _filename = image._filename;
    _instantiate_image();
}

Image::~Image()
{
    if (_data != 0)
    {
        delete[] _data;
    }
    if (_exifThumbnail != 0)
    {
        delete _exifThumbnail;
    }
}

void Image::readMetadata()
{
    // Release the GIL to allow other python threads to run
    // while reading metadata.
    release_gil in_this_block;

    _image->readMetadata();
    _exifData = &_image->exifData();
    _iptcData = &_image->iptcData();
    _xmpData = &_image->xmpData();
    _dataRead = true;
}

void Image::writeMetadata()
{
    check_metadata_read();

    // Release the GIL to allow other python threads to run
    // while writing metadata.
    {
        release_gil in_this_block;

        _image->writeMetadata();
    }
}

unsigned int Image::pixelWidth() const
{
    check_metadata_read();
    return _image->pixelWidth();
}

unsigned int Image::pixelHeight() const
{
    check_metadata_read();
    return _image->pixelHeight();
}

std::string Image::mimeType() const
{
    check_metadata_read();
    return _image->mimeType();
}

boost::python::list Image::exifKeys()
{
    check_metadata_read();

    boost::python::list keys;
    for(Exiv2::ExifMetadata::iterator i = _exifData->begin();
        i != _exifData->end();
        ++i)
    {
        keys.append(i->key());
    }
    return keys;
}

const ExifTag Image::getExifTag(std::string key)
{
    check_metadata_read();

    Exiv2::ExifKey exifKey = Exiv2::ExifKey(key);

    if(_exifData->findKey(exifKey) == _exifData->end())
    {
        throw Exiv2::Error(Exiv2::kerInvalidKey, key);
    }

    return ExifTag(key, &(*_exifData)[key], _exifData, _image->byteOrder());
}

void Image::deleteExifTag(std::string key)
{
    check_metadata_read();

    Exiv2::ExifKey exifKey = Exiv2::ExifKey(key);
    Exiv2::ExifMetadata::iterator datum = _exifData->findKey(exifKey);
    if(datum == _exifData->end())
    {
        throw Exiv2::Error(Exiv2::kerInvalidKey, key);
    }
    _exifData->erase(datum);
}

boost::python::list Image::iptcKeys()
{
    check_metadata_read();

    boost::python::list keys;
    for(Exiv2::IptcMetadata::iterator i = _iptcData->begin();
        i != _iptcData->end();
        ++i)
    {
        // The key is appended to the list if and only if it is not already
        // present.
        if (keys.count(i->key()) == 0)
        {
            keys.append(i->key());
        }
    }
    return keys;
}

const IptcTag Image::getIptcTag(std::string key)
{
    check_metadata_read();

    Exiv2::IptcKey iptcKey = Exiv2::IptcKey(key);

    if(_iptcData->findKey(iptcKey) == _iptcData->end())
    {
        throw Exiv2::Error(Exiv2::kerInvalidKey, key);
    }
    return IptcTag(key, _iptcData);
}

void Image::deleteIptcTag(std::string key)
{
    check_metadata_read();

    Exiv2::IptcKey iptcKey = Exiv2::IptcKey(key);
    Exiv2::IptcMetadata::iterator dataIterator = _iptcData->findKey(iptcKey);

    if (dataIterator == _iptcData->end())
    {
        throw Exiv2::Error(Exiv2::kerInvalidKey, key);
    }

    while (dataIterator != _iptcData->end())
    {
        if (dataIterator->key() == key)
        {
            dataIterator = _iptcData->erase(dataIterator);
        }
        else
        {
            ++dataIterator;
        }
    }
}

boost::python::list Image::xmpKeys()
{
    check_metadata_read();

    boost::python::list keys;
    for(Exiv2::XmpMetadata::iterator i = _xmpData->begin();
        i != _xmpData->end();
        ++i)
    {
        keys.append(i->key());
    }
    return keys;
}

const XmpTag Image::getXmpTag(std::string key)
{
    check_metadata_read();

    Exiv2::XmpKey xmpKey = Exiv2::XmpKey(key);

    if(_xmpData->findKey(xmpKey) == _xmpData->end())
    {
        throw Exiv2::Error(Exiv2::kerInvalidKey, key);
    }

    return XmpTag(key, &(*_xmpData)[key]);
}

void Image::deleteXmpTag(std::string key)
{
    check_metadata_read();

    Exiv2::XmpKey xmpKey = Exiv2::XmpKey(key);
    Exiv2::XmpMetadata::iterator i = _xmpData->findKey(xmpKey);
    if(i != _xmpData->end())
    {
        _xmpData->erase(i);
    }
    else
    {
        throw Exiv2::Error(Exiv2::kerInvalidKey, key);
    }
}

const std::string Image::getComment() const
{
    check_metadata_read();
    return _image->comment();
}

void Image::setComment(const std::string& comment)
{
    check_metadata_read();
    _image->setComment(comment);
}

void Image::clearComment()
{
    check_metadata_read();
    _image->clearComment();
}


boost::python::list Image::previews()
{
    check_metadata_read();

    boost::python::list previews;
    Exiv2::PreviewManager pm(*_image);
    Exiv2::PreviewPropertiesList props = pm.getPreviewProperties();
    for (Exiv2::PreviewPropertiesList::const_iterator i = props.begin();
         i != props.end();
         ++i)
    {
        previews.append(Preview(pm.getPreviewImage(*i)));
    }

    return previews;
}

void Image::copyMetadata(Image& other, bool exif, bool iptc, bool xmp) const
{
    check_metadata_read();
    other.check_metadata_read();

    if (exif)
        other._image->setExifData(*_exifData);
    if (iptc)
        other._image->setIptcData(*_iptcData);
    if (xmp)
        other._image->setXmpData(*_xmpData);
}

boost::python::object Image::getDataBuffer() const
{
    Exiv2::BasicIo& io = _image->io();
    unsigned long size = io.size();
    if (size > (unsigned long)LONG_MAX)
    {
        // The image is too large to represent in memory.
        throw std::bad_alloc();
    }

    long ssize = (long) size;
    long readpos = 0;
    long nread;

    // Use the PyBytes_* API to create a data buffer that we can read
    // directly into.  This must be done before releasing the GIL.
    PyObject *buffer = PyBytes_FromStringAndSize(NULL, size);
    if (!buffer)
    {
        throw std::bad_alloc();
    }
    // Arrange to deallocate 'buffer' if an exception is thrown after
    // this point.
    boost::python::handle<> buffer_h(buffer);

    // Because the bytes object is brand new and we hold the only
    // reference to it, we are allowed to write into its data area.
    // See https://docs.python.org/3/c-api/bytes.html#c.PyBytes_AsString
    void *data = PyBytes_AS_STRING(buffer);

    {
        // Release the GIL to allow other python threads to run
        // while reading the image data.
        release_gil in_this_block;

        // Save and restore the seek position within the image, or
        // open and close the image file, as necessary.
        preserve_read_state of(io);

        // Copy from the file into the Python buffer.
        do
        {
            nread = io.read(((Exiv2::byte*)data) + readpos, ssize - readpos);
            readpos += nread;
        }
        while (nread > 0 && readpos < ssize);

    } // GIL re-acquired and io reset to its previous state here

    // Direct access to the buffer's data area after this point would
    // be a bug.
    data = 0;

    // If we got the amount of data we expected, we're done.
    if (readpos == ssize)
    {
        return boost::python::object(buffer_h);
    }

    // If there was less data than expected, truncate the buffer to
    // the size of the data actually read.  This calls into the Python
    // allocator, so it must happen after re-acquiring the GIL.
    // _PyBytes_Resize may change the raw buffer pointer, so we have
    // to take it back from buffer_h.
    buffer_h.release();

    if (_PyBytes_Resize(&buffer, (unsigned long)readpos))
    {
        // If _PyBytes_Resize fails, it deallocates the original
        // buffer.
        throw std::bad_alloc();
    }
    return boost::python::object(boost::python::handle<>(buffer));
}

Exiv2::ByteOrder Image::getByteOrder() const
{
    check_metadata_read();
    return _image->byteOrder();
}

Exiv2::ExifThumb* Image::_getExifThumbnail()
{
    check_metadata_read();
    if (_exifThumbnail == 0)
    {
        _exifThumbnail = new Exiv2::ExifThumb(*_exifData);
    }
    return _exifThumbnail;
}

const std::string Image::getExifThumbnailMimeType()
{
    return std::string(_getExifThumbnail()->mimeType());
}

const std::string Image::getExifThumbnailExtension()
{
    return std::string(_getExifThumbnail()->extension());
}

void Image::writeExifThumbnailToFile(const std::string& path)
{
    _getExifThumbnail()->writeFile(path);
}

boost::python::list Image::getExifThumbnailData()
{
    Exiv2::DataBuf buffer = _getExifThumbnail()->copy();
    // Copy the data buffer in a list.
    boost::python::list data;
    for(unsigned int i = 0; i < buffer.size_; ++i)
    {
        unsigned int datum = buffer.pData_[i];
        data.append(datum);
    }
    return data;
}

void Image::eraseExifThumbnail()
{
    _getExifThumbnail()->erase();
}

void Image::setExifThumbnailFromFile(const std::string& path)
{
    _getExifThumbnail()->setJpegThumbnail(path);
}

void Image::setExifThumbnailFromData(const std::string& data)
{
    const Exiv2::byte* buffer = (const Exiv2::byte*) data.c_str();
    _getExifThumbnail()->setJpegThumbnail(buffer, data.size());
}

const std::string Image::getIptcCharset() const
{
    check_metadata_read();
    const char* charset = _iptcData->detectCharset();
    if (charset != 0)
    {
        return std::string(charset);
    }
    else
    {
        return std::string();
    }
}


ExifTag::ExifTag(const std::string& key,
                 Exiv2::Exifdatum* datum, Exiv2::ExifData* data,
                 Exiv2::ByteOrder byteOrder):
    _key(key), _byteOrder(byteOrder)
{
    if (datum != 0 && data != 0)
    {
        _datum = datum;
        _data = data;
    }
    else
    {
        _datum = new Exiv2::Exifdatum(_key);
        _data = 0;
    }

    Exiv2::ExifKey exifKey(key);
    _type = Exiv2::TypeInfo::typeName(exifKey.defaultTypeId());
    // Where available, extract the type from the metadata, it is more reliable
    // than static type information. The exception is for user comments, for
    // which we’d rather keep the 'Comment' type instead of 'Undefined'.
    if ((_data != 0) && (_type != "Comment"))
    {
        const char* typeName = _datum->typeName();
        if (typeName != 0)
        {
            _type = typeName;
        }
    }
    _name = exifKey.tagName();
    _label = exifKey.tagLabel();
    _description = exifKey.tagDesc();
    _sectionName = Exiv2::ExifTags::sectionName(exifKey);
    // The section description is not exposed in the API any longer
    // (see https://dev.exiv2.org/issues/744). For want of anything better,
    // fall back on the section’s name.
    _sectionDescription = _sectionName;
}

ExifTag::~ExifTag()
{
    if (_data == 0)
    {
        delete _datum;
    }
}

void ExifTag::setRawValue(const std::string& value)
{
    int result = _datum->setValue(value);
    if (result != 0)
    {
        std::string message("Invalid value: ");
        message += value;
        throw Exiv2::Error(Exiv2::kerInvalidDataset, message);
    }
}

void ExifTag::setParentImage(Image& image)
{
    Exiv2::ExifData* data = image.getExifData();
    if (data == _data)
    {
        // The parent image is already the one passed as a parameter.
        // This happens when replacing a tag by itself. In this case, don’t do
        // anything (see https://bugs.launchpad.net/pyexiv2/+bug/622739).
        return;
    }
    _data = data;
    Exiv2::Value::AutoPtr value = _datum->getValue();
    delete _datum;
    _datum = &(*_data)[_key.key()];
    _datum->setValue(value.get());

    _byteOrder = image.getByteOrder();
}

const std::string ExifTag::getKey()
{
    return _key.key();
}

const std::string ExifTag::getType()
{
    return _type;
}

const std::string ExifTag::getName()
{
    return _name;
}

const std::string ExifTag::getLabel()
{
    return _label;
}

const std::string ExifTag::getDescription()
{
    return _description;
}

const std::string ExifTag::getSectionName()
{
    return _sectionName;
}

const std::string ExifTag::getSectionDescription()
{
    return _sectionDescription;
}

const std::string ExifTag::getRawValue()
{
    return _datum->toString();
}

const std::string ExifTag::getHumanValue()
{
    return _datum->print(_data);
}

int ExifTag::getByteOrder()
{
    return _byteOrder;
}


IptcTag::IptcTag(const std::string& key, Exiv2::IptcData* data): _key(key)
{
    _from_data = (data != 0);

    if (_from_data)
    {
        _data = data;
    }
    else
    {
        _data = new Exiv2::IptcData();
        _data->add(Exiv2::Iptcdatum(_key));
    }

    Exiv2::IptcMetadata::iterator iterator = _data->findKey(_key);
    const uint16_t tag = iterator->tag();
    const uint16_t record = iterator->record();
    _type = Exiv2::TypeInfo::typeName(Exiv2::IptcDataSets::dataSetType(tag, record));
    _name = Exiv2::IptcDataSets::dataSetName(tag, record);
    _title = Exiv2::IptcDataSets::dataSetTitle(tag, record);
    _description = Exiv2::IptcDataSets::dataSetDesc(tag, record);
    // What is the photoshop name anyway? Where is it used?
    _photoshopName = Exiv2::IptcDataSets::dataSetPsName(tag, record);
    _repeatable = Exiv2::IptcDataSets::dataSetRepeatable(tag, record);
    _recordName = Exiv2::IptcDataSets::recordName(record);
    _recordDescription = Exiv2::IptcDataSets::recordDesc(record);

    if (_from_data)
    {
        // Check that we are not trying to assign multiple values to a tag that
        // is not repeatable.
        unsigned int nb_values = 0;
        for(Exiv2::IptcMetadata::iterator iterator = _data->begin();
            iterator != _data->end(); ++iterator)
        {
            if (iterator->key() == key)
            {
                ++nb_values;
                if (!_repeatable && (nb_values > 1))
                {
                    std::string mssg("Tag not repeatable: ");
                    mssg += key;
                    throw Exiv2::Error(Exiv2::kerErrorMessage, mssg);
                }
            }
        }
    }
}

IptcTag::~IptcTag()
{
    if (!_from_data)
    {
        delete _data;
    }
}

void IptcTag::setRawValues(const boost::python::list& values)
{
    if (!_repeatable && (boost::python::len(values) > 1))
    {
        // The tag is not repeatable but we are trying to assign it more than
        // one value.
        throw Exiv2::Error(Exiv2::kerInvalidDataset, "Tag not repeatable");
    }

    unsigned int index = 0;
    unsigned int max = boost::python::len(values);
    Exiv2::IptcMetadata::iterator iterator = _data->findKey(_key);
    while (index < max)
    {
        std::string value = boost::python::extract<std::string>(values[index++]);
        if (iterator != _data->end())
        {
            // Override an existing value
            int result = iterator->setValue(value);
            if (result != 0)
            {
                std::string mssg("Invalid value: ");
                mssg += value;
                // there's no invalid value error in libexiv2, so we use
                // kerInvalidDataset wich raise a Python ValueError
                throw Exiv2::Error(Exiv2::kerInvalidDataset, mssg);
            }
            // Jump to the next datum matching the key
            ++iterator;
            while ((iterator != _data->end()) && (iterator->key() != _key.key()))
            {
                ++iterator;
            }
        }
        else
        {
            // Append a new value
            Exiv2::Iptcdatum datum(_key);
            int result = datum.setValue(value);
            if (result != 0)
            {
                std::string mssg("Invalid value: ");
                mssg += value;
                throw Exiv2::Error(Exiv2::kerErrorMessage, mssg);
            }
            int state = _data->add(datum);
            if (state == 6)
            {
                std::string mssg("Tag not repeatable: ");
                mssg += _key.key();
                throw Exiv2::Error(Exiv2::kerErrorMessage, mssg);
            }
            // Reset iterator that has been invalidated by appending a datum
            iterator = _data->end();
        }
    }
    // Erase the remaining values if any
    while (iterator != _data->end())
    {
        if (iterator->key() == _key.key())
        {
            iterator = _data->erase(iterator);
        }
        else
        {
            ++iterator;
        }
    }
}

void IptcTag::setParentImage(Image& image)
{
    Exiv2::IptcData* data = image.getIptcData();
    if (data == _data)
    {
        // The parent image is already the one passed as a parameter.
        // This happens when replacing a tag by itself. In this case, don’t do
        // anything (see https://bugs.launchpad.net/pyexiv2/+bug/622739).
        return;
    }
    const boost::python::list values = getRawValues();
    delete _data;
    _from_data = true;
    _data = data;
    setRawValues(values);
}

const std::string IptcTag::getKey()
{
    return _key.key();
}

const std::string IptcTag::getType()
{
    return _type;
}

const std::string IptcTag::getName()
{
    return _name;
}

const std::string IptcTag::getTitle()
{
    return _title;
}

const std::string IptcTag::getDescription()
{
    return _description;
}

const std::string IptcTag::getPhotoshopName()
{
    return _photoshopName;
}

const bool IptcTag::isRepeatable()
{
    return _repeatable;
}

const std::string IptcTag::getRecordName()
{
    return _recordName;
}

const std::string IptcTag::getRecordDescription()
{
    return _recordDescription;
}

const boost::python::list IptcTag::getRawValues()
{
    boost::python::list values;
    for(Exiv2::IptcMetadata::iterator iterator = _data->begin();
        iterator != _data->end(); ++iterator)
    {
        if (iterator->key() == _key.key())
        {
            values.append(iterator->toString());
        }
    }
    return values;
}


XmpTag::XmpTag(const std::string& key, Exiv2::Xmpdatum* datum): _key(key)
{
    _from_datum = (datum != 0);

    if (_from_datum)
    {
        _datum = datum;
        _exiv2_type = datum->typeName();
    }
    else
    {
        _datum = new Exiv2::Xmpdatum(_key);
        _exiv2_type = Exiv2::TypeInfo::typeName(Exiv2::XmpProperties::propertyType(_key));
    }

    const char* title = Exiv2::XmpProperties::propertyTitle(_key);
    if (title != 0)
    {
        _title = title;
    }

    const char* description = Exiv2::XmpProperties::propertyDesc(_key);
    if (description != 0)
    {
        _description = description;
    }

    const Exiv2::XmpPropertyInfo* info = Exiv2::XmpProperties::propertyInfo(_key);
    if (info != 0)
    {
        _name = info->name_;
        _type = info->xmpValueType_;
    }
}

XmpTag::~XmpTag()
{
    if (!_from_datum)
    {
        delete _datum;
    }
}

void XmpTag::setTextValue(const std::string& value)
{
    _datum->setValue(value);
}

void XmpTag::setArrayValue(const boost::python::list& values)
{
    // Reset the value
    _datum->setValue(0);

    for(boost::python::stl_input_iterator<std::string> iterator(values);
        iterator != boost::python::stl_input_iterator<std::string>();
        ++iterator)
    {
        _datum->setValue(*iterator);
    }
}

void XmpTag::setLangAltValue(const boost::python::dict& values)
{
    // Reset the value
    _datum->setValue(0);

    for(boost::python::stl_input_iterator<std::string> iterator(values);
        iterator != boost::python::stl_input_iterator<std::string>();
        ++iterator)
    {
        std::string key = *iterator;
        std::string value = boost::python::extract<std::string>(values.get(key));
        _datum->setValue("lang=\"" + key + "\" " + value);
    }
}

void XmpTag::setParentImage(Image& image)
{
    Exiv2::Xmpdatum* datum = &(*image.getXmpData())[_key.key()];
    if (datum == _datum)
    {
        // The parent image is already the one passed as a parameter.
        // This happens when replacing a tag by itself. In this case, don’t do
        // anything (see https://bugs.launchpad.net/pyexiv2/+bug/622739).
        return;
    }
    Exiv2::Value::AutoPtr value = _datum->getValue();
    delete _datum;
    _from_datum = true;
    _datum = &(*image.getXmpData())[_key.key()];
    _datum->setValue(value.get());
}

const std::string XmpTag::getKey()
{
    return _key.key();
}

const std::string XmpTag::getExiv2Type()
{
    return _exiv2_type;
}

const std::string XmpTag::getType()
{
    return _type;
}

const std::string XmpTag::getName()
{
    return _name;
}

const std::string XmpTag::getTitle()
{
    return _title;
}

const std::string XmpTag::getDescription()
{
    return _description;
}

const std::string XmpTag::getTextValue()
{
    return dynamic_cast<const Exiv2::XmpTextValue*>(&_datum->value())->value_;
}

const boost::python::list XmpTag::getArrayValue()
{
    // We can't use &_datum->value())->value_ because value_ is private in
    // this context (change in libexiv2 0.27)
    const Exiv2::XmpArrayValue* xav =
            dynamic_cast<const Exiv2::XmpArrayValue*>(&_datum->value());
    boost::python::list rvalue;
    for(int i = 0; i < xav->count(); ++i)
    {
        std::string value = xav->toString(i);
        rvalue.append(value);
    }
    return rvalue;
}

const boost::python::dict XmpTag::getLangAltValue()
{
    Exiv2::LangAltValue::ValueType value =
        dynamic_cast<const Exiv2::LangAltValue*>(&_datum->value())->value_;
    boost::python::dict rvalue;
    for (Exiv2::LangAltValue::ValueType::const_iterator i = value.begin();
         i != value.end(); ++i)
    {
        rvalue[i->first] = i->second;
    }
    return rvalue;
}


Preview::Preview(const Exiv2::PreviewImage& previewImage)
{
    _mimeType = previewImage.mimeType();
    _extension = previewImage.extension();
    _size = previewImage.size();
    _dimensions = boost::python::make_tuple(previewImage.width(),
                                            previewImage.height());

    // Copy the data buffer in a string. Since the data buffer can contain null
    // characters ('\x00'), the string cannot be simply constructed like that:
    //     _data = std::string((char*) previewImage.pData());
    // because it would be truncated after the first occurence of a null
    // character. Therefore, it has to be copied character by character.
    const Exiv2::byte* pData = previewImage.pData();
    // First allocate the memory for the whole string...
    _data = std::string(_size, ' ');
    // ... then fill it with the raw data.
    for(unsigned int i = 0; i < _size; ++i)
    {
        _data[i] = pData[i];
    }
}

boost::python::object Preview::getData() const
{
    return boost::python::object(boost::python::handle<>(
        PyBytes_FromStringAndSize(_data.c_str(), _size)
        ));
}

void Preview::writeToFile(const std::string& path) const
{
    std::string filename = path + _extension;
    std::ofstream fd(filename.c_str(), std::ios::out | std::ios::binary);
    fd << _data;
    fd.close();
}

void translateExiv2Error(Exiv2::Error const& error)
{
    // Use the Python 'C' API to set up an exception object
    const char* message = error.what();

    // The type of the Python exception depends on the error code
    // Warning: this piece of code should be updated in case the error codes
    // defined by Exiv2 (file 'src/error.cpp') are changed.
    // The cast is because error.code() returns an int.
    switch ((Exiv2::ErrorCode)error.code())
    {
        // I/O error while reading or writing an image.  There may be
        // embedded strerror() text.  Unfortunately the corresponding
        // errno value is lost, which means we can't use PyErr_SetFromErrno
        // to get a fine-grained OSError subclass.
    case Exiv2::kerDataSourceOpenFailed:
    case Exiv2::kerFileOpenFailed:
    case Exiv2::kerFailedToReadImageData:
    case Exiv2::kerFailedToMapFileForReadWrite:
    case Exiv2::kerFileRenameFailed:
    case Exiv2::kerTransferFailed:
    case Exiv2::kerMemoryTransferFailed:
    case Exiv2::kerInputDataReadFailed:
    case Exiv2::kerImageWriteFailed:
    case Exiv2::kerOffsetOutOfRange:
        PyErr_SetString(PyExc_IOError, message);
        return;

        // Errors relating to an invalid value for a tag.
    case Exiv2::kerInvalidDataset:
    case Exiv2::kerValueNotSet:
    case Exiv2::kerValueTooLarge:
    case Exiv2::kerDataAreaValueTooLarge:
    case Exiv2::kerInvalidCharset:
    case Exiv2::kerUnsupportedDateFormat:
    case Exiv2::kerUnsupportedTimeFormat:
    case Exiv2::kerInvalidSettingForImage:
    case Exiv2::kerTooLargeJpegSegment:
    case Exiv2::kerDecodeLangAltPropertyFailed:
    case Exiv2::kerDecodeLangAltQualifierFailed:
    case Exiv2::kerEncodeLangAltPropertyFailed:
    case Exiv2::kerInvalidXmpText:
    case Exiv2::kerInvalidKeyXmpValue:
        PyErr_SetString(PyExc_ValueError, message);
        return;

        // Errors relating to an invalid name or code for a tag.
    case Exiv2::kerInvalidRecord:
    case Exiv2::kerInvalidKey:
    case Exiv2::kerInvalidTag:
    case Exiv2::kerInvalidIfdId:
    case Exiv2::kerNoNamespaceInfoForXmpPrefix:
    case Exiv2::kerNoPrefixForNamespace:
    case Exiv2::kerPropertyNameIdentificationFailed:
    case Exiv2::kerSchemaNamespaceNotRegistered:
    case Exiv2::kerNoNamespaceForPrefix:
        PyErr_SetString(PyExc_KeyError, message);
        return;

        // The image is in an unrecognized format.
        // TypeError doesn't make a whole lot of sense, but none of the
        // other exception classes make _more_ sense.
    case Exiv2::kerNotAnImage:
    case Exiv2::kerFileContainsUnknownImageType:
    case Exiv2::kerMemoryContainsUnknownImageType:
    case Exiv2::kerNotAJpeg:
    case Exiv2::kerNoImageInInputData:
    case Exiv2::kerNotACrwImage:
    case Exiv2::kerTooManyTiffDirectoryEntries:
    case Exiv2::kerMultipleTiffArrayElementTagsInDirectory:
    case Exiv2::kerWrongTiffArrayElementTagType:
    case Exiv2::kerInvalidIccProfile:
    case Exiv2::kerInvalidXMP:
    case Exiv2::kerTiffDirectoryTooLarge:
    case Exiv2::kerInvalidTypeValue:
    case Exiv2::kerCorruptedMetadata:
        PyErr_SetString(PyExc_TypeError, message);
        return;

        // Caller asked to use an image format, or a feature of an
        // image format, that has not yet been implemented by libexiv2.
    case Exiv2::kerUnsupportedImageType:
    case Exiv2::kerUnsupportedDataAreaOffsetType:
    case Exiv2::kerWritingImageFormatUnsupported:
    case Exiv2::kerFunctionNotSupported:
    case Exiv2::kerUnhandledXmpdatum:
    case Exiv2::kerUnhandledXmpNode:
    case Exiv2::kerAliasesNotSupported:
        PyErr_SetString(PyExc_NotImplementedError, message);
        return;

        // Memory allocation failure
    case Exiv2::kerInvalidMalloc:
    case Exiv2::kerMallocFailed:
        PyErr_SetString(PyExc_MemoryError, message);
        return;

        // Arithmetic overflow
    case Exiv2::kerArithmeticOverflow:
        PyErr_SetString(PyExc_OverflowError, message);
        return;

        // Should be impossible
    case Exiv2::kerSuccess:
        PyErr_SetString(PyExc_AssertionError, message);
        return;

        // We can't be more specific than a RuntimeError.
    case Exiv2::kerGeneralError:
    case Exiv2::kerErrorMessage:
    case Exiv2::kerCallFailed:
    case Exiv2::kerXMPToolkitError:
        break;
    }

    // Putting the fallback action below the switch statement, instead
    // of having a 'default' entry, makes some compilers issue
    // warnings if we don't mention every single kerXXX code in the
    // switch statement.
    PyErr_SetString(PyExc_RuntimeError, message);
}


bool initialiseXmpParser()
{
    if (!Exiv2::XmpParser::initialize())
        return false;

    std::string prefix("py3exiv2");
    std::string name("www.py3exiv2.tuxfamily.org/");

    try
    {
        const std::string& ns = Exiv2::XmpProperties::ns(prefix);
    }

    catch (Exiv2::Error& error)
    {
        // No namespace exists with the requested prefix, it is safe to
        // register a new one.
        Exiv2::XmpProperties::registerNs(name, prefix);
    }

    return true;
}

bool closeXmpParser()
{
    std::string name("www.py3exiv2.tuxfamily.org/");
    const std::string& prefix = Exiv2::XmpProperties::prefix(name);
    if (prefix != "")
    {
        Exiv2::XmpProperties::unregisterNs(name);
    }

    Exiv2::XmpParser::terminate();

    return true;
}

void registerXmpNs(const std::string& name, const std::string& prefix)
{
    try
    {
        const std::string& ns = Exiv2::XmpProperties::ns(prefix);
    }

    catch (Exiv2::Error& error)
    {
        // No namespace exists with the requested prefix, it is safe to
        // register a new one.
        Exiv2::XmpProperties::registerNs(name, prefix);
        return;
    }

    std::string mssg("Namespace already exists: ");
    mssg += prefix;
    throw Exiv2::Error(Exiv2::kerInvalidKey, mssg);
}

void unregisterXmpNs(const std::string& name)
{
    const std::string& prefix = Exiv2::XmpProperties::prefix(name);
    if (prefix != "")
    {
        Exiv2::XmpProperties::unregisterNs(name);
        try
        {
            (void) Exiv2::XmpProperties::nsInfo(prefix);
        }
        catch (Exiv2::Error& error)
        {
            // The namespace has been successfully unregistered.
            return;
        }

        // The namespace hasn’t been unregistered because it’s builtin.
        std::string mssg("Can't unregister builtin namespace: ");
        mssg += name;
        throw Exiv2::Error(Exiv2::kerInvalidKey, mssg);
    }
    else
    {
        std::string mssg("Namespace does not exist: ");
        mssg += name;
        throw Exiv2::Error(Exiv2::kerInvalidKey, mssg);
    }
}

void unregisterAllXmpNs()
{
    // Unregister all custom namespaces.
    Exiv2::XmpProperties::unregisterNs();
}

} // End of anonymous namespace

using namespace boost::python;

BOOST_PYTHON_MODULE(_libexiv2)
{
    scope().attr("exiv2_version_info") = \
        boost::python::make_tuple(EXIV2_MAJOR_VERSION,
                                  EXIV2_MINOR_VERSION,
                                  EXIV2_PATCH_VERSION);

    register_exception_translator<Exiv2::Error>(&translateExiv2Error);

    // Swallow all warnings and error messages written by libexiv2 to stderr
    // (if it was compiled with DEBUG or without SUPPRESS_WARNINGS).
    // See https://bugs.launchpad.net/pyexiv2/+bug/507620.
    std::cerr.rdbuf(NULL);

    class_<ExifTag>("_ExifTag", init<std::string>())

        .def("_setRawValue", &ExifTag::setRawValue)
        .def("_setParentImage", &ExifTag::setParentImage)

        .def("_getKey", &ExifTag::getKey)
        .def("_getType", &ExifTag::getType)
        .def("_getName", &ExifTag::getName)
        .def("_getLabel", &ExifTag::getLabel)
        .def("_getDescription", &ExifTag::getDescription)
        .def("_getSectionName", &ExifTag::getSectionName)
        .def("_getSectionDescription", &ExifTag::getSectionDescription)
        .def("_getRawValue", &ExifTag::getRawValue)
        .def("_getHumanValue", &ExifTag::getHumanValue)
        .def("_getByteOrder", &ExifTag::getByteOrder)
    ;

    class_<IptcTag>("_IptcTag", init<std::string>())

        .def("_setRawValues", &IptcTag::setRawValues)
        .def("_setParentImage", &IptcTag::setParentImage)

        .def("_getKey", &IptcTag::getKey)
        .def("_getType", &IptcTag::getType)
        .def("_getName", &IptcTag::getName)
        .def("_getTitle", &IptcTag::getTitle)
        .def("_getDescription", &IptcTag::getDescription)
        .def("_getPhotoshopName", &IptcTag::getPhotoshopName)
        .def("_isRepeatable", &IptcTag::isRepeatable)
        .def("_getRecordName", &IptcTag::getRecordName)
        .def("_getRecordDescription", &IptcTag::getRecordDescription)
        .def("_getRawValues", &IptcTag::getRawValues)
    ;

    class_<XmpTag>("_XmpTag", init<std::string>())

        .def("_setTextValue", &XmpTag::setTextValue)
        .def("_setArrayValue", &XmpTag::setArrayValue)
        .def("_setLangAltValue", &XmpTag::setLangAltValue)
        .def("_setParentImage", &XmpTag::setParentImage)

        .def("_getKey", &XmpTag::getKey)
        .def("_getExiv2Type", &XmpTag::getExiv2Type)
        .def("_getType", &XmpTag::getType)
        .def("_getName", &XmpTag::getName)
        .def("_getTitle", &XmpTag::getTitle)
        .def("_getDescription", &XmpTag::getDescription)
        .def("_getTextValue", &XmpTag::getTextValue)
        .def("_getArrayValue", &XmpTag::getArrayValue)
        .def("_getLangAltValue", &XmpTag::getLangAltValue)
    ;

    class_<Preview>("_Preview", init<Exiv2::PreviewImage>())

        .def_readonly("mime_type", &Preview::_mimeType)
        .def_readonly("extension", &Preview::_extension)
        .def_readonly("size", &Preview::_size)
        .def_readonly("dimensions", &Preview::_dimensions)
        .def_readonly("data", &Preview::_data)

        .def("get_data", &Preview::getData)
        .def("write_to_file", &Preview::writeToFile)
    ;

    class_<Image>("_Image", init<std::string>())
        .def(init<std::string, long>())

        .def("_readMetadata", &Image::readMetadata)
        .def("_writeMetadata", &Image::writeMetadata)

        .def("_getPixelWidth", &Image::pixelWidth)
        .def("_getPixelHeight", &Image::pixelHeight)

        .def("_getMimeType", &Image::mimeType)

        .def("_exifKeys", &Image::exifKeys)
        .def("_getExifTag", &Image::getExifTag)
        .def("_deleteExifTag", &Image::deleteExifTag)

        .def("_iptcKeys", &Image::iptcKeys)
        .def("_getIptcTag", &Image::getIptcTag)
        .def("_deleteIptcTag", &Image::deleteIptcTag)

        .def("_xmpKeys", &Image::xmpKeys)
        .def("_getXmpTag", &Image::getXmpTag)
        .def("_deleteXmpTag", &Image::deleteXmpTag)

        .def("_getComment", &Image::getComment)
        .def("_setComment", &Image::setComment)
        .def("_clearComment", &Image::clearComment)

        .def("_previews", &Image::previews)

        .def("_copyMetadata", &Image::copyMetadata)

        .def("_getDataBuffer", &Image::getDataBuffer)

        .def("_getExifThumbnailMimeType", &Image::getExifThumbnailMimeType)
        .def("_getExifThumbnailExtension", &Image::getExifThumbnailExtension)
        .def("_writeExifThumbnailToFile", &Image::writeExifThumbnailToFile)
        .def("_getExifThumbnailData", &Image::getExifThumbnailData)
        .def("_eraseExifThumbnail", &Image::eraseExifThumbnail)
        .def("_setExifThumbnailFromFile", &Image::setExifThumbnailFromFile)
        .def("_setExifThumbnailFromData", &Image::setExifThumbnailFromData)

        .def("_getIptcCharset", &Image::getIptcCharset)
    ;

    def("_initialiseXmpParser", initialiseXmpParser);
    def("_closeXmpParser", closeXmpParser);
    def("_registerXmpNs", registerXmpNs, args("name", "prefix"));
    def("_unregisterXmpNs", unregisterXmpNs, args("name"));
    def("_unregisterAllXmpNs", unregisterAllXmpNs);
}

// Local Variables:
// c-basic-offset: 4
// c-file-style: "gnu"
// c-file-offsets: ((innamespace . 0) (substatement-open . 0))
// End:
