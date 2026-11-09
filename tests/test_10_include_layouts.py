# SPDX-FileCopyrightText: 2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Test decks with INCLUDE records spread over several lines."""

from types import SimpleNamespace

import pytest

from pycopm.core.pycopm import main
from pycopm.utils.parser_deck import (
    _include_contains_endbox,
    _include_keyword_index,
    _scan_deck_file,
    _special_include_names,
    find_multiplier_keywords,
)

from .utils import SGWFN_TABLE as TABLE
from .utils import hello_world_deck

PROPS_INCLUDES = (
    "INCLUDE\n'TABLE_SWL.INC' /\n\nINCLUDE\n-- End points.\n'ENDPOINTS.INC' /\n"
)
ENDSCALE = ("METRIC\n", "METRIC\n\nENDSCALE\n/\n")


@pytest.fixture(name="run_hello_world")
def fixture_run_hello_world(flow, tmp_path, monkeypatch):
    """Return a function that runs pycopm on HELLO_WORLD in tmp_path, with its SGWFN
    table replaced by the given records, and returns the generated deck."""
    monkeypatch.chdir(tmp_path)

    def run(props_records, edits=(), grid=("-c", "5,5,1")):
        deck_text = hello_world_deck(props_records)
        for old, new in edits:
            assert old in deck_text
            deck_text = deck_text.replace(old, new)
        (tmp_path / "HELLO_WORLD.DATA").write_text(deck_text, encoding="utf8")

        main(["-i", "HELLO_WORLD.DATA", "-f", flow, *grid, "-m", "all"])

        assert (tmp_path / "HELLO_WORLD_PYCOPM.EGRID").is_file()
        return (tmp_path / "HELLO_WORLD_PYCOPM.DATA").read_text(encoding="utf8")

    return run


def _write_props_includes(tmp_path):
    """Write the includes of PROPS_INCLUDES, only the first of which has "swl" in its
    name."""
    (tmp_path / "TABLE_SWL.INC").write_text(TABLE, encoding="utf8")
    (tmp_path / "ENDPOINTS.INC").write_text("SWL\n400*0.1 /\n", encoding="utf8")


def test_10_include_layouts(run_hello_world, tmp_path):
    """A blank line between INCLUDE and its path must not crash the include scan."""

    (tmp_path / "SGWFN.INC").write_text(TABLE, encoding="utf8")

    run_hello_world("INCLUDE\n\n'SGWFN.INC' /\n")


def test_10_include_layouts_props(run_hello_world, tmp_path):
    """The include holding SWL must be replaced and the one holding SGWFN kept,
    although only the latter has "swl" in its name and the former has a comment
    before its path."""

    _write_props_includes(tmp_path)

    deck_text = run_hello_world(PROPS_INCLUDES, edits=[ENDSCALE])

    assert "INCLUDE\n'PYCOPM_SWL.INC' /\n" in deck_text


def test_10_include_layouts_props_inlined(run_hello_world, tmp_path):
    """A replaced include whose refined values are all equal must be inlined, with
    the comment before its path kept and its INCLUDE removed."""

    _write_props_includes(tmp_path)
    fully_active = [
        ("PORO 0 6 10 11 15 2* /\n", ""),
        ("PORO 0 16 20 1 5 2* /\n", ""),
    ]

    deck_text = run_hello_world(
        PROPS_INCLUDES, edits=[ENDSCALE, *fully_active], grid=("-g", "1,1,0")
    )

    assert "'TABLE_SWL.INC' /\n\n-- End points.\nSWL\n1600*0.1 /\n" in deck_text
    assert "PYCOPM_SWL.INC" not in deck_text


def test_10_include_layouts_scan(tmp_path):
    """Comments, remarks, directories and quoting must not hide or replace the include."""

    (tmp_path / "sub").mkdir()
    (tmp_path / "A.INC").write_text("MULTZ\n1*0.5 /\n", encoding="utf8")
    (tmp_path / "B.INC").write_text("", encoding="utf8")
    (tmp_path / "C.INC").write_text("", encoding="utf8")
    (tmp_path / "sub" / "D.INC").write_text("MULTX\n1*0.5 /\n", encoding="utf8")
    (tmp_path / "E F.INC").write_text("MULTY\n1*0.5 /\n", encoding="utf8")
    (tmp_path / "G.INC").write_text("", encoding="utf8")
    (tmp_path / "DECK.DATA").write_text(
        "INCLUDE\n\n'A.INC' / Remark.\n"
        "INCLUDE -- Comment.\n-- Comment.\n'B.INC'\t/\n"
        "INCLUDE\nC.INC /\n"
        "INCLUDE\nsub/D.INC /\n"
        'INCLUDE\n"E F.INC" /\n'
        f"INCLUDE\n{tmp_path / 'G.INC'} /\n"
        "INCLUDE\n'MISSING.INC' /\n",
        encoding="utf8",
    )
    dck = SimpleNamespace(deck_encoding="utf8", input_deck_name=str(tmp_path / "DECK"))

    includes, _, _ = _scan_deck_file(dck, tmp_path / "DECK.DATA")
    _, mults = find_multiplier_keywords(dck)

    names = ("A.INC", "B.INC", "C.INC", "sub/D.INC", "E F.INC", "G.INC")
    assert includes == [str(tmp_path / name) for name in names]
    assert mults.tolist() == [True, False, True, False, True, False]


def test_10_include_layouts_endbox(tmp_path):
    """The ENDBOX check must find includes in subdirectories and with spaces in their name."""

    (tmp_path / "sub").mkdir()
    box = "BOX\n1 1 1 1 1 1 /\nENDBOX\n"
    (tmp_path / "sub" / "BOX.INC").write_text(box, encoding="utf8")
    (tmp_path / "MY BOX.INC").write_text(box, encoding="utf8")
    dck = SimpleNamespace(deck_encoding="utf8", input_deck_name=str(tmp_path / "DECK"))

    assert _include_contains_endbox(dck, "sub/BOX.INC /")
    # The csv reader has already stripped the double quotes of `"MY BOX.INC" /`.
    assert _include_contains_endbox(dck, "MY BOX.INC /")


def test_10_include_layouts_keyword_index():
    """The path record is matched to its INCLUDE across blank and comment lines."""

    deck = ["PROPS", "INCLUDE -- Comment.", "", "-- Comment."]

    assert _include_keyword_index(deck, "'A.INC' /") == 1
    assert _include_keyword_index(deck, "-- swl.") is None
    assert _include_keyword_index(deck, "") is None
    assert _include_keyword_index(deck + ["'A.INC' /"], "'B.INC' /") is None


def test_10_include_layouts_special_keywords(tmp_path):
    """Includes are replaced by the keywords they define, not by their names."""

    files = {
        "ENDPOINTS": "SWL\n400*0.1 /\n",
        "pp03_KRW": "-- Comment.\nKRWR\n400*0.9 /\n",
        "BOTH": "SWL\n400*0.1 /\nKRWR\n400*0.9 /\n",
        "TABLE_SWL": TABLE,
        "MIXED": "SWL\n400*0.1 /\n" + TABLE,
    }
    for name, text in files.items():
        (tmp_path / name).write_text(text, encoding="utf8")
    dck = SimpleNamespace(
        deck_encoding="utf8",
        include_prefix="PYCOPM_",
        input_deck_name=str(tmp_path / "DECK"),
        special_keywords=["swl", "krwr", "krw"],
    )

    def names(path):
        return _special_include_names(dck, True, f"'{path}' /")

    assert names("ENDPOINTS") == ["swl"]
    assert names("pp03_KRW") == ["krwr"]
    assert names("BOTH") == ["swl", "krwr"]
    assert names("TABLE_SWL") == []
    assert names("MIXED") == []
    assert names("MISSING_SWL.INC") == ["swl"]
