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

#ifndef CYEXIV2_LIBEXIV2_IF_HPP
#define CYEXIV2_LIBEXIV2_IF_HPP 1

// Shims between libexiv2's raw API and Cython.  Some of this code has
// to be written in C++, some of it is easier to write in C++, and
// some of it exists primarily so that libexiv2_if.pxd doesn't have to
// deal with namespaces.

#include <ios>
#include <new>
#include <stdexcept>
#include <string>
#include <typeinfo>

#include <Python.h>

#include <exiv2/exiv2.hpp>

#if EXIV2_MAJOR_VERSION == 0 && EXIV2_MINOR_VERSION < 27
# error "libexiv2 is too old (version 0.27 or later required)"
#endif

namespace {

// RAII class to release and re-acquire the GIL.
struct release_gil
{
    release_gil()
        : state(PyEval_SaveThread())
    {}

    ~release_gil()
    {
        PyEval_RestoreThread(state);
    }

private:
    PyThreadState *state;

    release_gil(release_gil const&) = delete;
    release_gil& operator=(release_gil const&) = delete;
};

// RAII class to save and restore an Exiv2::BasicIo seek position
// (if the file is already open) or open the file and close it again
// (if it wasn't already open).  Exiv2::IoCloser only handles the
// second case, unfortunately.
struct preserve_read_state
{
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

private:
    Exiv2::BasicIo& io;
    long pos;

    preserve_read_state(preserve_read_state const&) = delete;
    preserve_read_state& operator=(preserve_read_state const&) = delete;
};

// Exception translation.  We have custom handling for Exiv2::Error
// exceptions, and preserve Cython's semantics for std:: exceptions.

void translateExiv2Error(Exiv2::Error const& error)
{
    char const* message = error.what();

    // Choose the type of the Python exception depending on the error
    // code.  This switch statement must cover every enumeration
    // constant defined for Exiv2::ErrorCode (see <exiv2/error.hpp>).
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
        PyErr_SetString(PyExc_OSError, message);
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

// The Cython documentation doesn't explain very well how to write the
// function named in 'except +translate' notation.  Based on a combination
// of <https://stackoverflow.com/a/29002414> and reverse engineering the
// generated code:
//
// * A custom exception translator has to be written in C++, and its
//   correct signature is `void exception_to_pyerr(void)`.  It will be
//   called from inside a `catch (...)` block; you use `try { throw; }`
//   followed by catch clauses to get access to the exception object
//   and dispatch on its type.
//
// * The translator should use the PyErr_* API to raise a Python
//   exception based on the C++ exception.  On exit from the
//   translator, PyErr_Occurred() must be true.
//
// * The translator _replaces_ the stock translator.  If you want
//   Cython's stock handling for std::exception subclasses, you must
//   reimplement this yourself.  The std::exception catch clauses
//   below are copied from __Pyx_CppExn2PyErr, which is the stock
//   translator, used for 'except +'.

void exception_to_pyerr()
{
    try {
        throw;
    } catch (Exiv2::Error& exn) {
        translateExiv2Error(exn);
    } catch (const std::bad_alloc& exn) {
        PyErr_SetString(PyExc_MemoryError, exn.what());
    } catch (const std::bad_cast& exn) {
        PyErr_SetString(PyExc_TypeError, exn.what());
    } catch (const std::bad_typeid& exn) {
        PyErr_SetString(PyExc_TypeError, exn.what());
    } catch (const std::domain_error& exn) {
        PyErr_SetString(PyExc_ValueError, exn.what());
    } catch (const std::invalid_argument& exn) {
        PyErr_SetString(PyExc_ValueError, exn.what());
    } catch (const std::ios_base::failure& exn) {
        PyErr_SetString(PyExc_IOError, exn.what());
    } catch (const std::out_of_range& exn) {
        PyErr_SetString(PyExc_IndexError, exn.what());
    } catch (const std::overflow_error& exn) {
        PyErr_SetString(PyExc_OverflowError, exn.what());
    } catch (const std::range_error& exn) {
        PyErr_SetString(PyExc_ArithmeticError, exn.what());
    } catch (const std::underflow_error& exn) {
        PyErr_SetString(PyExc_ArithmeticError, exn.what());
    } catch (const std::exception& exn) {
        PyErr_SetString(PyExc_RuntimeError, exn.what());
    } catch (...) {
        PyErr_SetString(PyExc_RuntimeError, "Unknown exception");
    }
}

//
// Access to the XMP parser's namespace registration hooks in
// libexiv2.  Caution: the libexiv2 APIs that these functions call
// mutate global state within the library, and do no locking
// themselves.  We are currently relying on Python's global
// interpreter lock to ensure that only one thread calls these
// functions at a time.
//

bool initialiseXmpParser()
{
    if (!Exiv2::XmpParser::initialize())
        return false;

    std::string prefix("py3exiv2");
    std::string name("www.py3exiv2.tuxfamily.org/");

    try
    {
        (void) Exiv2::XmpProperties::ns(prefix);
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
        (void) Exiv2::XmpProperties::ns(prefix);
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

//
// Intermediate shim classes.  Each of these corresponds to a public
// class defined in _libexiv2.pyx, so that C++-level data management
// can be handled in C++, where it's easier to reason about.
// Note: due to limitations in Cython, these classes must all have
// nullary constructors.
//

struct Image;

using Exiv2::Exifdatum;
using Exiv2::ExifData;

struct ExifTag
{
    ExifTag()
        : _key(0), _datum(0), _data(0), _byteorder(Exiv2::invalidByteOrder)
    {}

    ~ExifTag()
    {
        delete _key;
        if (_data == 0)
        {
            delete _datum;
        }
    }

    // Initialize without an image object
    void init(std::string const& key)
    {
        if (_key)
        {
            throw Exiv2::Error(Exiv2::kerErrorMessage,
                               "ExifTag::init(1): already initialized");
        }
        _key = new Exiv2::ExifKey(key);
        _datum = new Exiv2::Exifdatum(*_key);
    }

    // Initialize from an image object
    void init(std::string const& key,
              Exiv2::Exifdatum* datum, Exiv2::ExifData* data,
              Exiv2::ByteOrder byteorder)
    {
        if (_key)
        {
            throw Exiv2::Error(Exiv2::kerErrorMessage,
                               "ExifTag::init(2): already initialized");
        }
        _key = new Exiv2::ExifKey(key);
        _datum = datum;
        _data = data;
        _byteorder = byteorder;
    }

    std::string getKey()
    {
        return _key->key();
    }

    void setParentImage(Image& image);

    std::string getRawValue()
    {
        return _datum->toString();
    }

    void setRawValue(std::string const& value)
    {
        if (_datum->setValue(value))
        {
            std::string message("Invalid value: ");
            message += value;
            throw Exiv2::Error(Exiv2::kerInvalidDataset, message);
        }
    }

    std::string getHumanValue()
    {
        return _datum->print(_data);
    }

    int getByteOrder()
    {
        return _byteorder;
    }

    char const* getType()
    {
        // Use the type of the datum when possible; fall back to
        // static type information for the key when the datum's type
        // hasn't been set, or if it's Undefined.  The latter case is
        // primarily for user comments, where the datum type will be
        // Undefined but the key type will be Comment.
        if (_data != 0 && _datum->typeId() != Exiv2::undefined)
        {
            char const* name = _datum->typeName();
            if (name)
            {
                return name;
            }
        }
        return Exiv2::TypeInfo::typeName(_key->defaultTypeId());
    }

    std::string getName()
    {
        return _key->tagName();
    }

    std::string getLabel()
    {
        return _key->tagLabel();
    }

    std::string getDescription()
    {
        return _key->tagDesc();
    }

    char const* getSectionName()
    {
        return Exiv2::ExifTags::sectionName(*_key);
    }

private:
    Exiv2::ExifKey* _key;
    Exiv2::Exifdatum* _datum;
    Exiv2::ExifData* _data;
    Exiv2::ByteOrder _byteorder;

    ExifTag(ExifTag const&) = delete;
    ExifTag& operator=(ExifTag const&) = delete;
};

using Exiv2::IptcData;

struct IptcTag
{
    IptcTag()
        : _key(0), _data(0), _tag(0), _record(0),
          _from_data(false), _repeatable(false)
    {}

    ~IptcTag()
    {
        delete _key;
        if (!_from_data)
        {
            delete _data;
        }
    }

    // Initialize without an image object
    void init(std::string const& key)
    {
        if (_key)
        {
            throw Exiv2::Error(Exiv2::kerErrorMessage,
                               "IptcTag::init(1): already initialized");
        }
        _key = new Exiv2::IptcKey(key);
        _data = new Exiv2::IptcData();
        _tag = _key->tag();
        _record = _key->record();
        _from_data = false;
        _repeatable = Exiv2::IptcDataSets::dataSetRepeatable(_tag, _record);
    }

    // Initialize from an image object
    void init(std::string const& key, Exiv2::IptcData* data)
    {
        if (_key)
        {
            throw Exiv2::Error(Exiv2::kerErrorMessage,
                               "IptcTag::init(2): already initialized");
        }
        _key = new Exiv2::IptcKey(key);
        _data = data;

        Exiv2::IptcMetadata::iterator i = _data->findKey(*_key);
        _tag = i->tag();
        _record = i->record();
        _from_data = true;
        _repeatable = Exiv2::IptcDataSets::dataSetRepeatable(_tag, _record);

        if (!_repeatable)
        {
            // Check that we are not trying to assign multiple values
            // to a tag that is not repeatable.
            unsigned int nb_values = 0;
            for (i = _data->begin(); i != _data->end(); ++i)
            {
                if (i->key() == key)
                {
                    ++nb_values;
                    if (nb_values > 1)
                    {
                        std::string msg("Tag not repeatable: ");
                        msg += key;
                        throw Exiv2::Error(Exiv2::kerInvalidRecord, msg);
                    }
                }
            }
        }
    }

    std::string getKey()
    {
        return _key->key();
    }

    void setParentImage(Image& image);

    void clearRawValues()
    {
        Exiv2::IptcMetadata::iterator i = _data->begin();
        while (i != _data->end())
        {
            if (i->record() == _record && i->tag() == _tag)
            {
                i = _data->erase(i);
            }
            else
            {
                ++i;
            }
        }
    }

    void addRawValue(std::string const& value)
    {
        Exiv2::Iptcdatum datum(*_key);
        if (datum.setValue(value))
        {
            // there's no invalid value error in libexiv2, so we use
            // kerInvalidDataset which is translated to a ValueError
            std::string msg("Invalid value: ");
            msg += value;
            throw Exiv2::Error(Exiv2::kerInvalidDataset, msg);
        }

        int result = _data->add(datum);
        if (result == 6)
        {
            /* attempt to add a second copy of a non-repeatable tag */
            std::string msg("Tag not repeatable: ");
            msg += _key->key();
            throw Exiv2::Error(Exiv2::kerInvalidRecord, msg);
        }
        else if (result != 0)
        {
            /* some other error? */
            std::string msg("IptcTag::addRawValue: error #");
            msg += std::to_string(result);
            throw Exiv2::Error(Exiv2::kerErrorMessage, msg);
        }
    }

    char const* getType()
    {
        return Exiv2::TypeInfo::typeName(
            Exiv2::IptcDataSets::dataSetType(_tag, _record));
    }

    uint16_t getTag() const
    {
        return _tag;
    }

    uint16_t getRecord() const
    {
        return _record;
    }

    bool isRepeatable() const
    {
        return _repeatable;
    }

    Exiv2::IptcData* getData() const
    {
        return _data;
    }

    std::string getName()
    {
        return Exiv2::IptcDataSets::dataSetName(_tag, _record);
    }

    char const* getTitle()
    {
        return Exiv2::IptcDataSets::dataSetTitle(_tag, _record);
    }

    char const* getDescription()
    {
        return Exiv2::IptcDataSets::dataSetDesc(_tag, _record);
    }

    char const* getPhotoshopName()
    {
        return Exiv2::IptcDataSets::dataSetPsName(_tag, _record);
    }

    std::string getRecordName()
    {
        return Exiv2::IptcDataSets::recordName(_record);
    }

    char const* getRecordDescription()
    {
        return Exiv2::IptcDataSets::recordDesc(_record);
    }

private:
    Exiv2::IptcKey* _key;
    Exiv2::IptcData* _data;
    uint16_t _tag;
    uint16_t _record;
    bool _from_data;
    bool _repeatable;

    IptcTag(IptcTag const&) = delete;
    IptcTag& operator=(IptcTag const&) = delete;
};

using Exiv2::XmpData;
using Exiv2::XmpArrayValue;
using XmpLangAltValue = Exiv2::LangAltValue::ValueType;

struct XmpTag
{
    XmpTag()
        : _key(0), _datum(0), _from_datum(false)
    {}

    ~XmpTag()
    {
        delete _key;
        if (!_from_datum)
        {
            delete _datum;
        }
    }

    void init(const std::string& key)
    {
        if (_key)
        {
            throw Exiv2::Error(Exiv2::kerErrorMessage,
                               "XmpTag::init(1): already initialized");
        }
        _key = new Exiv2::XmpKey(key);
        _datum = new Exiv2::Xmpdatum(*_key);
        _from_datum = false;
    }

    void init(const std::string& key, Exiv2::Xmpdatum* datum)
    {
        if (_key)
        {
            throw Exiv2::Error(Exiv2::kerErrorMessage,
                               "XmpTag::init(2): already initialized");
        }
        _key = new Exiv2::XmpKey(key);
        _datum = datum;
        _from_datum = true;
    }

    std::string getKey()
    {
        return _key->key();
    }

    void setParentImage(Image& image);

    void resetValue()
    {
        _datum->setValue(0);
    }

    void appendValue(const std::string& value)
    {
        _datum->setValue(value);
    }

    std::string getTextValue()
    {
        auto tval = dynamic_cast<const Exiv2::XmpTextValue*>(&_datum->value());
        return tval->value_;
    }

    XmpArrayValue const* getArrayValue()
    {
        return dynamic_cast<const Exiv2::XmpArrayValue*>(&_datum->value());
    }

    XmpLangAltValue const* getLangAltValue()
    {
        return &(dynamic_cast<const Exiv2::LangAltValue*>
                 (&_datum->value())->value_);
    }

    char const* getType()
    {
        auto info = Exiv2::XmpProperties::propertyInfo(*_key);
        if (info != 0)
        {
            return info->xmpValueType_;
        }
        return "";
    }

    char const* getExiv2Type()
    {
        if (_from_datum)
        {
            return _datum->typeName();
        }
        else
        {
            return Exiv2::TypeInfo::typeName(
                Exiv2::XmpProperties::propertyType(*_key));
        }
    }

    char const* getName()
    {
        auto info = Exiv2::XmpProperties::propertyInfo(*_key);
        if (info != 0)
        {
            return info->name_;
        }
        return "";
    }

    char const* getTitle()
    {
        return Exiv2::XmpProperties::propertyTitle(*_key);
    }

    char const* getDescription()
    {
        return Exiv2::XmpProperties::propertyDesc(*_key);
    }

private:
    Exiv2::XmpKey* _key;
    Exiv2::Xmpdatum* _datum;
    bool _from_datum; // whether the tag is built from an existing Xmpdatum

    XmpTag(XmpTag const&) = delete;
    XmpTag& operator=(XmpTag const&) = delete;
};

using Exiv2::PreviewImage;
using Exiv2::PreviewManager;
using Exiv2::PreviewProperties;
using Exiv2::PreviewPropertiesList;

struct Image
{
    Image()
        : _filename(), _data(0), _size(0), _image(), _exifThumbnail(),
          _dataRead(false)
    {}

    ~Image()
    {
        if (_data != 0)
        {
            delete[] _data;
        }
    }

    void init(std::string const& filename)
    {
        if (_image.get() != 0 || _exifThumbnail != 0 || _dataRead)
        {
            throw Exiv2::Error(Exiv2::kerErrorMessage,
                               "Image::init(1): already initialized");
        }

        // Release the GIL to allow other python threads to run
        // while opening the file.
        release_gil until_return;

        _filename = filename;
        _data = 0;
        _image = Exiv2::ImageFactory::open(_filename);
        assert(_image.get() != 0);
    }

    void init(void const* buffer, unsigned long size)
    {
        if (_image.get() != 0 || _exifThumbnail != 0 || _dataRead)
        {
            throw Exiv2::Error(Exiv2::kerErrorMessage,
                               "Image::init(2): already initialized");
        }

        // Release the GIL to allow other python threads to run
        // while copying the buffer.
        release_gil until_return;

        // We're copying out of a Python buffer object, but our caller
        // pins a reference (via PyObject_GetBuffer()), so it's safe
        // to do this without holding the GIL.
        _size = size;
        _data = new Exiv2::byte[_size];
        memcpy(_data, buffer, _size);
        _image = Exiv2::ImageFactory::open(_data, _size);
        assert(_image.get() != 0);
    }

    void readMetadata()
    {
        // Release the GIL to allow other python threads to run
        // while reading metadata.
        release_gil until_return;

        _image->readMetadata();
        _dataRead = true;
    }

    void writeMetadata()
    {
        check_metadata_read();

        // Release the GIL to allow other python threads to run
        // while writing metadata.
        release_gil until_return;
        _image->writeMetadata();
    }

    void copyMetadata(Image& other, bool exif, bool iptc, bool xmp) const
    {
        check_metadata_read();
        other.check_metadata_read();

        if (exif)
            other._image->setExifData(*getExifData());
        if (iptc)
            other._image->setIptcData(*getIptcData());
        if (xmp)
            other._image->setXmpData(*getXmpData());
    }

    // Read-only access to the dimensions of the picture.
    unsigned int pixelWidth() const
    {
        check_metadata_read();
        return _image->pixelWidth();
    }

    unsigned int pixelHeight() const
    {
        check_metadata_read();
        return _image->pixelHeight();
    }

    // Read-only access to the MIME type of the image.
    std::string mimeType() const
    {
        check_metadata_read();
        return _image->mimeType();
    }

    // Return the image data buffer.
    PyObject* getDataBuffer() const
    try
    {
        Exiv2::BasicIo& io = _image->io();
        unsigned long size = io.size();
        if (size > (unsigned long)LONG_MAX)
        {
            // The image is too large to represent in memory.
            return PyErr_NoMemory();
        }

        long ssize = (long) size;
        long readpos = 0;
        long nread;

        // Use the PyBytes_* API to create a data buffer that we can read
        // directly into.  This must be done before releasing the GIL.
        std::unique_ptr<PyObject, decltype(&Py_DecRef)> buffer_h
            (PyBytes_FromStringAndSize(NULL, size), &Py_DecRef);
        if (!buffer_h)
        {
            return PyErr_NoMemory();
        }

        {
            // Because the bytes object is brand new and we hold the only
            // reference to it, we are allowed to write into its data area.
            // https://docs.python.org/3/c-api/bytes.html#c.PyBytes_AsString
            void *data = PyBytes_AS_STRING(buffer_h.get());

            // Release the GIL to allow other python threads to run
            // while reading the image data.
            release_gil in_this_block;

            // Save and restore the seek position within the image, or
            // open and close the image file, as necessary.
            preserve_read_state of(io);

            // Copy from the file into the Python buffer.
            do
            {
                nread = io.read(((Exiv2::byte*)data) + readpos,
                                ssize - readpos);
                readpos += nread;
            }
            while (nread > 0 && readpos < ssize);

        } // GIL re-acquired and io reset to its previous state here

        // If we got the amount of data we expected, we're done.
        if (readpos == ssize)
        {
            return buffer_h.release();
        }

        // If there was less data than expected, truncate the buffer to
        // the size of the data actually read.  This calls into the Python
        // allocator, so it must happen after re-acquiring the GIL.
        // _PyBytes_Resize may change the raw buffer pointer, so we have
        // to take it back from buffer_h.
        PyObject* buffer = buffer_h.release();
        // If _PyBytes_Resize fails, it deallocates the original
        // buffer, sets a Python exception, and sets buffer to NULL.
        _PyBytes_Resize(&buffer, (unsigned long)readpos);
        return buffer;
    }
    catch (...)
    {
        exception_to_pyerr();
        return 0;
    }

    // Comments
    std::string getComment()
    {
        check_metadata_read();
        return _image->comment();
    }

    void setComment(const std::string& comment)
    {
        check_metadata_read();
        _image->setComment(comment);
    }

    void clearComment()
    {
        check_metadata_read();
        _image->clearComment();
    }

    Exiv2::ByteOrder getByteOrder() const
    {
        check_metadata_read();
        return _image->byteOrder();
    }

    char const* getIptcCharset() const
    {
        check_metadata_read();
        char const* charset = _image->iptcData().detectCharset();
        if (charset != 0)
        {
            return charset;
        }
        return "";
    }

    char const* getExifThumbnailMimeType()
    {
        return _getExifThumbnail()->mimeType();
    }

    char const* getExifThumbnailExtension()
    {
        return _getExifThumbnail()->extension();
    }

    void writeExifThumbnailToFile(std::string const& path)
    {
        _getExifThumbnail()->writeFile(path);
    }

    void eraseExifThumbnail()
    {
        _getExifThumbnail()->erase();
    }

    void setExifThumbnailFromFile(std::string const& path)
    {
        _getExifThumbnail()->setJpegThumbnail(path);
    }

    void getExifTag(std::string const& key, ExifTag& tag)
    {
        check_metadata_read();

        Exiv2::ExifKey exifKey = Exiv2::ExifKey(key);
        Exiv2::ExifData* data = getExifData();
        if (data->findKey(exifKey) == data->end())
        {
            throw Exiv2::Error(Exiv2::kerInvalidKey, key);
        }

        tag.init(key, &(*data)[key], data, _image->byteOrder());
    }

    void deleteExifTag(std::string const& key)
    {
        check_metadata_read();

        Exiv2::ExifKey exifKey = Exiv2::ExifKey(key);
        Exiv2::ExifData* data = getExifData();
        Exiv2::ExifMetadata::iterator datum = data->findKey(exifKey);
        if (datum == data->end())
        {
            throw Exiv2::Error(Exiv2::kerInvalidKey, key);
        }
        data->erase(datum);
    }

    void getIptcTag(std::string const& key, IptcTag& tag)
    {
        check_metadata_read();

        Exiv2::IptcKey iptcKey = Exiv2::IptcKey(key);
        Exiv2::IptcData* data = getIptcData();
        if (data->findKey(iptcKey) == data->end())
        {
            throw Exiv2::Error(Exiv2::kerInvalidKey, key);
        }
        tag.init(key, data);
    }

    void deleteIptcTag(std::string const& key)
    {
        check_metadata_read();

        Exiv2::IptcKey iptcKey = Exiv2::IptcKey(key);
        Exiv2::IptcData* data = getIptcData();
        bool erased = false;
        for (auto p = data->begin(); p != data->end(); )
        {
            if (p->key() == key)
            {
                erased = true;
                p = data->erase(p);
            }
            else
            {
                ++p;
            }
        }
        if (!erased)
        {
            throw Exiv2::Error(Exiv2::kerInvalidKey, key);
        }
    }

    void getXmpTag(std::string const& key, XmpTag& tag)
    {
        check_metadata_read();

        Exiv2::XmpKey xmpKey = Exiv2::XmpKey(key);
        Exiv2::XmpData* data = getXmpData();
        if (data->findKey(xmpKey) == data->end())
        {
            throw Exiv2::Error(Exiv2::kerInvalidKey, key);
        }
        tag.init(key, &(*data)[key]);
    }

    void deleteXmpTag(std::string const& key)
    {
        check_metadata_read();

        Exiv2::XmpKey xmpKey = Exiv2::XmpKey(key);
        Exiv2::XmpData* data = getXmpData();
        Exiv2::XmpMetadata::iterator i = data->findKey(xmpKey);
        if (i != data->end())
        {
            data->erase(i);
        }
        else
        {
            throw Exiv2::Error(Exiv2::kerInvalidKey, key);
        }
    }

    // Manipulate the JPEG/TIFF thumbnail embedded in the EXIF data.
    PyObject* getExifThumbnailData()
    try
    {
        // Unfortunately, this copies the data twice.  There doesn't
        // seem to be any way to get a pointer to the image data from
        // an ExifThumb object without copying it, and there doesn't
        // seem to be any way to create a PyBytes object without
        // copying into it, either.
        Exiv2::DataBuf buffer = _getExifThumbnail()->copy();
        return PyBytes_FromStringAndSize(
            (const char *)buffer.pData_, buffer.size_);
    }
    catch (...)
    {
        exception_to_pyerr();
        return 0;
    }

    void setExifThumbnailFromData(const unsigned char *data, size_t len)
    {
        if (len > (size_t)LONG_MAX)
        {
            // Thumbnail is too large.
            throw std::bad_alloc();
        }
        _getExifThumbnail()->setJpegThumbnail(data, len);
    }

    // Cython does not support local variables with C++ class types
    // that have no default or copy constructor, nor does it support
    // local variables with reference type, nor does it support
    // `cdef char placement[sizeof(type)]` ... so we have to
    // heap-allocate the dang thing.
    PreviewManager* getPreviewManager()
    {
        return new PreviewManager(*_image);
    }

    // Accessors used by {Exif,Iptc,Xmp}Tag.
    Exiv2::ExifData* getExifData() const { return &_image->exifData(); }
    Exiv2::IptcData* getIptcData() const { return &_image->iptcData(); }
    Exiv2::XmpData* getXmpData() const { return &_image->xmpData(); }

private:
    void check_metadata_read() const
    {
        if (!_dataRead)
        {
            throw Exiv2::Error(Exiv2::kerErrorMessage, "metadata not read");
        }
    }

    Exiv2::ExifThumb* _getExifThumbnail()
    {
        check_metadata_read();
        if (!_exifThumbnail)
        {
            _exifThumbnail.reset(new Exiv2::ExifThumb(_image->exifData()));
        }
        return _exifThumbnail.get();
    }

    std::string _filename;
    Exiv2::byte* _data;
    long _size;
    std::unique_ptr<Exiv2::Image> _image;
    std::unique_ptr<Exiv2::ExifThumb> _exifThumbnail;

    // true if the image's internal metadata has already been read,
    // false otherwise
    bool _dataRead;

    Image(Image const& image) = delete;
    Image& operator=(Image const&) = delete;
};

// These methods have to be defined at a point where the full
// declarations of both Image and XxxTag are visible.
inline void ExifTag::setParentImage(Image& image)
{
    Exiv2::ExifData* data = image.getExifData();
    if (data == _data)
    {
        // The parent image is already the one passed as a
        // parameter.  This happens when replacing a tag by
        // itself. In this case, don’t do anything (see
        // https://bugs.launchpad.net/pyexiv2/+bug/622739).
        return;
    }

    // Copy the current value of this tag into the new parent
    // image's ExifData, and update our _datum pointer to refer
    // to that.
    Exiv2::Exifdatum* oldDatum = _datum;
    _datum = &(*data)[_key->key()];
    _datum->setValue(oldDatum->getValue().get());

    // Only deallocate oldDatum if we didn't have a parent image
    // before this call.
    if (_data == 0)
    {
        delete oldDatum;
    }

    _data = data;
    _byteorder = image.getByteOrder();
}

inline void IptcTag::setParentImage(Image& image)
{
    Exiv2::IptcData* data = image.getIptcData();
    if (data == _data)
    {
        // The parent image is already the one passed as a
        // parameter.  This happens when replacing a tag by
        // itself. In this case, don’t do anything (see
        // https://bugs.launchpad.net/pyexiv2/+bug/622739).
        return;
    }

    // Replace any values for this key, in the new dataset,
    // with the values from the old dataset.
    // Since we are copying from oldData to data, we don't have
    // to worry about whether there's more than one entry for a
    // non-repeatable key.
    Exiv2::IptcData* oldData = _data;
    _data = data;
    clearRawValues();
    for (Exiv2::IptcMetadata::iterator i = oldData->begin();
         i != oldData->end(); ++i)
    {
        if (i->record() == _record && i->tag() == _tag)
        {
            _data->add(*i);
        }
    }

    // Deallocate oldData if and only if we allocated it.
    if (!_from_data)
    {
        delete oldData;
    }
    _from_data = true;
}

inline void XmpTag::setParentImage(Image& image)
{
    Exiv2::Xmpdatum* datum = &(*image.getXmpData())[_key->key()];
    if (datum == _datum)
    {
        // The parent image is already the one passed as a
        // parameter.  This happens when replacing a tag by
        // itself. In this case, don’t do anything (see
        // https://bugs.launchpad.net/pyexiv2/+bug/622739).
        return;
    }
    Exiv2::Value::AutoPtr value = _datum->getValue();
    if (!_from_datum)
    {
        delete _datum;
    }
    _from_datum = true;
    _datum = &(*image.getXmpData())[_key->key()];
    _datum->setValue(value.get());
}

} // anonymous namespace

#endif // _libexiv2_if.hpp

// Local Variables:
// c-basic-offset: 4
// c-file-style: "gnu"
// c-file-offsets: ((innamespace . 0) (substatement-open . 0))
// End:
