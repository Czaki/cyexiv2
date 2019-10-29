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


def patched_make_tarball(base_name, base_dir, compress="gzip",
                         verbose=0, dry_run=0, owner=None, group=None):
    """Modified version of distutils.archive_util.make_tarball which supports
    SOURCE_DATE_EPOCH.

    Create a (possibly compressed) tar file from all the files under
    'base_dir'.

    'compress' must be "gzip" (the default), "bzip2", "xz", "compress", or
    None.  ("compress" will be deprecated in Python 3.2)

    'owner' and 'group' can be used to define an owner and a group for the
    archive that is being built. If not provided, the current owner and group
    will be used.

    If the environment variable SOURCE_DATE_EPOCH is set, each file's
    timestamp will be adjusted to be no later than that value.

    The output tar file will be named 'base_dir' +  ".tar", possibly plus
    the appropriate compression extension (".gz", ".bz2", ".xz" or ".Z").

    Returns the output filename.
    """
    # late imports to avoid circular dependencies
    import os
    import sys
    import tarfile
    from distutils.archive_util import (
        _get_gid,
        _get_uid,
        log,
        mkpath,
        spawn,
        warn,
    )

    tar_compression = {'gzip': 'gz', 'bzip2': 'bz2', 'xz': 'xz', None: '',
                       'compress': ''}
    compress_ext = {'gzip': '.gz', 'bzip2': '.bz2', 'xz': '.xz',
                    'compress': '.Z'}

    # flags for compression program, each element of list will be an argument
    if compress is not None and compress not in compress_ext.keys():
        raise ValueError(
            "bad value for 'compress': must be None, 'gzip', 'bzip2', "
            "'xz' or 'compress'")

    archive_name = base_name + '.tar'
    if compress != 'compress':
        archive_name += compress_ext.get(compress, '')

    mkpath(os.path.dirname(archive_name), dry_run=dry_run)

    log.info('Creating tar archive')

    uid = _get_uid(owner)
    gid = _get_gid(group)
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch is not None:
        epoch = int(epoch)

    def _adjust_tarinfo(tarinfo):
        if gid is not None:
            tarinfo.gid = gid
            tarinfo.gname = group
        if uid is not None:
            tarinfo.uid = uid
            tarinfo.uname = owner
        if epoch is not None:
            if tarinfo.mtime > epoch:
                tarinfo.mtime = epoch
        return tarinfo

    if not dry_run:
        tar = tarfile.open(archive_name, 'w|%s' % tar_compression[compress])
        try:
            tar.add(base_dir, filter=_adjust_tarinfo)
        finally:
            tar.close()

    # compression using `compress`
    if compress == 'compress':
        warn("'compress' will be deprecated.", PendingDeprecationWarning)
        # the option varies depending on the platform
        compressed_name = archive_name + compress_ext[compress]
        if sys.platform == 'win32':
            cmd = [compress, archive_name, compressed_name]
        else:
            cmd = [compress, '-f', archive_name]
        spawn(cmd, dry_run=dry_run)
        return compressed_name

    return archive_name


def install_patched_make_tarball():
    """Monkey patch SOURCE_DATE_EPOCH support into sdist generation.
    Workaround for <https://bugs.python.org/issue38632>.
    """

    from distutils.archive_util import ARCHIVE_FORMATS
    for fmt, (fn, params, desc) in list(ARCHIVE_FORMATS.items()):
        if fmt.endswith('tar'):
            ARCHIVE_FORMATS[fmt] = (patched_make_tarball, params, desc)


def restore_sdist_d_and_u():
    """Restore the -u and -g options from distutils' sdist command.
    Workaround for <https://github.com/pypa/setuptools/issues/1893>.

    The CI driver needs these to produce sdist tarballs independent of
    the user running the script.  It is unclear why setuptools removed
    them.
    """
    from distutils.command.sdist import sdist as d_sdist
    from setuptools.command.sdist import sdist as s_sdist

    need_owner = True
    need_group = True
    for opt_tuple in s_sdist.user_options:
        if opt_tuple[0] == 'owner=':
            need_owner = False
        elif opt_tuple[0] == 'group=':
            need_group = False

    if not need_owner and not need_group:
        return
    for opt_tuple in d_sdist.user_options:
        if ((need_owner and opt_tuple[0] == 'owner=')
            or (need_group and opt_tuple[0] == 'group=')):  # noqa: E129
            s_sdist.user_options.append(opt_tuple)
