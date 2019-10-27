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
# Maintainer: Zack Weinberg <zackw@panix.com>
#
# ******************************************************************************

"""Build script for libexiv2 in the Azure Pipelines CI environment."""


import hashlib
import os
import shlex
import signal
import ssl
import subprocess
import sys
import tempfile
from urllib.request import urlopen

EXIV2_SRC_BASE   = 'exiv2-0.27.2-Source.tar.gz'
EXIV2_SRC_DIR    = 'exiv2-0.27.2-Source'
EXIV2_SRC_URL    = 'https://www.exiv2.org/builds/exiv2-0.27.2-Source.tar.gz'
EXIV2_SRC_SHA256 = \
    '2652f56b912711327baff6dc0c90960818211cf7ab79bb5e1eb59320b78d153f'


def format_failed_process(err):
    cmd = ' '.join(shlex.quote(word) for word in err.cmd)
    if err.returncode == 0:
        status = "exited successfully?!"
    elif err.returncode > 0:
        status = "exited with code {}".format(err.returncode)
    else:
        try:
            status = "killed by {}".format(
                signal.Signals(-err.returncode).name)
        except (ValueError, AttributeError):
            status = "killed by signal {}".format(-err.returncode)

    return "Command " + cmd + ": " + status


def R(cmd, **kwargs):
    """Like subprocess.run, but logs the command it's about to run.
       The very short name is for readability below."""

    sys.stdout.write("##[command]" + " ".join(shlex.quote(word)
                                              for word in cmd) + "\n")
    sys.stdout.flush()

    # subprocess.run() was added in Python 3.5, we still support 3.4
    return subprocess.check_call(cmd, **kwargs)


def download_and_check_hash(url, sha256, dest):
    sys.stdout.write("##[command]Downloading {}...\n".format(url))
    sys.stdout.flush()
    sslcx = ssl.create_default_context()
    h = hashlib.sha256()
    with urlopen(url, context=sslcx) as resp:
        headers = resp.info()
        if "content-length" in headers:
            size = int(headers["content-length"])
            progress_chunk = size / 20
        else:
            size = -1
            progress_chunk = 1024 * 1024

        nread = 0
        last_progress = 0

        while True:
            block = resp.read(8192)
            if block:
                h.update(block)
                dest.write(block)
                nread += len(block)

            if not block or nread - last_progress > progress_chunk:
                last_progress = nread
                if size == -1:
                    sys.stdout.write("##[info]{} bytes read\n"
                                     .format(nread))
                else:
                    sys.stdout.write("##[info]{}/{} bytes read\n"
                                     .format(nread, size))

            if not block:
                break

        if size >= 0 and nread != size:
            raise RuntimeError("Expected {} bytes, got {}"
                               .format(size, nread))

    digest = h.hexdigest()
    if digest != sha256:
        sys.stdout.write(
            "##[error]Checksum mismatch:\n"
            "##[error] expected: {}\n"
            "##[error]      got: {}\n"
            .format(sha256, digest))
        raise RuntimeError("Checksum mismatch for downloaded file")


def download_and_unpack_libexiv2():
    with open(EXIV2_SRC_BASE, "wb") as fp:
        download_and_check_hash(EXIV2_SRC_URL, EXIV2_SRC_SHA256, fp)

    R(["tar", "axf", EXIV2_SRC_BASE])
    sys.stdout.write("##[command]cd {}\n".format(EXIV2_SRC_DIR))
    sys.stdout.flush()
    os.chdir(EXIV2_SRC_DIR)


def build_libexiv2_ubuntu():
    with tempfile.TemporaryDirectory() as scratch:
        os.chdir(scratch)
        download_and_unpack_libexiv2()
        sys.stdout.write("##[command]mkdir build && cd build\n")
        sys.stdout.flush()
        os.mkdir("build")
        os.chdir("build")
        R(["cmake", "..", "-DCMAKE_BUILD_TYPE=Release"])
        R(["cmake", "--build", "."])
        R(["make", "tests"])
        R(["sudo", "make", "install"])


def main():
    try:
        build_libexiv2_ubuntu()
        sys.exit(0)

    except subprocess.CalledProcessError as e:
        sys.stdout.write("##vso[task.logissue type=error]{}\n".format(
            format_failed_process(e)))
        sys.exit(1)

    except Exception as e:
        sys.stdout.write("##vso[task.logissue type=error]{}\n".format(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
