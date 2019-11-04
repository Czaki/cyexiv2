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
import glob
import hashlib
import io
import itertools
import locale
import os
import platform
import shlex
import shutil
import signal
import ssl
import stat
import subprocess
import sys
import tempfile
from xml.dom.minidom import parse as parse_xml
from xml.dom import Node as DOMNode, NotFoundErr as DOMNotFoundError
from urllib.request import urlopen


EXIV2_SRC_BASE   = 'exiv2-0.27.2-Source.tar.gz'
EXIV2_SRC_DIR    = 'exiv2-0.27.2-Source'
EXIV2_SRC_TS     = 1564381986  # 2019-07-29 02:33:06 +0000
EXIV2_SRC_URL    = 'https://www.exiv2.org/builds/exiv2-0.27.2-Source.tar.gz'
EXIV2_SRC_SHA256 = \
    '2652f56b912711327baff6dc0c90960818211cf7ab79bb5e1eb59320b78d153f'

# This list partially cribbed from Autoconf's shell environment
# normalization logic.
BAD_ENVIRONMENT_VARS = frozenset((
    "__PYVENV_LAUNCHER__",  # https://bugs.python.org/issue22490
    "BASH_ENV",
    "CDPATH",
    "CLICOLOR_FORCE",
    "ENV",
    "GREP_OPTIONS",
    "IFS",
    "LANG",
    "LANGUAGE",
    "LS_COLORS",
    "PS1",
    "PS2",
    "PS3",
    "PS4",
))

# This list was cribbed from Emacs' vc/*.el and is not remotely
# exhaustive, but covers everything that's likely to be used and a
# few more.  To avoid a number of Windows-related headaches, the
# names have all been lowercased and leading '.' and '_' have been
# removed.
VERSION_CONTROL_DIRS = frozenset((
    "bzr",
    "cvs",
    "darcs",
    "git",
    "hg",
    "mtn",
    "rcs",
    "sccs",
    "svn",
))


def is_vcs_dir(d):
    """True if D is a directory likely to contain a version control
       system's metadata."""

    if not d:
        return False
    if d[0] in ('_', '.'):
        d = d[1:]
    return d.lower() in VERSION_CONTROL_DIRS


def classify_direntry(path):
    """Annotate a directory entry with type information, akin to what
       GNU ls -F does."""
    st = os.lstat(path)
    mode = st.st_mode
    perms = stat.S_IMODE(mode)

    if stat.S_ISREG(mode):
        if perms & (stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH):
            suffix = "*"
        else:
            suffix = ""
        if perms & stat.S_ISUID:
            suffix += " !suid!"
        elif perms & stat.S_ISGID:
            suffix += " !sgid!"

    elif stat.S_ISDIR(mode):
        suffix = "/"

    elif stat.S_ISLNK(mode):
        dest = os.readlink(path)
        try:
            dest = classify_direntry(
                os.path.join(os.path.dirname(path), dest))
            suffix = " => " + dest
        except OSError:  # broken symlink
            suffix = " =/> " + shlex.quote(dest)

    else:
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

    return shlex.quote(path) + suffix


def get_parallel_jobs():
    """Intuit the available parallelism for build tasks."""

    def _get_parallel_jobs():
        try:
            return max(len(os.sched_getaffinity(0)), 1)
        except Exception:
            pass

        try:
            return os.cpu_count() or 1
        except Exception:
            pass

        try:
            from multiprocessing import cpu_count
            return cpu_count() or 1
        except Exception:
            pass

        return 1

    global _parallel_jobs
    try:
        return _parallel_jobs
    except NameError:
        _parallel_jobs = pj = _get_parallel_jobs()
        return pj


def log_file_contents(path):
    sys.stdout.write("##[section]Contents of {}:\n"
                     .format(shlex.quote(path)))
    with open(path, "rt") as f:
        sys.stdout.write(f.read())


def log_dir_contents(dir, label):
    sys.stdout.write("##[section]{}:\n".format(label))
    sys.stdout.write("  {}/\n".format(shlex.quote(dir)))
    for f in sorted(os.listdir(dir)):
        sys.stdout.write("    {}\n".format(
            classify_direntry(os.path.join(dir, f))))
    sys.stdout.write("\n")
    sys.stdout.flush()


def log_cwd():
    log_dir_contents(os.getcwd(), "Working directory")


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

    sys.stdout.write("Parallelism: {}\n".format(get_parallel_jobs()))
    sys.stdout.write("\n")
    sys.stdout.flush()


def log_environ():
    sys.stdout.write("##[section]Environment variables:\n")
    for k, v in sorted(os.environ.items()):
        sys.stdout.write("  {}={}\n".format(shlex.quote(k), shlex.quote(v)))
    sys.stdout.write("\n")
    sys.stdout.flush()


def log_command(*cmd, suffix=""):
    sys.stdout.write("##[command]"
                     + " ".join(shlex.quote(word) for word in cmd)
                     + suffix
                     + "\n")
    sys.stdout.flush()


def log_warning(msg):
    for line in msg.splitlines():
        sys.stdout.write("##[warning]" + msg.rstrip() + "\n")
    sys.stdout.flush()


def log_error(msg):
    for line in msg.splitlines():
        sys.stdout.write("##[error]" + msg.rstrip() + "\n")
    sys.stdout.flush()


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


def run_get_output(cmd, **kwargs):
    """Like subprocess.check_output, but logs the command it's about to
       run.  The return value is a list of decoded, stripped lines.
    """
    log_command(*cmd, suffix=" |")
    output = subprocess.check_output(cmd).decode("utf-8")
    return [l.rstrip() for l in output.splitlines()]


def setenv(var, value):
    """Like os.environ[var] = value, but logs the action."""
    sys.stdout.write("##[command]export {}={}\n".format(
        shlex.quote(var), shlex.quote(value)))
    os.environ[var] = value


def unsetenv(var):
    """Like os.environ.pop(var, None), but logs the action."""
    if os.environ.pop(var, None) is not None:
        log_command("unset", var)


def remove(fname):
    """Like os.remove, but logs the action."""
    log_command("rm", fname)
    os.remove(fname)


def rename(src, dst):
    """Like os.rename, but logs the action."""
    log_command("mv", src, dst)
    os.rename(src, dst)


def copyfile(src, dst):
    """Like shutil.copyfile, but logs the action and does not follow
       symlinks."""
    log_command("cp", src, dst)
    shutil.copyfile(src, dst, follow_symlinks=False)


def rename_aside(dir, prefix, suffix):
    """Rename 'aside' every file in DIR whose name begins with PREFIX and
       ends with SUFFIX.  'Aside' means: if the name of a file is
       ${prefix}${middle}${suffix}, then it is renamed to
       ${prefix}${middle}-1${suffix}.  Renames are done in an
       appropriate order, so that no file gets clobbered.
    """
    needs_rename = []
    plen = len(prefix)
    slen = len(suffix)
    for name in os.listdir(dir):
        if name.startswith(prefix) and name.endswith(suffix):
            needs_rename.append(name[plen:-slen])

    needs_rename.sort(key=lambda s: (-len(s), s))
    for middle in needs_rename:
        src = os.path.join(dir, prefix + middle + suffix)
        dst = os.path.join(dir, prefix + middle + "-1" + suffix)
        rename(src, dst)


def recursive_reset_timestamps(topdir, timestamp):
    """Recursively reset the atime and mtime of everything within TOPDIR
       to TIMESTAMP, except that version control directories are
       skipped.  See above for the list of recognized version control
       directories.  TIMESTAMP is expected to be a whole number of
       seconds.
    """
    # Note: we'd like to use os.utime(..., follow_symlinks=False) but
    # that throws NotImplementedError on Windows.  This function is
    # currently only used on the contents of the exiv2 source tarball,
    # and as of 0.27.2, that tarball does not contain any symlinks, so
    # we can live with this for now.

    times = (timestamp, timestamp)
    for subdir, dirs, files in os.walk(topdir):
        vcs_dirs = [d for d in dirs if is_vcs_dir(d)]
        for d in vcs_dirs:
            dirs.remove(d)

        try:
            os.utime(subdir, times=times)
        except OSError as e:
            log_warning("resetting timestamp on {}: {}"
                        .format(subdir, e))

        for f in files:
            fpath = os.path.join(subdir, f)
            try:
                os.utime(fpath, times=times)
            except OSError as e:
                log_warning("resetting timestamp on {}: {}"
                            .format(subdir, e))


def chdir(dest):
    """Like os.chdir, but logs the action."""

    log_command("cd", dest)
    os.chdir(dest)


def makedirs(dest):
    """Like os.makedirs, but logs the action.  Always uses exist_ok=True."""

    log_command("mkdir", "-p", dest)
    os.makedirs(dest, exist_ok=True)


@contextlib.contextmanager
def working_directory(dest):
    """Change into DEST for the duration of a with-context, then return to
       the previous working directory.
    """

    prev_wd = os.getcwd()
    chdir(dest)
    try:
        yield
    finally:
        chdir(prev_wd)


def augment_path(var, dir):
    """Add DIR to the front of the PATH-like environment variable VAR,
       or move it to the front if it's already present."""

    if var not in os.environ:
        value = dir
    else:
        value = os.environ[var].split(os.pathsep)
        for i in range(len(value)):
            if value[i] == dir:
                if i > 0:
                    del value[i]
                    value.insert(0, dir)
                break
        else:
            value.insert(0, dir)
        value = os.pathsep.join(value)

    setenv(var, value)


def activate_venv(venv_dir):
    """Activate a virtualenv for all subprocesses of this script.
       Does not alter PS1, unlike ". ${venv_dir}/bin/activate".
       Exiting from an enclosing "with restore_environ()" block
       (see below) will deactivate the virtualenv.
    """
    venv_dir = os.path.abspath(venv_dir)
    old_venv_dir = os.environ.get("VIRTUAL_ENV")
    if venv_dir == old_venv_dir:
        return

    log_command("activate_venv", venv_dir)

    if os.path.isfile(os.path.join(venv_dir, "bin", "activate")):
        bin_dir = "bin"
    elif os.path.isfile(os.path.join(venv_dir, "Scripts", "activate")):
        bin_dir = "Scripts"
    else:
        raise RuntimeError("{!r} does not appear to be a virtualenv"
                           .format(venv_dir))

    path = os.environ["PATH"].split(os.pathsep)
    new_bin = os.path.join(venv_dir, bin_dir)
    if old_venv_dir is not None:
        old_bin = os.path.join(old_venv_dir, bin_dir)
    else:
        old_bin = None
    for i in range(len(path)):
        if path[i] == new_bin or path[i] == old_bin:
            del path[i]
    path.insert(0, new_bin)

    setenv("VIRTUAL_ENV", venv_dir)
    setenv("PATH", os.pathsep.join(path))
    unsetenv("PYTHONHOME")
    # https://bugs.python.org/issue22490
    unsetenv("__PYVENV_LAUNCHER__")


def ensure_venv(venv_dir):
    """As activate_venv, but, if venv_dir doesn't already exist, it is
       created and initialized.
    """
    venv_dir = os.path.abspath(venv_dir)
    if not os.path.isdir(venv_dir):
        run([sys.executable, "-m", "venv", venv_dir])
    activate_venv(venv_dir)


def sanitize_env():
    """Ensure a clean starting environment for builds."""

    # Clear all of the BAD_ENVIRONMENT_VARS and all LC_* variables.
    to_unset = []
    for k in os.environ.keys():
        if k in BAD_ENVIRONMENT_VARS or k.startswith("LC_"):
            to_unset.append(k)

    for k in to_unset:
        unsetenv(k)

    # Set LC_ALL=C.UTF-8 if supported, otherwise LC_ALL=C.
    setenv("LC_ALL", "C.UTF-8")
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error as e:
        log_warning("C.UTF-8 locale not available: {}".format(e))
        setenv("LC_ALL", "C")
        locale.setlocale(locale.LC_ALL, "")

    # Force use of UTF-8, line-buffered output on both stdout and
    # stderr.
    sys.stdout.flush()
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(),
                                  encoding="utf-8",
                                  errors="backslashreplace",
                                  newline=None,
                                  line_buffering=True)

    sys.stderr.flush()
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(),
                                  encoding="utf-8",
                                  errors="backslashreplace",
                                  newline=None,
                                  line_buffering=True)

    # For subprocesses.
    setenv("PYTHONIOENCODING", "utf-8:backslashreplace")

    # Set SOURCE_DATE_EPOCH if possible and not already set.
    if "SOURCE_DATE_EPOCH" not in os.environ:
        sourcedate = None
        try:
            sourcedate = run_get_output([
                "git", "show", "-s", "--format=%ct", "HEAD"
            ])[0]
        except subprocess.CalledProcessError:
            pass

        # FIXME: implement a way to do this from an sdist tarball.
        # We could take the maximum of all the source timestamps
        # but that seems both slow and fragile.

        if sourcedate is not None:
            setenv("SOURCE_DATE_EPOCH", sourcedate)
        else:
            log_warning("no VCS info available and SOURCE_DATE_EPOCH not set")

    # If AGENT_TEMPDIRECTORY is set, override TEMP, TMP, and TMPDIR to
    # the same value.  (Azure may set the latter three to unusable
    # locations!)
    agent_tmp = os.environ.get("AGENT_TEMPDIRECTORY")
    if agent_tmp is not None:
        setenv("TEMP", agent_tmp)
        setenv("TMP", agent_tmp)
        setenv("TMPDIR", agent_tmp)


@contextlib.contextmanager
def restore_environ():
    """Restore all environment variables to their previous values upon
       exiting the context."""
    save_env = os.environ.copy()
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(save_env)


def assert_in_srcdir():
    if os.path.isfile("setup.py") and os.path.isfile(os.path.join(
            "src", "pyexiv2", "__init__.py")):
        return
    raise RuntimeError("Cannot find pyexiv2 source code")


def normalize_cov_xml(xmlfile, dest=None):
    """Read XMLFILE, remove build-environment nondeterminism from the
       XML structure, and write it back out to DEST (or to XMLFILE if
       DEST is not specified)."""
    with parse_xml(xmlfile) as doc:
        root = doc.documentElement

        epoch = os.environ.get('SOURCE_DATE_EPOCH')
        cwd = os.getcwd()

        if epoch is not None:
            root.setAttribute('timestamp', epoch)
        else:
            try:
                root.removeAttribute('timestamp')
            except DOMNotFoundError:
                pass

        for source in doc.getElementsByTagName('source'):
            source.normalize()
            if (
                    source.firstChild is not None
                    and source.firstChild.nodeType == DOMNode.TEXT_NODE
                    and source.firstChild.data.strip() == cwd
            ):
                source.replaceChild(doc.createTextNode("."),
                                    source.firstChild)

        newxml = doc.documentElement.toprettyxml(indent=" ")

    if dest is None:
        dest = xmlfile
    if isinstance(dest, str):
        with open(dest, "wt", encoding="utf-8") as w:
            w.write(newxml)
    else:
        dest.write(newxml)


def strip_junitxml_time_attrs(xmlfile, dest=None):
    """Read XMLFILE, remove all time= attributes from <testsuite> and
       <testcase> elements, and write it back out to DEST (or to XMLFILE
       if DEST is not specified)."""
    with parse_xml(xmlfile) as doc:
        for el in itertools.chain(doc.getElementsByTagName("testsuite"),
                                  doc.getElementsByTagName("testcase")):
            for attr in ["time", "timestamp"]:
                try:
                    el.removeAttribute(attr)
                except DOMNotFoundError:
                    pass

        newxml = doc.documentElement.toprettyxml(indent=" ")

    if dest is None:
        dest = xmlfile
    if isinstance(dest, str):
        with open(dest, "rt", encoding="utf-8") as w:
            w.write(newxml)
    else:
        dest.write(newxml)


def compare_test_results(r1, r2):
    """Compare test result files R1 and R2 (both JUnitXML).  They should
       be identical, except that time= attributes on <testsuite> and
       <testcase> elements are ignored."""

    def ntf():
        return tempfile.NamedTemporaryFile(
            mode="w+t", encoding="utf-8", suffix=".xml")

    with ntf() as t1, ntf() as t2:
        strip_junitxml_time_attrs(r1, t1)
        strip_junitxml_time_attrs(r2, t2)
        run(["diff", "-u", t1.name, t2.name])


def download_and_check_hash(url, sha256, dest, cafile):
    log_command("urlretrieve", url)
    sslcx = ssl.create_default_context(cafile=cafile)
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


def download_and_unpack_libexiv2(*, cafile=None, patches=[]):
    with open(EXIV2_SRC_BASE, "wb") as fp:
        download_and_check_hash(EXIV2_SRC_URL, EXIV2_SRC_SHA256, fp, cafile)

    run(["tar", "zxf", EXIV2_SRC_BASE])
    for patch in patches:
        with open(os.path.join(os.path.dirname(__file__), patch), "rb") as fp:
            run(["patch", "-p1", "-N", "-r", "-", "-d", EXIV2_SRC_DIR],
                stdin=fp)
    recursive_reset_timestamps(EXIV2_SRC_DIR, EXIV2_SRC_TS)


def report_env(args):
    log_platform()
    log_cwd()
    log_environ()


def install_deps_pip(extra_packages=[]):

    # On Windows, trying to use the 'pip' binary to upgrade pip will
    # throw an "Access is denied" error, because it's trying to overwrite
    # a running executable.
    run(["python", "-m", "pip", "install", "--upgrade", "pip"])

    pip_install = ["pip", "install", "setuptools", "wheel"]
    pip_install.extend(extra_packages)
    run(pip_install)

    # Per advice at https://pypi.org/project/Cython/ : for a one-off
    # CI build, compiling cython's accelerator modules from source
    # will be slower overall than falling back to the pure-python
    # implementation.  This has to be a separate command because
    # none of the other packages will recognize the option.
    run(["pip", "install", "Cython",
         "--install-option=--no-cython-compile"])


def install_deps_ubuntu(args):
    run(["sudo", "apt-get", "update"])
    run(["sudo", "DEBIAN_FRONTEND=noninteractive", "apt-get", "install", "-y",
         "cmake", "zlib1g-dev", "libexpat1-dev", "libxml2-utils"])

    ensure_venv("build/venv")
    install_deps_pip(extra_packages=["pytest", "pytest-cov"])


def install_deps_centos(args):
    run(["yum", "install", "-y",
         "cmake3", "zlib-devel", "expat-devel", "libxml2"])

    # cibuildwheel installs auditwheel, but if we don't tell pip to
    # install auditwheel in the same invocation that installs wheel,
    # it might install an incompatible version of wheel.
    install_deps_pip(extra_packages=["auditwheel"])


def install_deps_macos():
    # don't waste time on cleanup
    unsetenv("HOMEBREW_INSTALL_CLEANUP")
    setenv("HOMEBREW_NO_INSTALL_CLEANUP", "yes")

    # md5sum is required by libexiv2 tests and is not installed by default
    # cmake, zlib, expat, and xmllint *are* all installed by default
    run(["brew", "update"])
    run(["brew", "--version"])
    run(["brew", "install", "md5sha1sum"])

    # need updated certificate bundle or downloading exiv2 will fail
    install_deps_pip(extra_packages=["certifi"])


def install_deps_windows():
    install_deps_pip(extra_packages=["conan"])
    run(["conan", "--version"])


def libexiv2_is_already_available():
    from distutils.ccompiler import new_compiler
    from distutils.sysconfig import customize_compiler

    ccdata = new_compiler()
    customize_compiler(ccdata)
    if ccdata.compiler_type == 'msvc':
        ccdata.initialize()
        CXX = ccdata.cc
        # this was added in MSVC2017, but that's what azure-pipelines.yml
        # asks for, so it should be fine
        # (we need *at least* C++11)
        USE_CXX11 = '/std:c++14'
    else:
        CXX = ccdata.compiler_cxx[0]
        # this is a guess
        USE_CXX11 = "-std=c++11"

    with open("is_libexiv2_available.cpp", "w+t") as f:
        f.write("#include <exiv2/exiv2.hpp>\n"
                "#if EXIV2_MAJOR_VERSION == 0"
                " && EXIV2_MINOR_VERSION < 27\n"
                "#error too old\n"
                "#endif\n"
                "int main(){}\n")
    try:
        run([CXX, USE_CXX11, "is_libexiv2_available.cpp"])
        return True

    except subprocess.CalledProcessError:
        # Either we need to build libexiv2, or the C++ compiler is broken.
        # If the C++ compiler is broken, the next step will bomb out.
        return False


def build_libexiv2_linux(args, sudo_install):
    with tempfile.TemporaryDirectory() as td, \
         working_directory(td), \
         restore_environ():  # noqa: E126 - bug in flake8, indentation is fine

        if libexiv2_is_already_available():
            return

        # CentOS's RPMs for cmake 3.x install /usr/bin/cmake3;
        # /usr/bin/cmake remains version 2.x.  exiv2 requires 3.x.
        try:
            run(["cmake3", "--version"])
            cmake = "cmake3"
        except (subprocess.CalledProcessError, FileNotFoundError):
            run(["cmake", "--version"])
            cmake = "cmake"

        download_and_unpack_libexiv2(patches=[
            "testsuite-with-suppress-warnings.patch",
        ])

        builddir = os.path.join(EXIV2_SRC_DIR, "build")
        makedirs(builddir)
        chdir(builddir)

        setenv("CFLAGS", "-DSUPPRESS_WARNINGS")
        setenv("CXXFLAGS", "-DSUPPRESS_WARNINGS -Wno-deprecated-declarations")
        run([cmake, "..", "-DCMAKE_BUILD_TYPE=Release"])
        run([cmake, "--build", "."])
        run(["make", "tests"])
        if sudo_install:
            run(["sudo", "make", "install"])
        else:
            run(["make", "install"])


def build_libexiv2_macos():
    with tempfile.TemporaryDirectory() as td, \
         working_directory(td), \
         restore_environ():  # noqa: E126 - bug in flake8, indentation is fine

        # Ensure use of matching minimum OSX version and C++ runtime as
        # for the module itself.
        setenv("MACOSX_DEPLOYMENT_TARGET", "10.9")
        setenv("CXX", "clang++ -std=c++11 -stdlib=libc++")

        if libexiv2_is_already_available():
            return

        import certifi
        download_and_unpack_libexiv2(cafile=certifi.where(), patches=[
            "testsuite-with-suppress-warnings.patch",
        ])

        builddir = os.path.join(EXIV2_SRC_DIR, "build")
        makedirs(builddir)
        chdir(builddir)

        setenv("CFLAGS", "-DSUPPRESS_WARNINGS")
        setenv("CXXFLAGS", "-DSUPPRESS_WARNINGS -Wno-deprecated-declarations")
        run(["cmake", "..", "-DCMAKE_BUILD_TYPE=Release"])
        run(["cmake", "--build", "."])
        run(["make", "tests"])
        run(["make", "install"])


def build_libexiv2_windows():
    with tempfile.TemporaryDirectory() as td, \
         working_directory(td), \
         restore_environ():  # noqa: E126 - bug in flake8, indentation is fine

        if libexiv2_is_already_available():
            return

        import struct
        abi = struct.calcsize('P') * 8
        conan_profile = os.path.join("..", "cmake", "msvc_conan_profiles",
                                     "msvc2017Release" + str(abi))

        download_and_unpack_libexiv2(patches=[
            "testsuite-with-suppress-warnings.patch",
            "test-Makefile-use-bare-python.patch",
            "test-Makefile-skip-tiff-test.patch",
        ])

        builddir = os.path.join(EXIV2_SRC_DIR, "build")
        makedirs(builddir)
        chdir(builddir)

        run(["conan", "install", "..", "--build", "missing",
             "-pr="+conan_profile])

        setenv("CFLAGS", "/DSUPPRESS_WARNINGS")
        setenv("CXXFLAGS", "/DSUPPRESS_WARNINGS")
        run(["cmake", "..", "-DCMAKE_BUILD_TYPE=Release"])
        run(["cmake", "--build", "."])

        setenv("EXIV2_EXT", ".exe")
        run(["cmake", "--build", ".", "--target", "tests"])

        run(["cmake", "--build", ".", "--target", "INSTALL"])


def lint_cyexiv2(args):
    assert_in_srcdir()
    if os.path.isdir("build/venv"):
        activate_venv("build/venv")

    run(["python", "setup.py", "check", "-s", "-m"])

    run(["pip", "install", "pre-commit"])
    # only run pre-commit checks on files that actually changed
    changed_files = run_get_output([
        "git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"
    ])
    run(["pre-commit", "run", "--files"] + changed_files)


def build_cyexiv2_inplace(args):
    assert_in_srcdir()
    if os.path.isdir("build/venv"):
        activate_venv("build/venv")
    run(["python", "setup.py", "build_ext", "--inplace"])


def test_cyexiv2_inplace(args):
    assert_in_srcdir()
    if os.path.isdir("build/venv"):
        activate_venv("build/venv")

    with restore_environ():
        augment_path("PYTHONPATH", os.path.join(os.getcwd(), "src"))
        augment_path("LD_LIBRARY_PATH", "/usr/local/lib")
        run(["pytest", "--doctest-modules", "--junitxml=test-results.xml",
             "--cov=pyexiv2", "--cov-report=xml"])

        normalize_cov_xml("coverage.xml")


def build_and_test_sdist(args):
    # --formats tar because we can't control the gzip invocation used by
    # --formats gztar, and by default it will record a creation timestamp,
    # rendering the tarballs not directly comparable.
    sdist_cmd = [
        "python", "setup.py", "sdist",
        "-u", "root", "-g", "root", "--formats", "tar"
    ]
    bdist_wheel_cmd = [
        "python", "setup.py", "bdist_wheel"
    ]

    assert_in_srcdir()
    if os.path.isdir("build/venv"):
        activate_venv("build/venv")

    # Create an sdist tarball from a completely clean checkout.
    run(sdist_cmd)

    # Move that tarball out of the way, create a wheel, and then
    # create an sdist tarball again.
    rename_aside("dist", "cyexiv2", ".tar")
    run(bdist_wheel_cmd)
    run(sdist_cmd)

    # The two tarballs should be byte-for-byte identical.
    tarballs = sorted(glob.glob(os.path.join("dist", "cyexiv2*.tar")))
    if len(tarballs) != 2:
        log_error("expected 2 tarballs, got: {}".format(tarballs))
        raise RuntimeError("wrong number of tarballs")

    run(["cmp"] + tarballs)

    # Run an inplace build and test, having already created a wheel.
    build_cyexiv2_inplace(args)
    test_cyexiv2_inplace(args)

    # Unpack one of the sdists into a scratch directory.
    # Run an inplace build and test on that sdist,
    # then afterward build a wheel and another sdist from it.
    # Copy the test results, the wheel, and the sdist back.
    orig_wd = os.getcwd()
    orig_distdir = os.path.join(orig_wd, "dist")
    sdist_abs = os.path.join(orig_wd, tarballs[0])

    with tempfile.TemporaryDirectory() as td, working_directory(td):
        run(["tar", "xf", sdist_abs])
        chdir(os.listdir()[0])
        build_cyexiv2_inplace(args)
        test_cyexiv2_inplace(args)
        run(bdist_wheel_cmd)
        run(sdist_cmd)

        copyfile("test-results.xml",
                 os.path.join(orig_wd, "test-results-sdist.xml"))
        copyfile("coverage.xml",
                 os.path.join(orig_wd, "coverage-sdist.xml"))
        for f in os.listdir("dist"):
            base, ext = os.path.splitext(f)
            copyfile(os.path.join("dist", f),
                     os.path.join(orig_distdir, base + "-sdist" + ext))

    # Coverage results, the new wheel, and the new
    # tarball should be byte-for-byte identical to those generated
    # from within the checkout.  Test results should be XML-identical
    # ignoring elapsed time for each test.
    compare_test_results("test-results.xml", "test-results-sdist.xml")
    run(["diff", "-u", "coverage.xml", "coverage-sdist.xml"])

    distdir_contents = [os.path.join("dist", fname)
                        for fname in os.listdir("dist")]

    wheels = sorted((f for f in distdir_contents if f.endswith(".whl")),
                    key = lambda f: (len(f), f))
    if len(wheels) != 2:
        log_error("expected 2 wheels, got: {}".format(wheels))
        raise RuntimeError("wrong number of wheels")

    tarballs = sorted((f for f in distdir_contents if f.endswith(".tar")),
                      key = lambda f: (len(f), f))
    old_tarball = tarballs[0]
    new_tarball = tarballs[-1]
    try:
        assert len(tarballs) == 3
        assert new_tarball.endswith("-sdist.tar")
        assert not old_tarball.endswith("-sdist.tar")
        assert not old_tarball.endswith("-1.tar")
    except AssertionError:
        raise RuntimeError("tarball names not as expected: {}"
                           .format(tarballs))

    run(["cmp"] + wheels)
    run(["cmp", old_tarball, new_tarball])

    # Remove everything except one of the tarballs from the dist
    # directory. The wheels are out-of-spec for installation anywhere,
    # but the sdist tar will get saved as a pipeline artifact and might
    # eventually even get uploaded to PyPI.
    for fname in distdir_contents:
        if fname != old_tarball:
            remove(fname)

    # Compress the remaining tarball.  Use gzip -n so there is no
    # embedded timestamp.
    run(["gzip", "-n", old_tarball])

    # Run a Twine check on the tarball.
    run(["pip", "install", "twine"])
    run(["twine", "check", old_tarball + ".gz"])


def cibuildwheel_outer(args):
    assert_in_srcdir()
    ensure_venv("build/cibw-venv")

    # On Windows, trying to use the 'pip' binary to upgrade pip will
    # throw an "Access is denied" error, because it's trying to overwrite
    # a running executable.
    run(["python", "-m", "pip", "install", "--upgrade", "pip"])
    run(["pip", "install", "cibuildwheel", "twine"])

    S = setenv
    S("CIBW_SKIP", "cp27-*")
    S("CIBW_BEFORE_BUILD",
      "python {project}/ci/azure-build.py cibw-beforebuild")
    S("CIBW_TEST_COMMAND", "pytest {project}/test")
    S("CIBW_TEST_REQUIRES", "pytest")
    S("CIBW_BUILD_VERBOSITY", "3")

    sysname = platform.system()
    if sysname == "Linux":
        # a version of cibw that defaults to manylinux2010 has not yet
        # been released
        S("CIBW_MANYLINUX1_X86_64_IMAGE", "quay.io/pypa/manylinux2010_x86_64")
        S("CIBW_MANYLINUX1_I686_IMAGE", "quay.io/pypa/manylinux2010_i686")

    elif sysname == "Darwin":
        # delocate won't find libexiv2.dylib without this
        S("CIBW_ENVIRONMENT", "DYLD_LIBRARY_PATH=/usr/local/lib")

    elif sysname == "Windows":
        # need more detail for debugging
        S("LOG_EXCEPTION_TRACEBACKS", "yes")

    run(["cibuildwheel", "--output-dir", "wheelhouse"])

    run(["twine", "check"] + glob.glob("wheelhouse/*.whl"))


def cibuildwheel_before(args):
    report_env(args)

    sysname = platform.system()
    if sysname == "Linux":
        install_deps_centos(args)
        build_libexiv2_linux(args, False)

    elif sysname == "Darwin":
        install_deps_macos()
        build_libexiv2_macos()

    elif sysname == "Windows":
        install_deps_windows()
        build_libexiv2_windows()

    else:
        raise RuntimeError("Unrecognized system: " + sysname)


def main():
    ACTIONS = {
        "report-env": report_env,
        "install-deps-ubuntu": install_deps_ubuntu,
        "install-deps-centos": install_deps_centos,
        "build-libexiv2-ubuntu": lambda a: build_libexiv2_linux(a, True),
        "lint-cyexiv2": lint_cyexiv2,
        "build-cyexiv2-inplace": build_cyexiv2_inplace,
        "test-cyexiv2-inplace": test_cyexiv2_inplace,
        "build-and-test-sdist": build_and_test_sdist,
        "cibw-outer": cibuildwheel_outer,
        "cibw-beforebuild": cibuildwheel_before,
    }

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=ACTIONS.keys())
    args = ap.parse_args()

    try:
        sanitize_env()
        ACTIONS[args.action](args)
        sys.exit(0)

    except subprocess.CalledProcessError as e:
        log_failed_process(e)
        sys.exit(1)

    except Exception as e:
        import traceback
        if "LOG_EXCEPTION_TRACEBACKS" in os.environ:
            log_error(traceback.format_exc())
        else:
            log_error("".join(traceback.format_exception_only(type(e), e)))

        sys.exit(1)


if __name__ == "__main__":
    main()
