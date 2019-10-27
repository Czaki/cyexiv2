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

"""Helper script to report on the CI environment being used for a build."""


import os
import platform
import shlex
import stat
import sys


# A subset of the behavior of GNU ls -F --color=always.
def classify_direntry(name):
    st = os.lstat(name)
    mode = st.st_mode
    perms = stat.S_IMODE(mode)

    if stat.S_ISREG(mode):
        if perms & stat.S_ISUID:
            colors = "37;41"
        elif perms & stat.S_ISGID:
            colors = "30;43"
        elif perms & (stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH):
            colors = "01;32"
        else:
            colors = ""
        if perms & (stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH):
            suffix = "*"
        else:
            suffix = ""

    elif stat.S_ISDIR(mode):
        colors = "01;34"
        suffix = "/"

    elif stat.S_ISLNK(mode):
        dest = os.readlink(name)
        try:
            dest = classify_direntry(dest)
            colors = "01;36"
            suffix = " => " + dest
        except OSError:  # broken symlink
            colors = "40;31;01"
            suffix = " => " + shlex.quote(dest)

    else:
        colors = "40;33;01"
        suffix = " % "
        if stat.S_ISBLK(mode):
            suffix += "blockdev"
        elif stat.S_ISCHR(mode):
            suffix += "chardev"
        elif stat.S_ISDOOR(mode):
            suffix += "door"
        elif stat.S_ISFIFO(mode):
            suffix += "fifo"
        elif stat.S_ISPORT(mode):
            suffix += "evport"
        elif stat.S_ISSOCK(mode):
            suffix += "sock"
        elif stat.S_ISWHT(mode):
            suffix += "whiteout"
        else:
            suffix += "unknown"

    name = shlex.quote(name)
    if colors:
        return "\033[" + colors + "m" + name + "\033[0m" + suffix
    else:
        return name + suffix


def log_cwd():
    sys.stdout.write("##[section]Working directory:\n")
    sys.stdout.write("  {}/\n".format(shlex.quote(os.getcwd())))
    for f in sorted(os.listdir(".")):
        sys.stdout.write("    {}\n".format(classify_direntry(f)))
    sys.stdout.write("\n")
    sys.stdout.flush()


def log_platform():
    plat = platform.platform(aliased=True)
    cc = platform.python_compiler()
    pyimpl = platform.python_implementation()
    pyvers = platform.python_version()

    sys.stdout.write("##[section]Python runtime environment:\n")

    sys.stdout.write("Interpreter: {} {}\n".format(pyimpl, pyvers))
    if cc:
        sys.stdout.write("Compiled by: {}\n".format(cc))
    sys.stdout.write("Running on:  {}\n".format(plat))

    # On Linux, we want to print the C library version number in addition
    # to the distribution identifiers.
    if platform.system() == "Linux":
        lver = platform.libc_ver()
        if lver[0]:
            sys.stdout.write("C library:   {} {}\n".format(*lver))

    sys.stdout.write("\n")
    sys.stdout.flush()


def log_environ():
    sys.stdout.write("##[section]Environment variables:\n")
    for k, v in sorted(os.environ.items()):
        sys.stdout.write("  {}={}\n".format(shlex.quote(k), shlex.quote(v)))
    sys.stdout.write("\n")
    sys.stdout.flush()


def main():
    log_platform()
    log_cwd()
    log_environ()


main()
