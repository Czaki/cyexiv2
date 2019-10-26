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

"""Install system-wide dependencies for building cyexiv2 in an Azure Pipelines
   task agent."""

import os
import shlex
import signal
import subprocess
import sys


def format_failed_process(err):
    cmd = ' '.join(shlex.quote(word) for word in err.cmd)
    if err.returncode == 0:
        status = "exited successfully?!"
    elif err.returncode > 0:
        status = "exited with code {}".format(err.returncode)
    else:
        try:
            status = "killed by {}".format(signal.Signals(-err.returncode)
                                            .name)
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


def assert_in_srcdir():
    if os.path.isfile("setup.py") and os.path.isfile(os.path.join(
            "src", "pyexiv2", "__init__.py")):
        return
    raise RuntimeError("Cannot find pyexiv2 source code")


def install_deps_ubuntu():
    # Tell apt-get not to try to prompt for interactive configuration.
    os.environ["DEBIAN_FRONTEND"] = "noninteractive"

    R(["sudo", "apt-get", "update"])
    R(["sudo", "apt-get", "install", "-y",
       "cmake", "zlib1g-dev", "libexpat1-dev"])

    R([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    R(["pip", "install", "--upgrade",
       "setuptools", "wheel", "pytest", "pytest-azurepipelines"])

    # per advice at https://pypi.org/project/Cython/ : for a one-off CI build,
    # compiling cython's accelerator modules from source will be slower
    # overall than falling back to the pure-python implementation
    R(["pip", "install", "Cython", "--install-option=--no-cython-compile"])


def main():
    try:
        assert_in_srcdir()
        install_deps_ubuntu()
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
