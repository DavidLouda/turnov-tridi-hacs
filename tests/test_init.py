"""Tests for the Turnov Třídí setup."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.turnov_tridi import async_setup
from custom_components.turnov_tridi.const import CARD_URL


async def test_card_is_served_and_registered(hass: HomeAssistant) -> None:
    """The card is served by the integration and loaded by the frontend."""
    hass.http = MagicMock(async_register_static_paths=AsyncMock())

    legacy_card = Path(
        hass.config.path("www/community/turnov_tridi/turnov-tridi-card.js")
    )
    legacy_card.parent.mkdir(parents=True)
    legacy_card.write_text("old card")

    with patch("custom_components.turnov_tridi.add_extra_js_url") as add_js:
        assert await async_setup(hass, {})

    (static_path,) = hass.http.async_register_static_paths.await_args.args[0]
    assert static_path.url_path == CARD_URL
    assert Path(static_path.path).is_file()
    add_js.assert_called_once()
    assert add_js.call_args.args[1].startswith(f"{CARD_URL}?v=")
    assert not legacy_card.parent.exists()
