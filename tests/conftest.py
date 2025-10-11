# SPDX-FileCopyrightText: 2025 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Command flag to pycopm for the path of the OPM Flow executable"""

import pytest


def pytest_addoption(parser):
    """Path to the OPM Flow executable"""
    parser.addoption("--flow", action="store", default="flow")


@pytest.fixture(scope="session")
def flow(request):
    """Get the OPM Flow executable path"""
    return request.config.option.flow
