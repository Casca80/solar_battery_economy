"""Sol- och batteriekonomi integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_BUY_PRICE_ADJUSTMENT,
    CONF_SELL_PRICE_ADJUSTMENT,
    CONF_GRID_IMPORT_FIXED,
    CONF_ENERGY_TAX,
    CONF_GRID_BENEFIT_ENABLED,
    CONF_GRID_BENEFIT_FIXED_ORE,
    CONF_GRID_BENEFIT_SPOT_MULTIPLIER,
)


_GRID_BENEFIT_FIELDS = {
    CONF_GRID_BENEFIT_ENABLED,
    CONF_GRID_BENEFIT_FIXED_ORE,
    CONF_GRID_BENEFIT_SPOT_MULTIPLIER,
}


_LOGGER = logging.getLogger(__name__)


_ORE_FIELDS = {
    CONF_BUY_PRICE_ADJUSTMENT,
    CONF_SELL_PRICE_ADJUSTMENT,
    CONF_GRID_IMPORT_FIXED,
    CONF_ENERGY_TAX,
}


def _repair_possible_ore_values(data: dict) -> tuple[dict, bool]:
    """Repair values that older versions could store in the wrong unit."""
    changed = False
    fixed = dict(data)

    if "battery_roundtrip_efficiency" in fixed:
        fixed.pop("battery_roundtrip_efficiency", None)
        changed = True

    if CONF_GRID_BENEFIT_ENABLED in fixed:
        value = fixed.get(CONF_GRID_BENEFIT_ENABLED)
        if isinstance(value, str):
            fixed[CONF_GRID_BENEFIT_ENABLED] = value.lower() in ("true", "1", "yes", "ja", "on")
            changed = True

    for optional_key in (CONF_GRID_BENEFIT_FIXED_ORE, CONF_GRID_BENEFIT_SPOT_MULTIPLIER):
        if fixed.get(optional_key) == "":
            fixed.pop(optional_key, None)
            changed = True

    for key in _ORE_FIELDS:
        value = fixed.get(key)
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number > 2.0:
            fixed[key] = number / 100.0
            changed = True

    return fixed, changed


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    from .sensor import EconomyRuntime

    new_data, data_changed = _repair_possible_ore_values(entry.data)
    new_options, options_changed = _repair_possible_ore_values(entry.options)

    if data_changed or options_changed:
        hass.config_entries.async_update_entry(
            entry,
            data=new_data if data_changed else entry.data,
            options=new_options if options_changed else entry.options,
        )

    await _async_register_services(hass)

    runtime = EconomyRuntime(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"runtime": runtime}

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    entry.async_on_unload(runtime.disconnect)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    stored = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if stored and (runtime := stored.get("runtime")):
        runtime.disconnect()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options are changed."""
    stored = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if stored and (runtime := stored.get("runtime")):
        runtime.disconnect()
    await hass.config_entries.async_reload(entry.entry_id)


RESET_INITIAL_SETTLEMENT_SERVICE = "reset_initial_settlement"


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, RESET_INITIAL_SETTLEMENT_SERVICE):
        return

    async def _handle_reset_initial_settlement(call: ServiceCall) -> None:
        """Reset initial settlement for one or all loaded entries."""
        confirm = call.data.get("confirm")
        if confirm != "RESET":
            _LOGGER.warning("Reset initial settlement rejected. Missing confirm: RESET")
            return

        entry_id = call.data.get("entry_id")
        stored_entries = hass.data.get(DOMAIN, {})

        if entry_id:
            target_items = [(entry_id, stored_entries.get(entry_id))]
        else:
            target_items = list(stored_entries.items())

        for target_entry_id, stored in target_items:
            if not stored:
                continue

            runtime = stored.get("runtime")
            if runtime is None:
                continue

            runtime.reset_initial_settlement()

            for entry in hass.config_entries.async_entries(DOMAIN):
                if entry.entry_id != target_entry_id:
                    continue

                options = dict(entry.options)
                for key in (
                    CONF_INITIAL_SETTLEMENT_DONE,
                    CONF_INITIAL_SETTLEMENT_TIME,
                    CONF_INITIAL_SETTLEMENT_KWH,
                    CONF_INITIAL_SETTLEMENT_VALUE,
                ):
                    options.pop(key, None)

                hass.config_entries.async_update_entry(entry, options=options)
                break

    hass.services.async_register(
        DOMAIN,
        RESET_INITIAL_SETTLEMENT_SERVICE,
        _handle_reset_initial_settlement,
        schema=vol.Schema(
            {
                vol.Required("confirm"): str,
                vol.Optional("entry_id"): str,
            }
        ),
    )
