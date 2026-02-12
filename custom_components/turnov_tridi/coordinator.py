"""Data update coordinator for Turnov Třídí."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import BASE_URL, DEFAULT_UPDATE_INTERVAL_HOURS, WASTE_TYPES

_LOGGER = logging.getLogger(__name__)


class TurnovTridiCoordinator(DataUpdateCoordinator[dict[str, list[date]]]):
    """Coordinator to fetch waste collection data from turnovtridi.cz."""

    def __init__(self, hass: HomeAssistant, street: str) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Turnov Třídí",
            update_interval=timedelta(hours=DEFAULT_UPDATE_INTERVAL_HOURS),
        )
        self.street = street

    async def _async_update_data(self) -> dict[str, list[date]]:
        """Fetch data from the API."""
        try:
            return await self._fetch_data()
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

    async def _fetch_data(self) -> dict[str, list[date]]:
        """Fetch and parse waste collection schedule."""
        today = date.today().isoformat()

        params = {
            "_wrapper_format": "drupal_ajax",
            "combine": self.street,
            "field_datum_svozu_value": today,
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

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(BASE_URL, params=params) as response:
                response.raise_for_status()
                json_data = await response.json(content_type=None)

        return self._parse_response(json_data)

    def _parse_response(self, json_data: list[dict[str, Any]]) -> dict[str, list[date]]:
        """Parse the Drupal AJAX JSON response into structured data."""
        result: dict[str, list[date]] = {
            wt["key"]: [] for wt in WASTE_TYPES.values()
        }

        # Find the command containing the HTML table data
        html_content = ""
        for command in json_data:
            if isinstance(command, dict) and command.get("data"):
                data = command["data"]
                if isinstance(data, str) and "<table" in data:
                    html_content = data
                    break

        if not html_content:
            _LOGGER.warning("No table data found in API response")
            return result

        # Parse table rows using regex
        # Each row has: <time datetime="2026-02-18T12:00:00Z">, waste type class
        row_pattern = re.compile(
            r'<time\s+datetime="(\d{4}-\d{2}-\d{2})T[^"]*"[^>]*>.*?</time>'
            r'.*?<span\s+class="(\w+)\s*">\s*</span>',
            re.DOTALL,
        )

        for match in row_pattern.finditer(html_content):
            date_str = match.group(1)
            waste_css_class = match.group(2)

            if waste_css_class in WASTE_TYPES:
                try:
                    collection_date = date.fromisoformat(date_str)
                    waste_key = WASTE_TYPES[waste_css_class]["key"]
                    result[waste_key].append(collection_date)
                except ValueError:
                    _LOGGER.warning("Invalid date format: %s", date_str)

        # Sort dates for each waste type
        for key in result:
            result[key].sort()

        _LOGGER.debug(
            "Parsed %d collection events for street '%s'",
            sum(len(v) for v in result.values()),
            self.street,
        )

        return result
