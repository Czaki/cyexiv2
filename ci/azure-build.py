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

CAN_FCHDIR = os.supports_fd

# This list partially cribbed from Autoconf's shell environment
# normalization logic.
BAD_ENVIRONMENT_VARS = frozenset((
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

# Directories likely to contain a version control system's metadata.
# This list was cribbed from Emacs' vc/*.el and is not remotely
# exhaustive, but covers everything that's likely to be used and a few
# more.  To avoid a number of Windows-related headaches, the names
# have all been lowercased and leading '.' and '_' have been removed.

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
    if not d:
        return False
    if d[0] in ('_', '.'):
        d = d[1:]
    return d.lower() in VERSION_CONTROL_DIRS


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


def log_warning(msg):
    for line in msg.splitlines():
        sys.stdout.write("##[warning]" + msg.rstrip() + "\n")
    sys.stdout.flush()


def log_error(msg):
    for line in msg.splitlines():
        sys.stdout.write("##[error]" + msg.rstrip() + "\n")
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
    times = (timestamp, timestamp)
    for subdir, dirs, files in os.walk(topdir):
        vcs_dirs = [d for d in dirs if is_vcs_dir(d)]
        for d in vcs_dirs:
            dirs.remove(d)

        try:
            os.utime(subdir, times=times, follow_symlinks=False)
        except OSError as e:
            log_warning("resetting timestamp on {}: {}"
                        .format(subdir, e))

        for f in files:
            fpath = os.path.join(subdir, f)
            try:
                os.utime(fpath, times=times, follow_symlinks=False)
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
            log_warning("fchdir: " + str(e))
            os.chdir(prev_wd_path)
            CAN_FCHDIR = False

        os.close(prev_wd_fd)


def augment_path(var, dir):
    """Add DIR to the front of the PATH-like environment variable VAR."""
    if var in os.environ:
        os.environ[var] = dir + os.pathsep + os.environ[var]
    else:
        os.environ[var] = dir
    log_command("export", "{}={}".format(var, os.environ[var]))


@contextlib.contextmanager
def restore_environ():
    """Restore all environment variables to their previous values upon
       exiting the context."""
    save_env = os.environ.copy()
    yield
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
            try:
                el.removeAttribute("time")
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
    recursive_reset_timestamps(EXIV2_SRC_BASE, EXIV2_SRC_TS)


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
        sys.executable, "setup.py", "sdist",
        "-u", "root", "-g", "root", "--formats", "tar"
    ]
    bdist_wheel_cmd = [
        sys.executable, "setup.py", "bdist_wheel"
    ]

    assert_in_srcdir()

    # Create an sdist tarball from a completely clean checkout.
    run(sdist_cmd)

    # Move that tarball out of the way, create a wheel, and then
    # create an sdist tarball again.
    rename_aside("dist", "cyexiv2", ".tar")
    run(bdist_wheel_cmd)
    run(sdist_cmd)

    # The two tarballs should be byte-for-byte identical.
    tarballs = sorted(os.path.join("dist", fname)
                      for fname in os.listdir("dist")
                      if fname.startswith("cyexiv2")
                      and fname.endswith(".tar"))
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

    wheels = sorted(os.path.join("dist", fname)
                    for fname in os.listdir("dist")
                    if fname.startswith("cyexiv2")
                    and fname.endswith(".whl"))
    if len(wheels) != 2:
        log_error("expected 2 wheels, got: {}".format(wheels))
        raise RuntimeError("wrong number of wheels")

    run(["cmp"] + wheels)

    new_tarball = [os.path.join("dist", fname)
                   for fname in os.listdir("dist")
                   if fname.startswith("cyexiv2")
                   and fname.endswith("-sdist.tar")][0]
    run(["cmp", tarballs[0], new_tarball])


def normalize_env():
    # Clear all of the BAD_ENVIRONMENT_VARS and all LC_* variables,
    to_unset = []
    for k in os.environ.keys():
        if k in BAD_ENVIRONMENT_VARS or k.startswith("LC_"):
            to_unset.append(k)

    for k in to_unset:
        log_command("unset", k)
        del os.environ[k]

    # Set LC_ALL=C.UTF-8 if supported, otherwise LC_ALL=C.
    log_command("export", "LC_ALL=C.UTF-8")
    os.environ["LC_ALL"] = "C.UTF-8"
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error as e:
        log_warning("C.UTF-8 locale not available: {}".format(e))

        log_command("export", "LC_ALL=C")
        os.environ["LC_ALL"] = "C"
        locale.setlocale(locale.LC_ALL, "")

    # Set SOURCE_DATE_EPOCH if possible and not already set.
    if "SOURCE_DATE_EPOCH" not in os.environ:
        sourcedate = None
        try:
            gitcmd = ["git", "show", "-s", "--format=%ct", "HEAD"]
            log_command(*gitcmd)
            sourcedate = \
                subprocess.check_output(gitcmd).decode("ascii").strip()
        except subprocess.CalledProcessError:
            pass

        # FIXME: implement a way to do this from an sdist tarball.
        # We could take the maximum of all the source timestamps
        # but that seems both slow and fragile.

        if sourcedate is not None:
            log_command("export", "SOURCE_DATE_EPOCH="+sourcedate)
            os.environ["SOURCE_DATE_EPOCH"] = sourcedate
        else:
            log_warning("no VCS info available and SOURCE_DATE_EPOCH not set")


def main():
    ACTIONS = {
        "report-env": report_env,
        "install-deps-ubuntu": install_deps_ubuntu,
        "build-libexiv2-ubuntu": build_libexiv2_ubuntu,
        "build-cyexiv2-inplace": build_cyexiv2_inplace,
        "test-cyexiv2-inplace": test_cyexiv2_inplace,
        "build-and-test-sdist": build_and_test_sdist
    }

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=ACTIONS.keys())
    args = ap.parse_args()

    try:
        normalize_env()
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
