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

"""Build script for py(3)exiv2 in the Azure Pipelines CI environment."""


import glob
import os
import platform
import shlex
import subprocess
import sys


def log_platform():
    plat = platform.platform(aliased=True)
    cc = platform.python_compiler()
    pyimpl = platform.python_implementation()
    pyvers = platform.python_version()

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
    sys.stdout.write("Environment variable dump:\n")
    for k, v in sorted(os.environ.items()):
        sys.stdout.write("  {}={}\n".format(shlex.quote(k), shlex.quote(v)))
    sys.stdout.write("\n")
    sys.stdout.write("Working directory: {}\n".format(os.getcwd()))
    sys.stdout.flush()


def augment_pythonpath(dir):
    env = os.environ.copy()
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = dir + os.pathsep + env["PYTHONPATH"]
    else:
        env["PYTHONPATH"] = dir
    return env


def assert_in_srcdir():
    if os.path.isfile("setup.py") and os.path.isfile(os.path.join(
            "src", "pyexiv2", "__init__.py")):
        return

    sys.stdout.write("ERROR: Cannot find pyexiv2 source code\n\n"
                     "Working directory contents:\n")
    for f in sorted(os.listdir(".")):
        sys.stdout.write("  {}\n".format(shlex.quote(f)))

    raise RuntimeError("Cannot find pyexiv2 source code")


def build_generic():
    # subprocess.run() was added in Python 3.5, we still support 3.4
    R = subprocess.check_call

    python = sys.executable
    pythonpath_for_test = augment_pythonpath(os.path.join(os.getcwd(), "src"))

    test_cmd = ["pytest"]
    test_cmd.extend(sorted(
        p for p in glob.glob(os.path.join("test", "*.py"))
        if not p.endswith("__init__.py")))

    sys.stdout.write("--- Installing dependencies ---\n")
    sys.stdout.flush()
    R(["sudo", "apt-get", "update"])
    R(["sudo", "apt-get", "install", "-y", "cython3", "libexiv2-dev"])
    R([python, "-m", "pip", "install", "--upgrade", "pip"])
    R(["pip", "install", "--upgrade",
       "setuptools", "wheel", "pytest", "pytest-azurepipelines"])

    sys.stdout.write("--- Building extension module ---\n")
    sys.stdout.flush()
    R([python, "setup.py", "build_ext", "--inplace"])

    sys.stdout.write("--- Running tests ---\n")
    sys.stdout.flush()
    R(test_cmd, env=pythonpath_for_test)


def main():
    sys.stdout.write("--- Build start ---\n")
    log_platform()
    log_environ()
    try:
        assert_in_srcdir()
        build_generic()
        sys.stdout.write("--- Build complete ---\n")
        sys.exit(0)
    except BaseException as e:  # yes, really
        sys.stdout.write("--- Build failed: {} ---\n".format(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
