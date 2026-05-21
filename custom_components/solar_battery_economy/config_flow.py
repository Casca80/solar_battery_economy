"""Config flow for Sol- och batteriekonomi."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_IMPORT_ENERGY,
    CONF_EXPORT_ENERGY,
    CONF_HOME_CONSUMPTION_ENERGY,
    CONF_SOLAR_PRODUCTION_ENERGY,
    CONF_BATTERY_CHARGE_ENERGY,
    CONF_BATTERY_DISCHARGE_ENERGY,
    CONF_SPOT_PRICE,
    CONF_BUY_PRICE_MODE,
    CONF_BUY_PRICE_ADJUSTMENT,
    CONF_SELL_PRICE_MODE,
    CONF_SELL_PRICE_ADJUSTMENT,
    CONF_GRID_IMPORT_MODE,
    CONF_GRID_IMPORT_FIXED,
    CONF_GRID_IMPORT_PERCENT_OF_SPOT,
    CONF_ENERGY_TAX,
    CONF_VAT_PERCENT,
    CONF_EXPORT_VAT_PERCENT,
    CONF_INVESTMENT_COST,
    CONF_GRID_BENEFIT_FIXED_ORE,
    CONF_GRID_BENEFIT_SPOT_PERCENT,
    MODE_SPOT,
    MODE_SPOT_PLUS,
    MODE_SPOT_MINUS,
    MODE_FIXED,
    MODE_FIXED_PLUS_PERCENT_SPOT,
    DEFAULT_NAME,
    DEFAULT_BUY_PRICE_MODE,
    DEFAULT_SELL_PRICE_MODE,
    DEFAULT_GRID_IMPORT_MODE,
    DEFAULT_BUY_PRICE_ADJUSTMENT,
    DEFAULT_SELL_PRICE_ADJUSTMENT,
    DEFAULT_GRID_IMPORT_FIXED,
    DEFAULT_GRID_IMPORT_PERCENT_OF_SPOT,
    DEFAULT_ENERGY_TAX,
    DEFAULT_VAT_PERCENT,
    DEFAULT_EXPORT_VAT_PERCENT,
    DEFAULT_INVESTMENT_COST,
    DEFAULT_GRID_BENEFIT_FIXED_ORE,
    DEFAULT_GRID_BENEFIT_SPOT_PERCENT,
)


ORE_FIELDS = (
    CONF_BUY_PRICE_ADJUSTMENT,
    CONF_SELL_PRICE_ADJUSTMENT,
    CONF_GRID_IMPORT_FIXED,
    CONF_ENERGY_TAX,
)


def _entity_selector() -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))


def _price_mode_selector() -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                {"value": MODE_SPOT, "label": "Spotpris"},
                {"value": MODE_SPOT_PLUS, "label": "Spotpris + påslag"},
                {"value": MODE_SPOT_MINUS, "label": "Spotpris - avdrag"},
                {"value": MODE_FIXED, "label": "Fast pris"},
            ],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _grid_mode_selector() -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                {"value": MODE_FIXED, "label": "Fast öre/kWh"},
                {"value": MODE_FIXED_PLUS_PERCENT_SPOT, "label": "Fast öre/kWh + procent av spotpris"},
            ],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _sek_to_ore(value: Any) -> float:
    return round(float(value) * 100.0, 4)


def _ore_to_sek(value: Any) -> float:
    return float(value) / 100.0


def _display_defaults(defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    source = dict(defaults or {})
    result: dict[str, Any] = {
        CONF_NAME: source.get(CONF_NAME, DEFAULT_NAME),
        CONF_IMPORT_ENERGY: source.get(CONF_IMPORT_ENERGY),
        CONF_EXPORT_ENERGY: source.get(CONF_EXPORT_ENERGY),
        CONF_HOME_CONSUMPTION_ENERGY: source.get(CONF_HOME_CONSUMPTION_ENERGY),
        CONF_SOLAR_PRODUCTION_ENERGY: source.get(CONF_SOLAR_PRODUCTION_ENERGY),
        CONF_BATTERY_CHARGE_ENERGY: source.get(CONF_BATTERY_CHARGE_ENERGY),
        CONF_BATTERY_DISCHARGE_ENERGY: source.get(CONF_BATTERY_DISCHARGE_ENERGY),
        CONF_SPOT_PRICE: source.get(CONF_SPOT_PRICE),
        CONF_BUY_PRICE_MODE: source.get(CONF_BUY_PRICE_MODE, DEFAULT_BUY_PRICE_MODE),
        CONF_SELL_PRICE_MODE: source.get(CONF_SELL_PRICE_MODE, DEFAULT_SELL_PRICE_MODE),
        CONF_GRID_IMPORT_MODE: source.get(CONF_GRID_IMPORT_MODE, DEFAULT_GRID_IMPORT_MODE),
        CONF_GRID_IMPORT_PERCENT_OF_SPOT: source.get(CONF_GRID_IMPORT_PERCENT_OF_SPOT, DEFAULT_GRID_IMPORT_PERCENT_OF_SPOT),
        CONF_VAT_PERCENT: source.get(CONF_VAT_PERCENT, DEFAULT_VAT_PERCENT),
        CONF_EXPORT_VAT_PERCENT: source.get(CONF_EXPORT_VAT_PERCENT, DEFAULT_EXPORT_VAT_PERCENT),
        CONF_INVESTMENT_COST: source.get(CONF_INVESTMENT_COST, DEFAULT_INVESTMENT_COST),
        CONF_GRID_BENEFIT_FIXED_ORE: source.get(CONF_GRID_BENEFIT_FIXED_ORE, DEFAULT_GRID_BENEFIT_FIXED_ORE),
        CONF_GRID_BENEFIT_SPOT_PERCENT: source.get(CONF_GRID_BENEFIT_SPOT_PERCENT, DEFAULT_GRID_BENEFIT_SPOT_PERCENT),
    }

    stored_defaults = {
        CONF_BUY_PRICE_ADJUSTMENT: DEFAULT_BUY_PRICE_ADJUSTMENT,
        CONF_SELL_PRICE_ADJUSTMENT: DEFAULT_SELL_PRICE_ADJUSTMENT,
        CONF_GRID_IMPORT_FIXED: DEFAULT_GRID_IMPORT_FIXED,
        CONF_ENERGY_TAX: DEFAULT_ENERGY_TAX,
    }

    for key, default in stored_defaults.items():
        result[key] = _sek_to_ore(source.get(key, default))

    return result


def _normalise_input(user_input: dict[str, Any]) -> dict[str, Any]:
    data = dict(user_input)

    for key in ORE_FIELDS:
        if key in data and data[key] is not None:
            data[key] = _ore_to_sek(data[key])

    data.pop("battery_roundtrip_efficiency", None)
    return data


def _add_required_entity(schema: dict, key: str, defaults: dict[str, Any]) -> None:
    if defaults.get(key):
        schema[vol.Required(key, default=defaults[key])] = _entity_selector()
    else:
        schema[vol.Required(key)] = _entity_selector()


def _add_optional_entity(schema: dict, key: str, defaults: dict[str, Any]) -> None:
    if defaults.get(key):
        schema[vol.Optional(key, default=defaults[key])] = _entity_selector()
    else:
        schema[vol.Optional(key)] = _entity_selector()


def _number(min_value: float, max_value: float, step: float, unit: str) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=min_value,
            max=max_value,
            step=step,
            unit_of_measurement=unit,
            mode=selector.NumberSelectorMode.BOX,
        )
    )


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    d = _display_defaults(defaults)
    schema: dict[Any, Any] = {}

    schema[vol.Required(CONF_NAME, default=d[CONF_NAME])] = str

    _add_required_entity(schema, CONF_IMPORT_ENERGY, d)
    _add_required_entity(schema, CONF_EXPORT_ENERGY, d)
    _add_optional_entity(schema, CONF_HOME_CONSUMPTION_ENERGY, d)
    _add_required_entity(schema, CONF_SOLAR_PRODUCTION_ENERGY, d)
    _add_optional_entity(schema, CONF_BATTERY_CHARGE_ENERGY, d)
    _add_optional_entity(schema, CONF_BATTERY_DISCHARGE_ENERGY, d)
    _add_required_entity(schema, CONF_SPOT_PRICE, d)

    schema[vol.Required(CONF_BUY_PRICE_MODE, default=d[CONF_BUY_PRICE_MODE])] = _price_mode_selector()
    schema[vol.Required(CONF_BUY_PRICE_ADJUSTMENT, default=d[CONF_BUY_PRICE_ADJUSTMENT])] = _number(0, 1000, 0.1, "öre/kWh")

    schema[vol.Required(CONF_SELL_PRICE_MODE, default=d[CONF_SELL_PRICE_MODE])] = _price_mode_selector()
    schema[vol.Required(CONF_SELL_PRICE_ADJUSTMENT, default=d[CONF_SELL_PRICE_ADJUSTMENT])] = _number(0, 1000, 0.1, "öre/kWh")

    schema[vol.Required(CONF_GRID_IMPORT_MODE, default=d[CONF_GRID_IMPORT_MODE])] = _grid_mode_selector()
    schema[vol.Required(CONF_GRID_IMPORT_FIXED, default=d[CONF_GRID_IMPORT_FIXED])] = _number(0, 1000, 0.1, "öre/kWh")
    schema[vol.Required(CONF_GRID_IMPORT_PERCENT_OF_SPOT, default=d[CONF_GRID_IMPORT_PERCENT_OF_SPOT])] = _number(0, 100, 0.1, "%")
    schema[vol.Required(CONF_ENERGY_TAX, default=d[CONF_ENERGY_TAX])] = _number(0, 1000, 0.1, "öre/kWh")
    schema[vol.Required(CONF_VAT_PERCENT, default=d[CONF_VAT_PERCENT])] = _number(0, 100, 0.1, "%")
    schema[vol.Required(CONF_EXPORT_VAT_PERCENT, default=d[CONF_EXPORT_VAT_PERCENT])] = _number(0, 100, 0.1, "%")
    schema[vol.Required(CONF_INVESTMENT_COST, default=d[CONF_INVESTMENT_COST])] = _number(0, 10000000, 100, "SEK")
    schema[vol.Required(CONF_GRID_BENEFIT_FIXED_ORE, default=d[CONF_GRID_BENEFIT_FIXED_ORE])] = _number(0, 1000, 0.1, "öre/kWh")
    schema[vol.Required(CONF_GRID_BENEFIT_SPOT_PERCENT, default=d[CONF_GRID_BENEFIT_SPOT_PERCENT])] = _number(0, 100, 0.01, "%")

    return vol.Schema(schema)


class SolarBatteryEconomyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            data = _normalise_input(user_input)
            await self.async_set_unique_id("solar_battery_economy")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=data[CONF_NAME], data=data)

        return self.async_show_form(step_id="user", data_schema=_schema())

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return SolarBatteryEconomyOptionsFlow(config_entry)


class SolarBatteryEconomyOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        current = {**self._config_entry.data, **self._config_entry.options}

        if user_input is not None:
            return self.async_create_entry(title="", data=_normalise_input(user_input))

        return self.async_show_form(step_id="init", data_schema=_schema(current))
