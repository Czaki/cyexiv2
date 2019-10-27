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

"""Test script for cyexiv2 in the Azure Pipelines CI environment."""

import os
import sys
import shlex


def augment_path(var, dir):
    if var in os.environ:
        os.environ[var] = dir + os.pathsep + os.environ[var]
    else:
        os.environ[var] = dir
    sys.stdout.write("##[command]export {}={}\n".format(
        var, shlex.quote(os.environ[var])))


def main():
    augment_path("PYTHONPATH", os.path.join(os.getcwd(), "src"))
    augment_path("LD_LIBRARY_PATH", "/usr/local/lib")

    pytest_cmd = [
        "pytest", "--doctest-modules", "--junitxml=test-results.xml",
        "--cov=pyexiv2", "--cov-report=xml", "--cov-report=html"
    ]

    sys.stdout.write("##[command]exec "
                     + " ".join(shlex.quote(word) for word in pytest_cmd)
                     + "\n")
    sys.stdout.flush()
    os.execvp(pytest_cmd[0], pytest_cmd)


if __name__ == "__main__":
    main()

