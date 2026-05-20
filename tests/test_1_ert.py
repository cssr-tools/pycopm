# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Test the ert functionality via the configuration file"""

from pathlib import Path
import subprocess


def test_1_ert(flow, tmp_path, monkeypatch):
    """See examples/configurations/drogon/input.toml"""
    repo_root = Path(__file__).parents[1]
    monkeypatch.chdir(tmp_path)
    confi = f"{repo_root}/examples/configurations/drogon/input.toml"
    subprocess.run(["pycopm", "-i", confi, "-o", "ert", "-f", flow], check=True)
    assert (tmp_path / "ert" / "postprocessing" / "hm_missmatch.png").is_file()
