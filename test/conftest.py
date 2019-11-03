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
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# pyexiv2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyexiv2.  If not, see <https://www.gnu.org/licenses/>.
#
# Author: Zack Weinberg <zackw@panix.com>
#
# ******************************************************************************

"""Local pytest hooks for the cyexiv2 testsuite."""

import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Reporting hook which makes all tests be treated as having failed
       if they wrote anything to stdout or stderr.  We do this because
       libexiv2 may write debugging messages to the C++ cerr stream if
       it's misconfigured.
    """

    report = (yield).get_result()
    if not hasattr(report, "outcome") or not hasattr(report, "sections"):
        return
    if report.outcome != "passed":
        return

    for label, content in report.sections:
        if (
                content
                and ("stdout" in label or "stderr" in label)
                and call.when in label
        ):
            report.outcome = "failed"
