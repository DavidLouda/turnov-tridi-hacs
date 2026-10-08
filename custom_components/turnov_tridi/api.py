"""API client for turnovtridi.cz."""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any

import aiohttp

from .const import BASE_URL, WASTE_TYPES

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)

# Each row has: <time datetime="2026-02-18T12:00:00Z">, waste type class
ROW_PATTERN = re.compile(
    r'<time\s+datetime="(\d{4}-\d{2}-\d{2})T[^"]*"[^>]*>.*?</time>'
    r'.*?<span\s+class="(\w+)\s*">\s*</span>',
    re.DOTALL,
)


class TurnovTridiError(Exception):
    """Base error for the Turnov Třídí API."""


class TurnovTridiConnectionError(TurnovTridiError):
    """Error to indicate the server could not be reached."""


class TurnovTridiParseError(TurnovTridiError):
    """Error to indicate the response did not contain the schedule table."""


class TurnovTridiApi:
    """Client fetching the waste collection schedule for one street."""

    def __init__(self, session: aiohttp.ClientSession, street: str) -> None:
        """Initialize the API client."""
        self._session = session
        self.street = street

    async def async_get_schedule(self, from_date: date) -> dict[str, list[date]]:
        """Fetch collection dates (from the given date on) keyed by waste type."""
        params = {
            "_wrapper_format": "drupal_ajax",
            "combine": self.street,
            "field_datum_svozu_value": from_date.isoformat(),
            "view_name": "svoz_odpadu_turnov",
            "view_display_id": "block_1",
            "view_path": "/node/3",
            "view_base_path": "",
            "view_dom_id": "turnov_tridi_ha",
            "pager_element": "0",
            "_drupal_ajax": "1",
            "ajax_page_state[theme]": "turnovtridi",
            "ajax_page_state[theme_token]": "",
            "ajax_page_state[libraries]": "",
        }

        try:
            async with self._session.get(
                BASE_URL, params=params, timeout=REQUEST_TIMEOUT
            ) as response:
                response.raise_for_status()
                json_data = await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError, ValueError) as err:
            raise TurnovTridiConnectionError(
                f"Error communicating with turnovtridi.cz: {err}"
            ) from err

        result = parse_response(json_data)
        _LOGGER.debug(
            "Parsed %d collection events for street '%s'",
            sum(len(v) for v in result.values()),
            self.street,
        )
        return result


def parse_response(json_data: Any) -> dict[str, list[date]]:
    """Parse the Drupal AJAX JSON response into sorted dates per waste type.

    Raises TurnovTridiParseError when the response contains no schedule table.
    """
    html_content = ""
    if isinstance(json_data, list):
        for command in json_data:
            if isinstance(command, dict):
                data = command.get("data")
                if isinstance(data, str) and "<table" in data:
                    html_content = data
                    break

    if not html_content:
        raise TurnovTridiParseError("No table data found in API response")

    result: dict[str, list[date]] = {wt["key"]: [] for wt in WASTE_TYPES.values()}

    for match in ROW_PATTERN.finditer(html_content):
        date_str, waste_css_class = match.groups()
        if waste_css_class not in WASTE_TYPES:
            continue
        try:
            collection_date = date.fromisoformat(date_str)
        except ValueError:
            _LOGGER.warning("Invalid date format: %s", date_str)
            continue
        dates = result[WASTE_TYPES[waste_css_class]["key"]]
        if collection_date not in dates:
            dates.append(collection_date)

    for dates in result.values():
        dates.sort()

    return result
