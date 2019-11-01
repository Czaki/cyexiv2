#! /usr/bin/env python3
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

import os
import platform
import sys
from setuptools import setup, find_packages, Extension
from Cython.Build import cythonize

TOPSRCDIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(TOPSRCDIR, "src"))

from setup_hacks import (
    install_patched_make_tarball,
    restore_sdist_d_and_u,
)  # noqa: E402

install_patched_make_tarball()
restore_sdist_d_and_u()


def read_long_description():
    with open(os.path.join(TOPSRCDIR, "DESCRIPTION.rst"),
              encoding="utf-8") as f:
        return f.read()


def extra_compile_args():
    sysname = platform.system()
    if sysname == "Linux":
        rv = ["-std=c++11"]
    elif sysname == "Darwin":
        rv = ["-std=c++11", "-stdlib=libc++", "-mmacosx-version-min=10.9"]
    else:
        raise NotImplementedError
    rv.append('-fdebug-prefix-map='+TOPSRCDIR+'=.')
    return rv


def extra_link_args():
    sysname = platform.system()
    if sysname == "Linux":
        rv = []
    elif sysname == "Darwin":
        rv = ["-std=c++11", "-stdlib=libc++", "-mmacosx-version-min=10.9"]
    else:
        raise NotImplementedError
    return rv


setup(
    name='cyexiv2',
    version='0.8.0.dev0',
    description='A Python3 binding to the library exiv2',
    long_description=read_long_description(),
    long_description_content_type='text/x-rst',
    url='https://bitbucket.org/elwoz/cyexiv2',
    author='Vincent Vande Vyvre',
    author_email='vincent.vandevyvre@oqapy.eu',
    license='GPL-3',

    python_requires='>= 3.3',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    ext_modules=cythonize([
        Extension(
            'pyexiv2._libexiv2',
            ['src/pyexiv2/_libexiv2.pyx'],
            depends=['src/pyexiv2/_libexiv2_if.pxd',
                     'src/pyexiv2/_libexiv2_if.hpp'],
            libraries=['exiv2'],
            extra_compile_args=extra_compile_args(),
            extra_link_args=extra_link_args()
        )
    ]),

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: C++',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    keywords='exiv2 pyexiv2 EXIF IPTC XMP image metadata',
)
