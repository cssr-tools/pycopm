# SPDX-FileCopyrightText: 2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Test decks with INCLUDE records spread over several lines."""

from pathlib import Path
from types import SimpleNamespace

from pycopm.core.pycopm import main
from pycopm.utils.parser_deck import _scan_deck_file, find_multiplier_keywords

TABLE = "SGWFN\n0 0\t1 0\n1 1 0 0 /\n"


def test_10_include_layouts(flow, tmp_path, monkeypatch):
    """A blank line between INCLUDE and its path must not crash the include scan."""

    monkeypatch.chdir(tmp_path)

    repo_root = Path(__file__).parents[1]
    deck_text = (repo_root / "examples" / "decks" / "HELLO_WORLD.DATA").read_text(
        encoding="utf8"
    )
    assert TABLE in deck_text
    (tmp_path / "SGWFN.INC").write_text(TABLE, encoding="utf8")
    (tmp_path / "HELLO_WORLD.DATA").write_text(
        deck_text.replace(TABLE, "INCLUDE\n\n'SGWFN.INC' /\n"),
        encoding="utf8",
    )

    main(
        [
            "-i",
            "HELLO_WORLD.DATA",
            "-f",
            flow,
            "-c",
            "5,5,1",
            "-m",
            "all",
        ]
    )

    assert (tmp_path / "HELLO_WORLD_PYCOPM.EGRID").is_file()


def test_10_include_layouts_scan(tmp_path):
    """Comments and remarks around the path must not hide or replace the include."""

    (tmp_path / "A.INC").write_text("MULTZ\n1*0.5 /\n", encoding="utf8")
    (tmp_path / "B.INC").write_text("", encoding="utf8")
    (tmp_path / "C.INC").write_text("", encoding="utf8")
    (tmp_path / "DECK.DATA").write_text(
        "INCLUDE\n\n'A.INC' / Remark.\n"
        "INCLUDE -- Comment.\n-- Comment.\n'B.INC'\t/\n"
        "INCLUDE\nC.INC /\n"
        "INCLUDE\n'MISSING.INC' /\n",
        encoding="utf8",
    )
    dck = SimpleNamespace(deck_encoding="utf8", input_deck_name=str(tmp_path / "DECK"))

    includes, _, _ = _scan_deck_file(dck, tmp_path / "DECK.DATA")
    _, mults = find_multiplier_keywords(dck)

    assert includes == [str(tmp_path / name) for name in ("A.INC", "B.INC", "C.INC")]
    assert mults.tolist() == [False, False, False, False, True, False]
