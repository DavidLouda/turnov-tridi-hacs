"""Tests for the turnovtridi.cz response parser."""

from __future__ import annotations

from datetime import date

import pytest

from custom_components.turnov_tridi.api import TurnovTridiParseError, parse_response


def _row(day: str, css_class: str) -> str:
    return (
        "<tr>"
        f'<td><time datetime="{day}T12:00:00Z" class="datetime">{day}</time></td>'
        f'<td><span class="{css_class} "></span></td>'
        "</tr>"
    )


def _response(*rows: str) -> list[dict]:
    table = f"<table><tbody>{''.join(rows)}</tbody></table>"
    return [
        {"command": "settings", "settings": {}},
        {"command": "insert", "method": "replaceWith", "data": table},
    ]


def test_parse_response() -> None:
    """Rows are grouped by waste type, sorted and deduplicated."""
    result = parse_response(
        _response(
            _row("2026-03-24", "sko"),
            _row("2026-03-10", "sko"),
            _row("2026-03-11", "plast"),
            _row("2026-03-11", "papir"),
            _row("2026-03-11", "papir"),
            _row("2026-03-12", "unknown"),
        )
    )

    assert result == {
        "mixed_waste": [date(2026, 3, 10), date(2026, 3, 24)],
        "plastic": [date(2026, 3, 11)],
        "paper": [date(2026, 3, 11)],
        "bio_waste": [],
    }


def test_parse_empty_table() -> None:
    """A table without rows yields no dates."""
    assert not any(parse_response(_response()).values())


@pytest.mark.parametrize(
    "json_data",
    [[], [{"command": "settings"}], {"unexpected": "object"}, None],
)
def test_parse_missing_table(json_data) -> None:
    """A response without the schedule table is an error, not an empty schedule."""
    with pytest.raises(TurnovTridiParseError):
        parse_response(json_data)
