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

"""Build script for cyexiv2 in the Azure Pipelines CI environment."""

import argparse
import contextlib
import hashlib
import os
import platform
import shlex
import signal
import ssl
import stat
import subprocess
import sys
import tempfile
from urllib.request import urlopen


EXIV2_SRC_BASE   = 'exiv2-0.27.2-Source.tar.gz'
EXIV2_SRC_DIR    = 'exiv2-0.27.2-Source'
EXIV2_SRC_URL    = 'https://www.exiv2.org/builds/exiv2-0.27.2-Source.tar.gz'
EXIV2_SRC_SHA256 = \
    '2652f56b912711327baff6dc0c90960818211cf7ab79bb5e1eb59320b78d153f'

CAN_FCHDIR = os.supports_fd


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


def log_command(*cmd):
    sys.stdout.write("##[command]"
                     + " ".join(shlex.quote(word) for word in cmd)
                     + "\n")
    sys.stdout.flush()


def log_error(msg):
    for line in msg.splitlines():
        sys.stdout.write("##[error]" + msg.strip() + "\n")
    sys.stdout.flush()


def log_exception(exc):
    import traceback
    msg = "".join(traceback.format_exception_only(type(exc), exc))
    log_error(msg)


def log_failed_process(err):
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

    log_error("Command {}: {}".format(cmd, status))


def run(cmd, **kwargs):
    """Like subprocess.run, but logs the command it's about to run."""

    log_command(*cmd)
    # subprocess.run() was added in Python 3.5, we still support 3.4
    return subprocess.check_call(cmd, **kwargs)


def chdir(dest):
    """Like os.chdir, but logs the action."""

    log_command("cd", dest)
    os.chdir(dest)


@contextlib.contextmanager
def working_directory(dest):
    """Change into DEST for the duration of a with-context, then return to
       the previous working directory.  Uses fchdir(2) for the return
       if possible.
    """

    global CAN_FCHDIR

    prev_wd_path = os.getcwd()
    prev_wd_fd = -1
    if CAN_FCHDIR:
        try:
            prev_wd_fd = os.open(".", os.O_PATH|os.O_DIRECTORY)
        except (OSError, AttributeError):
            CAN_FCHDIR = False

    log_command("cd", dest)
    os.chdir(dest)
    yield
    log_command("cd", prev_wd_path)
    if prev_wd_fd == -1:
        os.chdir(prev_wd_path)
    else:
        try:
            os.chdir(prev_wd_fd)
        except OSError as e:
            sys.stdout.write("##[warning]fchdir: {}\n".format(e))
            sys.stdout.flush()
            os.chdir(prev_wd_path)
            CAN_FCHDIR = False

        os.close(prev_wd_fd)


def makedirs(dest):
    """Like os.makedirs, but logs the action.  Always uses exist_ok=True."""

    log_command("mkdir", "-p", dest)
    os.makedirs(dest, exist_ok=True)


def augment_path(var, dir):
    """Add DIR to the front of the PATH-like environment variable VAR."""
    if var in os.environ:
        os.environ[var] = dir + os.pathsep + os.environ[var]
    else:
        os.environ[var] = dir
    log_command("export", "{}={}".format(var, os.environ[var]))


def assert_in_srcdir():
    if os.path.isfile("setup.py") and os.path.isfile(os.path.join(
            "src", "pyexiv2", "__init__.py")):
        return
    raise RuntimeError("Cannot find pyexiv2 source code")


def download_and_check_hash(url, sha256, dest):
    log_command("urlretrieve", url)
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
                    sys.stdout.write("{} bytes read\n".format(nread))
                else:
                    sys.stdout.write("{}/{} bytes read\n".format(nread, size))

            if not block:
                break

        if size >= 0 and nread != size:
            raise RuntimeError("Expected {} bytes, got {}"
                               .format(size, nread))

    digest = h.hexdigest()
    if digest != sha256:
        log_error(
            "Checksum mismatch:\n"
            " expected: {}\n"
            "      got: {}\n"
            .format(sha256, digest))
        raise RuntimeError("Checksum mismatch for downloaded file")


def download_and_unpack_libexiv2():
    with open(EXIV2_SRC_BASE, "wb") as fp:
        download_and_check_hash(EXIV2_SRC_URL, EXIV2_SRC_SHA256, fp)

    run(["tar", "axf", EXIV2_SRC_BASE])


def report_env(args):
    log_platform()
    log_cwd()
    log_environ()


def install_deps_ubuntu(args):
    # Tell apt-get not to try to prompt for interactive configuration.
    os.environ["DEBIAN_FRONTEND"] = "noninteractive"

    run(["sudo", "apt-get", "update"])
    run(["sudo", "apt-get", "install", "-y",
         "cmake", "zlib1g-dev", "libexpat1-dev", "libxml2-utils"])

    run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    run(["pip", "install", "--upgrade",
         "setuptools", "wheel",
         "pytest", "pytest-azurepipelines", "pytest-cov",
         "flake8"])

    # per advice at https://pypi.org/project/Cython/ : for a one-off CI build,
    # compiling cython's accelerator modules from source will be slower
    # overall than falling back to the pure-python implementation
    run(["pip", "install", "Cython", "--install-option=--no-cython-compile"])


def build_libexiv2_ubuntu(args):
    with tempfile.TemporaryDirectory() as td, working_directory(td):

        download_and_unpack_libexiv2()
        builddir = os.path.join(EXIV2_SRC_DIR, "build")
        makedirs(builddir)
        chdir(builddir)
        run(["cmake", "..", "-DCMAKE_BUILD_TYPE=Release"])
        run(["cmake", "--build", "."])
        run(["make", "tests"])
        run(["sudo", "make", "install"])


def build_cyexiv2_inplace(args):
    assert_in_srcdir()
    run([sys.executable, "setup.py", "build_ext", "--inplace"])


def test_cyexiv2_inplace(args):
    assert_in_srcdir()

    augment_path("PYTHONPATH", os.path.join(os.getcwd(), "src"))
    augment_path("LD_LIBRARY_PATH", "/usr/local/lib")
    run(["pytest", "--doctest-modules", "--junitxml=test-results.xml",
         "--cov=pyexiv2", "--cov-report=xml", "--cov-report=html"])


def main():
    ACTIONS = {
        "report-env": report_env,
        "install-deps-ubuntu": install_deps_ubuntu,
        "build-libexiv2-ubuntu": build_libexiv2_ubuntu,
        "build-cyexiv2-inplace": build_cyexiv2_inplace,
        "test-cyexiv2-inplace": test_cyexiv2_inplace,
    }

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=ACTIONS.keys())
    args = ap.parse_args()

    try:
        ACTIONS[args.action](args)
        sys.exit(0)

    except subprocess.CalledProcessError as e:
        log_failed_process(e)
        sys.exit(1)

    except Exception as e:
        log_exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
