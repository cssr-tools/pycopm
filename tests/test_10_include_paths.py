# SPDX-FileCopyrightText: 2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Test decks with relative INCLUDE paths written to another output folder."""

from pathlib import Path

from pycopm.core.pycopm import main
from pycopm.utils.generate_decks import _resolve_include_paths

TABLE = "SGWFN\n0 0\t1 0\n1 1 0 0 /\n"


def test_10_include_paths(flow, tmp_path, monkeypatch):
    """Both dry runs must find the includes when the output folder is not the deck's."""

    monkeypatch.chdir(tmp_path)

    repo_root = Path(__file__).parents[1]
    deck_text = (repo_root / "examples" / "decks" / "HELLO_WORLD.DATA").read_text(
        encoding="utf8"
    )
    assert TABLE in deck_text
    deck_folder = tmp_path / "deck"
    (deck_folder / "include").mkdir(parents=True)
    (deck_folder / "include" / "SGWFN.INC").write_text(TABLE, encoding="utf8")
    (deck_folder / "HELLO_WORLD.DATA").write_text(
        deck_text.replace(TABLE, "INCLUDE\n'include/SGWFN.INC' /\n"),
        encoding="utf8",
    )

    main(
        [
            "-i",
            str(deck_folder / "HELLO_WORLD.DATA"),
            "-f",
            flow,
            "-c",
            "5,5,1",
            "-m",
            "all",
            "-o",
            "output",
        ]
    )

    assert (tmp_path / "output" / "HELLO_WORLD_PYCOPM.EGRID").is_file()
    assert "'../deck/include/SGWFN.INC' /" in (
        tmp_path / "output" / "HELLO_WORLD_PYCOPM.DATA"
    ).read_text(encoding="utf8")


def test_10_include_paths_kept(tmp_path):
    """Absolute, aliased, and same-folder paths must not be rewritten."""

    deck_text = (
        "INCLUDE\n'/abs/A.INC' /\n"
        "INCLUDE\n'$DIR/B.INC' /\n"
        "INCLUDE\n\n-- Comment.\n'C.INC' / Remark.\n"
    )

    assert _resolve_include_paths(deck_text, tmp_path, tmp_path) == deck_text
    assert _resolve_include_paths(deck_text, tmp_path, tmp_path / "out") == (
        deck_text.replace("'C.INC'", "'../C.INC'")
    )
