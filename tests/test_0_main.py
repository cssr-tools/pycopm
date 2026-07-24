# SPDX-FileCopyrightText: 2024-2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Test the configuration files"""

from pathlib import Path
import shutil

from pycopm.core.pycopm import main


def test_0_main(flow, tmp_path, monkeypatch):
    """See examples/configurations/norne/input.toml"""
    monkeypatch.chdir(tmp_path)
    repo_root = Path(__file__).parents[1]
    input_config = repo_root / "examples" / "configurations" / "norne" / "input.toml"
    shutil.copy(input_config, tmp_path / "input.toml")
    monkeypatch.chdir(tmp_path)
    main(["-f", flow])
    assert (tmp_path / "postprocessing" / "errors.txt").is_file()
    assert (
        tmp_path / "postprocessing" / "wells" / "HISTO_DATA_WWPR_E-1H.png"
    ).is_file()
