"""Buttons for Sol- och batteriekonomi."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, MANUFACTURER, MODEL, CONF_NAME, DEFAULT_NAME
from .sensor import EconomyRuntime, _cfg


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    """Set up button platform."""
    runtime: EconomyRuntime = hass.data[DOMAIN][entry.entry_id]["runtime"]
    async_add_entities([InitialSettlementButton(runtime)])


class InitialSettlementButton(ButtonEntity, RestoreEntity):
    """One-time initial settlement button.

    ButtonEntity must be listed before RestoreEntity in newer Home Assistant
    versions to avoid MRO conflicts.
    """

    _attr_has_entity_name = True

    def __init__(self, runtime: EconomyRuntime) -> None:
        self.runtime = runtime
        cfg = _cfg(runtime.entry)
        self._attr_unique_id = f"{runtime.entry.entry_id}_initial_settlement_status"
        self._attr_name = "Kör engångsavräkning"
        self._attr_icon = "mdi:cash-check"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, runtime.entry.entry_id)},
            "name": cfg.get(CONF_NAME, DEFAULT_NAME),
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    async def async_added_to_hass(self) -> None:
        """Restore one-time settlement lock state."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self.runtime.restore_value("initial_settlement_status", 0.0, dict(last_state.attributes))

    @property
    def available(self) -> bool:
        """Button is unavailable after successful one-time settlement."""
        return not self.runtime.initial_settlement_done

    async def async_press(self) -> None:
        """Run initial settlement once."""
        if self.runtime.initial_settlement_done:
            return

        self.runtime.run_initial_settlement()
        self.async_write_ha_state()

        for entity in self.runtime.entities:
            entity.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose settlement status and calculation details."""
        attrs: dict[str, Any] = {
            "initial_settlement_done": self.runtime.initial_settlement_done,
            "locked_after_first_successful_run": True,
            "calculation": "producerad_solenergi - exporterad_energi = historisk_egenforbrukad_solel",
            "value_formula": "historisk_egenforbrukad_solel * (overforingsavgift + energiskatt) * moms",
        }

        if self.runtime.initial_settlement_time:
            attrs["initial_settlement_time"] = self.runtime.initial_settlement_time
        if self.runtime.initial_settlement_kwh is not None:
            attrs["initial_settlement_kwh"] = round(self.runtime.initial_settlement_kwh, 4)
        if self.runtime.initial_settlement_value is not None:
            attrs["initial_settlement_value"] = round(self.runtime.initial_settlement_value, 4)

        return attrs
