# SPDX-FileCopyrightText: 2026 NORCE Research AS
# SPDX-License-Identifier: GPL-3.0
# pylint: disable=R0913,R0917

"""Common test assertion utilities."""

from pathlib import Path

import numpy as np
import pytest

RTOL = 1e-5
ATOL = 1e-8


def assert_init_checks(
    init,
    checks,
    exact_checks=None,
    active_cells=None,
):
    """Check floating-point, integer, and active-cell regressions."""

    for keyword, op, reference in checks:
        value = op(init[keyword])

        assert value == pytest.approx(
            reference,
            rel=RTOL,
            abs=ATOL,
        ), (
            f"{op.__name__}({keyword}) = {value}, " f"expected {reference}"
        )

    if exact_checks:
        for keyword, op, expected in exact_checks:
            value = op(init[keyword])

            assert value == expected, (
                f"{op.__name__}({keyword}) = {value}, " f"expected {expected}"
            )

    if active_cells is not None:
        active = int(np.sum(init["PORV"] > 0))

        assert active == active_cells, (
            f"active cells = {active}, " f"expected {active_cells}"
        )


def _convert_deck_token(token):
    """Normalize and convert one deck token."""

    token = token.strip()

    if len(token) >= 2 and token[0] == token[-1] and token[0] in {"'", '"'}:
        token = token[1:-1]

    try:
        return int(token)
    except ValueError:
        pass

    try:
        return float(token)
    except ValueError:
        return token


def _split_deck_line(line):
    """Split a deck line into tokens without regex or shlex."""

    tokens = []
    current = []
    quote = None

    for character in line:
        if quote is not None:
            if character == quote:
                quote = None
            else:
                current.append(character)

            continue

        if character in {"'", '"'}:
            quote = character
            continue

        if character == "/":
            if current:
                tokens.append("".join(current))
                current = []

            tokens.append("/")
            continue

        if character.isspace():
            if current:
                tokens.append("".join(current))
                current = []

            continue

        current.append(character)

    if current:
        tokens.append("".join(current))

    return tokens


def _read_keyword_records(data_file, keyword):
    """Read slash-terminated records for one keyword."""

    lines = Path(data_file).read_text(encoding="utf8").splitlines()

    records = []
    current_record = []
    reading_keyword = False

    for raw_line in lines:
        line = raw_line.split("--", maxsplit=1)[0].strip()

        if not line:
            continue

        if not reading_keyword:
            first_token = line.split(maxsplit=1)[0]

            if first_token.upper() != keyword.upper():
                continue

            reading_keyword = True

            remainder = line[len(first_token) :].strip()

            if not remainder:
                continue

            tokens = _split_deck_line(remainder)
        else:
            tokens = _split_deck_line(line)

        for token in tokens:
            if token != "/":
                current_record.append(_convert_deck_token(token))
                continue

            if current_record:
                records.append(current_record)
                current_record = []
            else:
                return records

    return records


def _normalize_expected_records(expected):
    """Normalize one expected record or a list of records."""

    if expected is None:
        return []

    if isinstance(expected, tuple):
        return [expected]

    if isinstance(expected, list):
        if not expected:
            return []

        if isinstance(expected[0], (list, tuple)):
            return [tuple(record) for record in expected]

        return [tuple(expected)]

    raise TypeError(
        "Expected deck records must be a tuple, a list, or a list of tuples/lists"
    )


def _records_with_minimum_size(records, minimum_size):
    """Return records containing at least the requested entries."""

    return [record for record in records if len(record) >= minimum_size]


def _assert_keyword_records(
    data_file,
    keyword,
    expected,
    start=0,
):
    """Compare the requested entries from keyword records."""

    expected_records = _normalize_expected_records(expected)

    actual_records = _read_keyword_records(
        data_file,
        keyword,
    )

    if not expected_records:
        assert not actual_records, (
            f"{data_file}: expected no {keyword} records, " f"found {actual_records}"
        )
        return

    required_sizes = [start + len(record) for record in expected_records]

    minimum_size = min(required_sizes)

    suitable_records = _records_with_minimum_size(
        actual_records,
        minimum_size,
    )

    assert len(suitable_records) >= len(expected_records), (
        f"{data_file}: found {len(suitable_records)} suitable "
        f"{keyword} records, expected at least "
        f"{len(expected_records)}"
    )

    for index, expected_record in enumerate(expected_records):
        entry_count = len(expected_record)
        actual_record = suitable_records[index]

        assert len(actual_record) >= start + entry_count, (
            f"{data_file}: {keyword} record {index + 1} "
            f"contains {len(actual_record)} entries, but "
            f"{start + entry_count} are required"
        )

        actual = tuple(actual_record[start : start + entry_count])
        expected_values = tuple(expected_record)

        assert actual == expected_values, (
            f"{data_file}: {keyword} record {index + 1}, "
            f"entries {start + 1}-{start + entry_count} "
            f"are {actual}, expected {expected_values}"
        )


def assert_data_checks(data_file, reference):
    """Check selected values in a generated DATA file."""

    data_file = Path(data_file)

    assert data_file.is_file(), f"Missing DATA file: {data_file}"

    if "length" in reference:
        actual_length = len(data_file.read_text(encoding="utf8").splitlines())
        expected_length = reference["length"]

        assert actual_length == expected_length, (
            f"{data_file}: line count = {actual_length}, " f"expected {expected_length}"
        )

    if "faults" in reference:
        # Skip the fault name. Compare as many subsequent entries
        # as supplied. Supplying six values checks the six indices.
        _assert_keyword_records(
            data_file,
            "FAULTS",
            reference["faults"],
            start=1,
        )

    if "welspecs" in reference:
        # Start from entry 3 and compare as many entries as supplied.
        _assert_keyword_records(
            data_file,
            "WELSPECS",
            reference["welspecs"],
            start=2,
        )

    if "source" in reference:
        # Start from entry 3 and compare as many entries as supplied.
        _assert_keyword_records(
            data_file,
            "SOURCE",
            reference["source"],
            start=0,
        )

    if "compdat" in reference:
        # Start from entry 3 and compare as many entries as supplied.
        _assert_keyword_records(
            data_file,
            "COMPDAT",
            reference["compdat"],
            start=0,
        )

    if "compsegs" in reference:
        # Start from COMPSEGS entry 1 and compare as many entries
        # as supplied. Short header records are skipped.
        _assert_keyword_records(
            data_file,
            "COMPSEGS",
            reference["compsegs"],
            start=0,
        )


def assert_grid_and_init(
    egrid,
    init,
    dimensions,
    checks,
    exact_checks=None,
    active_cells=None,
    data_file=None,
    data_checks=None,
):
    """Check grid, INIT, and optional DATA-file regressions."""

    actual_dimensions = tuple(egrid.dimension)

    assert actual_dimensions == dimensions, (
        f"grid dimensions = {actual_dimensions}, " f"expected {dimensions}"
    )

    assert_init_checks(
        init,
        checks,
        exact_checks=exact_checks,
        active_cells=active_cells,
    )

    if data_checks is not None:
        assert (
            data_file is not None
        ), "data_file is required when data_checks is provided"

        assert_data_checks(
            data_file,
            data_checks,
        )


def assert_restart_preserved(
    reference,
    result,
    keyword,
    rstep=0,
    atol=50,
):
    """Check that a summed restart quantity is preserved."""

    ref = np.sum(reference[keyword, rstep])
    value = np.sum(result[keyword, rstep])

    assert value == pytest.approx(
        ref,
        abs=atol,
    ), (
        f"sum({keyword}) = {value}, " f"expected {ref}"
    )
