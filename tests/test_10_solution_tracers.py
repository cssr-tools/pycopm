# SPDX-FileCopyrightText: 2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0

"""Test per-cell tracer concentrations in the SOLUTION section."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from pycopm.core.pycopm import main
from pycopm.utils.parser_deck import (
    _handle_tracer_blocks,
    _ParserState,
    _resize_tracer_include,
)

TRACER = "TRACER\nIW1 WAT /\nIW2 WAT /\n/\n"


@pytest.fixture(name="refine_hello_world")
def fixture_refine_hello_world(flow, tmp_path, monkeypatch):
    """Return a function that refines HELLO_WORLD in tmp_path, with two water tracers
    whose concentrations are set by the given SOLUTION records, and returns the
    generated deck."""
    monkeypatch.chdir(tmp_path)

    def refine(solution_records):
        examples = Path(__file__).parents[1] / "examples" / "decks"
        deck_text = (examples / "HELLO_WORLD.DATA").read_text(encoding="utf8")
        for anchor, records in (
            ("METRIC\n", "TRACERS\n0 2 /\n\n"),
            ("1 1 0 0 /\n", TRACER),
            ("0 1 0 0 0 0 1 1 0 /\n", solution_records),
        ):
            assert anchor in deck_text
            deck_text = deck_text.replace(anchor, anchor + records, 1)
        (tmp_path / "HELLO_WORLD.DATA").write_text(deck_text, encoding="utf8")

        main(["-i", "HELLO_WORLD.DATA", "-f", flow, "-g", "1,1,0", "-m", "all"])

        assert (tmp_path / "HELLO_WORLD_PYCOPM.EGRID").is_file()
        return (tmp_path / "HELLO_WORLD_PYCOPM.DATA").read_text(encoding="utf8")

    return refine


def test_10_solution_tracers(refine_hello_world):
    """Constant TBLKF arrays must be resized to the refined grid."""

    generated = refine_hello_world(
        "\nTBLKFIW1\n200*0.0\n200*0 /\nTBLKFIW2\n400*1.0 /\n"
    )

    assert "TBLKFIW1\n1600*0.0 /" in generated
    assert "TBLKFIW2\n1600*1.0 /" in generated


def test_10_solution_tracers_includes(refine_hello_world, tmp_path):
    """Constant TBLKF arrays in included files, nested or not, must be resized in
    copies of these files, also when they are reached through a file that only
    includes them."""

    (tmp_path / "SOLUTION.INC").write_text(
        "-- Comment.\nTBLKFIW1\n400*0.0 /\nINCLUDE\n'PARENT.INC' /\n", encoding="utf8"
    )
    (tmp_path / "PARENT.INC").write_text("INCLUDE\n'NESTED.INC' /\n", encoding="utf8")
    (tmp_path / "NESTED.INC").write_text("TBLKFIW2\n400*1.0 /\n", encoding="utf8")

    generated = refine_hello_world("\nINCLUDE\n'SOLUTION.INC' /\n")

    assert "INCLUDE\n'PYCOPM_TRACERS_SOLUTION.INC' /\n" in generated
    assert (tmp_path / "PYCOPM_TRACERS_SOLUTION.INC").read_text(encoding="utf8") == (
        "-- Comment.\nTBLKFIW1\n1600*0.0 /\nINCLUDE\n'PYCOPM_TRACERS_PARENT.INC' /\n"
    )
    assert (tmp_path / "PYCOPM_TRACERS_PARENT.INC").read_text(encoding="utf8") == (
        "INCLUDE\n'PYCOPM_TRACERS_NESTED.INC' /\n"
    )
    assert (tmp_path / "PYCOPM_TRACERS_NESTED.INC").read_text(encoding="utf8") == (
        "TBLKFIW2\n1600*1.0 /\n"
    )


def test_10_solution_tracers_copy_names(tmp_path):
    """Files sharing a name must get their own copies, and a file included again
    must reuse its copy."""

    for folder, value in (("a", "0.0"), ("b", "1.0")):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "TRACERS.INC").write_text(
            f"TBLKFIW1\n1*{value} /\n", encoding="utf8"
        )
    dck = SimpleNamespace(
        deck_encoding="utf8",
        include_prefix="PYCOPM_",
        input_deck_name=str(tmp_path / "DECK"),
        output_directory=str(tmp_path),
        output_nx=2,
        output_ny=2,
        output_nz=1,
    )
    copies: dict[Path, str] = {}

    records = [
        _resize_tracer_include(dck, f"'{path}' /", copies)
        for path in ("a/TRACERS.INC", "b/TRACERS.INC", "a/TRACERS.INC")
    ]

    assert records == [
        "'PYCOPM_TRACERS_TRACERS.INC' /",
        "'PYCOPM_TRACERS_TRACERS_2.INC' /",
        "'PYCOPM_TRACERS_TRACERS.INC' /",
    ]
    for name, value in (("TRACERS", "0.0"), ("TRACERS_2", "1.0")):
        assert (tmp_path / f"PYCOPM_TRACERS_{name}.INC").read_text(
            encoding="utf8"
        ) == f"TBLKFIW1\n4*{value} /\n"


def test_10_solution_tracers_records():
    """Records spread over lines are resized, and differing values stop pycopm."""

    dck = SimpleNamespace(output_nx=2, output_ny=2, output_nz=1)

    def handle(lines):
        kwr, deck = _ParserState(), []
        for line in lines:
            assert _handle_tracer_blocks(dck, kwr, deck, line)
        return deck

    assert handle(["TBLKSIW1 -- Comment.", "3*0.5", "-- Comment.", "0.50/"]) == [
        "TBLKSIW1",
        "4*0.5 /",
    ]
    with pytest.raises(SystemExit, match="TBLKFIW1"):
        handle(["TBLKFIW1", "3*0.0 1.0 /"])
