"""Sensors for Sol- och batteriekonomi."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import logging
from typing import Any, Callable

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import StateType

from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL,
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
    CONF_INITIAL_SETTLEMENT_DONE,
    CONF_INITIAL_SETTLEMENT_TIME,
    CONF_INITIAL_SETTLEMENT_KWH,
    CONF_INITIAL_SETTLEMENT_VALUE,
    CONF_GRID_BENEFIT_ENABLED,
    CONF_GRID_BENEFIT_FIXED_ORE,
    CONF_GRID_BENEFIT_SPOT_PERCENT,
    CONF_GRID_BENEFIT_SPOT_MULTIPLIER,
    MODE_SPOT,
    MODE_SPOT_PLUS,
    MODE_SPOT_MINUS,
    MODE_FIXED,
    MODE_FIXED_PLUS_PERCENT_SPOT,
    DEFAULT_NAME,
    DEFAULT_BUY_PRICE_MODE,
    DEFAULT_SELL_PRICE_MODE,
    DEFAULT_GRID_IMPORT_MODE,
    DEFAULT_GRID_IMPORT_FIXED,
    DEFAULT_GRID_IMPORT_PERCENT_OF_SPOT,
    DEFAULT_ENERGY_TAX,
    DEFAULT_VAT_PERCENT,
    DEFAULT_EXPORT_VAT_PERCENT,
    DEFAULT_INVESTMENT_COST,
    DEFAULT_GRID_BENEFIT_ENABLED,
    DEFAULT_GRID_BENEFIT_FIXED_ORE,
    DEFAULT_GRID_BENEFIT_SPOT_PERCENT,
    DEFAULT_GRID_BENEFIT_SPOT_MULTIPLIER,
    LARGE_DELTA_WARNING_KWH,
)

_LOGGER = logging.getLogger(__name__)

CURRENCY = "SEK"
PRICE_UNIT = "SEK/kWh"
PERCENTAGE = "%"


def _state_and_unit(hass: HomeAssistant, entity_id: str | None) -> tuple[float | None, str | None]:
    if not entity_id:
        return None, None
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unknown", "unavailable", None):
        return None, None
    try:
        value = float(str(state.state).replace(",", "."))
    except (TypeError, ValueError):
        return None, state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
    return value, state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)


def _normalise_unit(unit: str | None) -> str:
    return (unit or "").strip().lower().replace(" ", "").replace("å", "a")


def _energy_to_kwh(value: float | None, unit: str | None) -> float | None:
    if value is None:
        return None
    u = _normalise_unit(unit)
    if u == "wh":
        return value / 1000.0
    if u in ("kwh", "kw·h"):
        return value
    if u == "mwh":
        return value * 1000.0
    return None


def _price_to_sek_per_kwh(value: float | None, unit: str | None) -> float | None:
    if value is None:
        return None
    u = _normalise_unit(unit)
    if u in ("sek/kwh", "kr/kwh"):
        return value
    if u in ("ore/kwh", "öre/kwh"):
        return value / 100.0
    if u in ("sek/mwh", "kr/mwh"):
        return value / 1000.0
    if u in ("ore/wh", "öre/wh"):
        return value * 10.0
    return None


def _normalised_energy_state(hass: HomeAssistant, entity_id: str | None) -> float | None:
    raw, unit = _state_and_unit(hass, entity_id)
    return _energy_to_kwh(raw, unit)


def _candidate_entity_ids(configured: str | None, fallbacks: tuple[str, ...]) -> list[str]:
    """Return configured entity first, then useful fallback entity ids."""
    candidates: list[str] = []
    for entity_id in (configured, *fallbacks):
        if entity_id and entity_id not in candidates:
            candidates.append(entity_id)
    return candidates


def _normalised_battery_energy_state(
    hass: HomeAssistant,
    configured_entity_id: str | None,
    fallbacks: tuple[str, ...],
) -> tuple[float | None, str | None, str | None]:
    """Read a battery energy meter, with fallback for common power-vs-energy mixups."""
    first_unit: str | None = None
    for entity_id in _candidate_entity_ids(configured_entity_id, fallbacks):
        raw, unit = _state_and_unit(hass, entity_id)
        if first_unit is None and unit is not None:
            first_unit = unit
        value = _energy_to_kwh(raw, unit)
        if value is not None:
            return value, entity_id, unit
    return None, None, first_unit


def _normalised_price_state(hass: HomeAssistant, entity_id: str | None) -> float | None:
    raw, unit = _state_and_unit(hass, entity_id)
    return _price_to_sek_per_kwh(raw, unit)


def _cfg(entry: ConfigEntry) -> dict[str, Any]:
    return {**entry.data, **entry.options}


def _price(mode: str, spot: float, adjustment: float) -> float:
    if mode == MODE_SPOT:
        return spot
    if mode == MODE_SPOT_PLUS:
        return spot + adjustment
    if mode == MODE_SPOT_MINUS:
        return spot - adjustment
    if mode == MODE_FIXED:
        return adjustment
    return spot


PERIOD_METRICS = {
    "import_cost": "Importkostnad",
    "export_revenue": "Exportintäkt",
    "grid_benefit": "Nätnytta",
    "self_consumed_value": "Värde egenförbrukad solel",
    "net_result": "Ekonomisk nytta",
}

# Nätnytta ackumuleras internt i v0.3.16 men exponeras inte som egna sensorer ännu.
VISIBLE_PERIOD_METRICS = {
    "import_cost": "Importkostnad",
    "export_revenue": "Exportintäkt",
    "grid_benefit": "Nätnytta",
    "self_consumed_value": "Värde egenförbrukad solel",
    "net_result": "Ekonomisk nytta",
}


class PriceCalculator:
    """Calculate current contract prices."""

    def __init__(self, runtime: "EconomyRuntime") -> None:
        self.runtime = runtime
        self.current: dict[str, float] = {}

    def recalculate(self, cfg: dict[str, Any]) -> None:
        spot = _normalised_price_state(self.runtime.hass, cfg.get(CONF_SPOT_PRICE)) or 0.0
        buy_energy = _price(cfg.get(CONF_BUY_PRICE_MODE, DEFAULT_BUY_PRICE_MODE), spot, float(cfg.get(CONF_BUY_PRICE_ADJUSTMENT, 0)))
        sell_energy = _price(cfg.get(CONF_SELL_PRICE_MODE, DEFAULT_SELL_PRICE_MODE), spot, float(cfg.get(CONF_SELL_PRICE_ADJUSTMENT, 0)))

        grid = float(cfg.get(CONF_GRID_IMPORT_FIXED, DEFAULT_GRID_IMPORT_FIXED))
        if cfg.get(CONF_GRID_IMPORT_MODE, DEFAULT_GRID_IMPORT_MODE) == MODE_FIXED_PLUS_PERCENT_SPOT:
            grid += spot * float(cfg.get(CONF_GRID_IMPORT_PERCENT_OF_SPOT, DEFAULT_GRID_IMPORT_PERCENT_OF_SPOT)) / 100.0

        tax = float(cfg.get(CONF_ENERGY_TAX, DEFAULT_ENERGY_TAX))
        vat = float(cfg.get(CONF_VAT_PERCENT, DEFAULT_VAT_PERCENT)) / 100.0
        export_vat = float(cfg.get(CONF_EXPORT_VAT_PERCENT, DEFAULT_EXPORT_VAT_PERCENT)) / 100.0
        buy_total = (buy_energy + grid + tax) * (1.0 + vat)
        sell_total = sell_energy * (1.0 + export_vat)

        # Nätnytta, samma princip som överföringsavgift:
        # fast öre/kWh + procent av aktuellt spotpris.
        grid_benefit_fixed_ore = float(cfg.get(CONF_GRID_BENEFIT_FIXED_ORE, DEFAULT_GRID_BENEFIT_FIXED_ORE) or 0.0)
        grid_benefit_spot_percent = float(cfg.get(CONF_GRID_BENEFIT_SPOT_PERCENT, DEFAULT_GRID_BENEFIT_SPOT_PERCENT) or 0.0)
        spot_ore = spot * 100.0
        grid_benefit_ore_per_kwh = grid_benefit_fixed_ore + (grid_benefit_spot_percent / 100.0 * spot_ore)
        grid_benefit_price = (grid_benefit_ore_per_kwh / 100.0) * (1.0 + export_vat)

        self.current = {
            "spot": spot,
            "buy_energy": buy_energy,
            "grid_import": grid,
            "energy_tax": tax,
            "vat_factor": vat,
            "export_vat_factor": export_vat,
            "buy_total": buy_total,
            "sell_energy": sell_energy,
            "sell_price": sell_total,
            "grid_benefit_fixed_ore": grid_benefit_fixed_ore,
            "grid_benefit_spot_percent": grid_benefit_spot_percent,
            "grid_benefit_price": grid_benefit_price,
        }


class EconomyRuntime:
    """Shared runtime calculator for one config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.entities: list[EconomySensor] = []
        self.last_energy: dict[str, float] = {}
        self.pending_solar_production_delta_kwh: float = 0.0
        self.values: dict[str, float] = {}

        for metric in PERIOD_METRICS:
            self.values[f"{metric}_today"] = 0.0
            self.values[f"{metric}_month"] = 0.0
            self.values[f"{metric}_total"] = 0.0

        self.price_calculator = PriceCalculator(self)
        self.unit_warnings: list[str] = []
        self.ignored_sensors: list[str] = []
        self.delta_warnings: list[str] = []
        self.current_date = date.today().isoformat()
        self.current_month = date.today().strftime("%Y-%m")

        cfg = _cfg(entry)
        self.initial_settlement_done = bool(cfg.get(CONF_INITIAL_SETTLEMENT_DONE, False))
        self.initial_settlement_time: str | None = cfg.get(CONF_INITIAL_SETTLEMENT_TIME)
        self.initial_settlement_kwh: float | None = self._optional_float(cfg.get(CONF_INITIAL_SETTLEMENT_KWH))
        self.initial_settlement_value: float | None = self._optional_float(cfg.get(CONF_INITIAL_SETTLEMENT_VALUE))
        self.initial_settlement_last_result: str | None = None
        self.initial_settlement_last_error: str | None = None

        self._unsub = None

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        try:
            if value is None or value == "":
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @property
    def current_prices(self) -> dict[str, float]:
        return self.price_calculator.current

    def disconnect(self) -> None:
        """Remove HA listeners owned by this runtime."""
        if self._unsub:
            self._unsub()
            self._unsub = None

    def attach(self, entity: "EconomySensor") -> None:
        self.entities.append(entity)

    def restore_value(self, key: str, value: float, attrs: dict[str, Any]) -> None:
        if key == "initial_settlement_status":
            # Config entry options are the primary source from v0.3.20 onward.
            # RestoreEntity attributes must not lock an entry after the saved
            # options have been reset.
            return

        if key.endswith("_today"):
            if attrs.get("calculation_date") == self.current_date:
                self.values[key] = value
            return

        if key.endswith("_month"):
            if attrs.get("calculation_month") == self.current_month:
                self.values[key] = value
            return

        if key.endswith("_total"):
            self.values[key] = value
            return

    def restore_initial_settlement(self, attrs: dict[str, Any]) -> None:
        raw_done = attrs.get("initial_settlement_done", False)
        done = raw_done if isinstance(raw_done, bool) else str(raw_done).lower() in ("true", "1", "yes", "ja", "on")
        if not done:
            return

        self.initial_settlement_done = True
        self.initial_settlement_time = attrs.get("initial_settlement_time")
        try:
            if attrs.get("initial_settlement_kwh") is not None:
                self.initial_settlement_kwh = float(attrs.get("initial_settlement_kwh"))
            if attrs.get("initial_settlement_value") is not None:
                self.initial_settlement_value = float(attrs.get("initial_settlement_value"))
        except (TypeError, ValueError):
            _LOGGER.warning("Could not restore initial settlement attributes")

    def run_initial_settlement(self) -> tuple[bool, str]:
        self.initial_settlement_last_error = None

        if self.initial_settlement_done:
            msg = "Engångsavräkning är redan utförd."
            self.initial_settlement_last_result = msg
            return False, msg

        cfg = _cfg(self.entry)
        self._calculate_current_prices(cfg)

        produced = _normalised_energy_state(self.hass, cfg.get(CONF_SOLAR_PRODUCTION_ENERGY))
        exported = _normalised_energy_state(self.hass, cfg.get(CONF_EXPORT_ENERGY))

        if produced is None or exported is None:
            msg = "Saknar giltig solproduktions- eller exportmätare."
            self.initial_settlement_last_error = msg
            self.initial_settlement_last_result = msg
            self._schedule_entities()
            return False, msg

        historical_self_consumed_kwh = max(0.0, produced - exported)
        if historical_self_consumed_kwh <= 0:
            msg = "Beräknad historisk egenförbrukning är 0 kWh eller negativ."
            self.initial_settlement_last_error = msg
            self.initial_settlement_last_result = msg
            self._schedule_entities()
            return False, msg

        fixed_grid_import = float(cfg.get(CONF_GRID_IMPORT_FIXED, DEFAULT_GRID_IMPORT_FIXED) or 0.0)
        tax = float(cfg.get(CONF_ENERGY_TAX, DEFAULT_ENERGY_TAX) or 0.0)
        vat = float(cfg.get(CONF_VAT_PERCENT, DEFAULT_VAT_PERCENT) or 0.0) / 100.0
        settlement_value = historical_self_consumed_kwh * (fixed_grid_import + tax) * (1.0 + vat)

        self.values["self_consumed_value_total"] += settlement_value
        self._recalculate_net_result()

        from datetime import datetime
        self.initial_settlement_done = True
        self.initial_settlement_time = datetime.now().isoformat(timespec="seconds")
        self.initial_settlement_kwh = historical_self_consumed_kwh
        self.initial_settlement_value = settlement_value
        self.initial_settlement_last_result = "Engångsavräkning utförd."

        self._persist_initial_settlement()
        self._schedule_entities()

        return True, "Engångsavräkning utförd."

    def _persist_initial_settlement(self) -> None:
        options = dict(self.entry.options)
        options[CONF_INITIAL_SETTLEMENT_DONE] = self.initial_settlement_done
        options[CONF_INITIAL_SETTLEMENT_TIME] = self.initial_settlement_time
        options[CONF_INITIAL_SETTLEMENT_KWH] = self.initial_settlement_kwh
        options[CONF_INITIAL_SETTLEMENT_VALUE] = self.initial_settlement_value
        self.hass.config_entries.async_update_entry(self.entry, options=options)

    def reset_initial_settlement(self) -> None:
        """Reset initial settlement and remove its value from totals."""
        if self.initial_settlement_value:
            self.values["self_consumed_value_total"] = max(
                0.0,
                self.values.get("self_consumed_value_total", 0.0) - self.initial_settlement_value,
            )
            self._recalculate_net_result()

        self.initial_settlement_done = False
        self.initial_settlement_time = None
        self.initial_settlement_kwh = None
        self.initial_settlement_value = None
        self.initial_settlement_last_result = "Engångsavräkning nollställd."
        self.initial_settlement_last_error = None
        self._schedule_entities()

    async def async_start(self) -> None:
        cfg = _cfg(self.entry)
        watched = [
            cfg.get(CONF_IMPORT_ENERGY),
            cfg.get(CONF_EXPORT_ENERGY),
            cfg.get(CONF_SOLAR_PRODUCTION_ENERGY),
            cfg.get(CONF_HOME_CONSUMPTION_ENERGY),
            cfg.get(CONF_BATTERY_CHARGE_ENERGY),
            cfg.get(CONF_BATTERY_DISCHARGE_ENERGY),
            cfg.get(CONF_SPOT_PRICE),
        ]
        watched = [x for x in watched if x]

        for ent in watched:
            if ent == cfg.get(CONF_SPOT_PRICE):
                continue
            val = _normalised_energy_state(self.hass, ent)
            if val is not None:
                self.last_energy[ent] = val

        self._calculate_current_prices(cfg)
        self._unsub = async_track_state_change_event(self.hass, watched, self._handle_state_change)

    @callback
    def _handle_state_change(self, event: Event) -> None:
        self._check_period_rollover()
        cfg = _cfg(self.entry)
        self._calculate_current_prices(cfg)
        entity_id = event.data.get("entity_id")

        if not entity_id:
            return

        if entity_id == cfg.get(CONF_SPOT_PRICE):
            self._schedule_entities()
            return

        new_val = _normalised_energy_state(self.hass, entity_id)
        if new_val is None:
            self._schedule_entities()
            return

        old_val = self.last_energy.get(entity_id)
        self.last_energy[entity_id] = new_val
        if old_val is None:
            self._schedule_entities()
            return

        delta_kwh = new_val - old_val
        if delta_kwh <= 0:
            self._schedule_entities()
            return

        if delta_kwh > LARGE_DELTA_WARNING_KWH:
            msg = (
                f"{entity_id} ökade med {delta_kwh:.3f} kWh sedan senaste giltiga värde. "
                "Delta accepteras men bör kontrolleras mot historik/faktura."
            )
            _LOGGER.warning(msg)
            self.delta_warnings.append(msg)
            self.delta_warnings = self.delta_warnings[-5:]

        buy_total = self.current_prices.get("buy_total", 0.0)
        sell_price = self.current_prices.get("sell_price", 0.0)

        if entity_id == cfg.get(CONF_IMPORT_ENERGY):
            self._add_period_metric("import_cost", delta_kwh * buy_total)

        elif entity_id == cfg.get(CONF_HOME_CONSUMPTION_ENERGY):
            self._add_period_metric("self_consumed_value", delta_kwh * buy_total)

        elif entity_id == cfg.get(CONF_SOLAR_PRODUCTION_ENERGY) and not cfg.get(CONF_HOME_CONSUMPTION_ENERGY):
            # Produktion kan komma före eller efter motsvarande exportuppdatering.
            # Vi buffrar därför producerad energi och räknar värde av egenförbrukning
            # som producerad energi minus exporterad energi.
            self.pending_solar_production_delta_kwh += delta_kwh

        elif entity_id == cfg.get(CONF_EXPORT_ENERGY):
            self._add_period_metric("export_revenue", delta_kwh * sell_price)
            grid_benefit_price = self.current_prices.get("grid_benefit_price", 0.0)
            if grid_benefit_price:
                self._add_period_metric("grid_benefit", delta_kwh * grid_benefit_price)

            if not cfg.get(CONF_HOME_CONSUMPTION_ENERGY) and self.pending_solar_production_delta_kwh > 0:
                self_consumed_delta = max(0.0, self.pending_solar_production_delta_kwh - delta_kwh)
                if self_consumed_delta > 0:
                    self._add_period_metric("self_consumed_value", self_consumed_delta * buy_total)
                self.pending_solar_production_delta_kwh = 0.0

        self._recalculate_net_result()
        self._schedule_entities()

    def _check_period_rollover(self) -> None:
        today = date.today().isoformat()
        month = date.today().strftime("%Y-%m")
        if today != self.current_date:
            self.current_date = today
            for key in list(self.values):
                if key.endswith("_today"):
                    self.values[key] = 0.0
        if month != self.current_month:
            self.current_month = month
            for key in list(self.values):
                if key.endswith("_month"):
                    self.values[key] = 0.0

    def _add_period_metric(self, metric: str, amount: float) -> None:
        self.values[f"{metric}_today"] += amount
        self.values[f"{metric}_month"] += amount
        self.values[f"{metric}_total"] += amount

    def _recalculate_net_result(self) -> None:
        for suffix in ("today", "month", "total"):
            self.values[f"net_result_{suffix}"] = (
                self.values.get(f"export_revenue_{suffix}", 0.0)
                + self.values.get(f"grid_benefit_{suffix}", 0.0)
                + self.values.get(f"self_consumed_value_{suffix}", 0.0)
            )

    def battery_efficiency(self) -> float | None:
        cfg = _cfg(self.entry)
        charge, _, _ = _normalised_battery_energy_state(
            self.hass,
            cfg.get(CONF_BATTERY_CHARGE_ENERGY),
            ("sensor.rembattery_charge", "sensor.battery_charge"),
        )
        discharge, _, _ = _normalised_battery_energy_state(
            self.hass,
            cfg.get(CONF_BATTERY_DISCHARGE_ENERGY),
            ("sensor.rembattery_discharge", "sensor.battery_discharge"),
        )

        if charge is None or discharge is None or charge <= 0:
            return None

        efficiency = discharge / charge
        if efficiency <= 0:
            return None

        # Direct calculation from the selected input sensors.
        # Do not clamp or reject values above 100 %, because some integrations expose
        # battery charge/discharge meters with different historical baselines.
        # If the result is above 100 %, expose it and show diagnostics in attributes.
        return efficiency

    def _calculate_current_prices(self, cfg: dict[str, Any]) -> None:
        self.price_calculator.recalculate(cfg)
        self._update_unit_warnings(cfg)

    def _update_unit_warnings(self, cfg: dict[str, Any]) -> None:
        checks = [
            (cfg.get(CONF_IMPORT_ENERGY), "energy", True),
            (cfg.get(CONF_EXPORT_ENERGY), "energy", True),
            (cfg.get(CONF_SOLAR_PRODUCTION_ENERGY), "energy", True),
            (cfg.get(CONF_HOME_CONSUMPTION_ENERGY), "energy", False),
            (cfg.get(CONF_SPOT_PRICE), "price", True),
        ]

        warnings: list[str] = []
        ignored: list[str] = []
        for entity_id, expected, required in checks:
            if not entity_id:
                if required:
                    warnings.append(f"Obligatorisk sensor saknas för {expected}.")
                continue
            raw, unit = _state_and_unit(self.hass, entity_id)
            if raw is None:
                continue
            u = _normalise_unit(unit)
            valid_energy = expected == "energy" and u in ("wh", "kwh", "kw·h", "mwh")
            valid_price = expected == "price" and u in ("sek/kwh", "kr/kwh", "ore/kwh", "öre/kwh", "sek/mwh", "kr/mwh", "ore/wh", "öre/wh")
            if not (valid_energy or valid_price):
                warnings.append(f"{entity_id} har okänd enhet '{unit}'. Värdet ignoreras tills enheten stöds.")
                ignored.append(entity_id)

        self.unit_warnings = warnings
        self.ignored_sensors = ignored

    def data_quality_state(self) -> str:
        cfg = _cfg(self.entry)
        required = [
            cfg.get(CONF_IMPORT_ENERGY),
            cfg.get(CONF_EXPORT_ENERGY),
            cfg.get(CONF_SOLAR_PRODUCTION_ENERGY),
            cfg.get(CONF_SPOT_PRICE),
        ]
        if any(not x for x in required):
            return "Fel"

        has_unit_warnings = len(self.unit_warnings) > 0
        has_ignored_sensors = len(self.ignored_sensors) > 0
        has_delta_warnings = len(self.delta_warnings) > 0

        if has_unit_warnings or has_ignored_sensors or has_delta_warnings:
            return "Varning"

        return "OK"

    @callback
    def _schedule_entities(self) -> None:
        for entity in self.entities:
            entity.async_write_ha_state()


@dataclass(frozen=True)
class SensorDescription:
    key: str
    name: str
    unit: str | None
    device_class: SensorDeviceClass | None
    state_class: SensorStateClass | None
    value_fn: Callable[[EconomyRuntime], Any]


def _investment_cost(runtime: EconomyRuntime) -> float:
    cfg = _cfg(runtime.entry)
    return float(cfg.get(CONF_INVESTMENT_COST, DEFAULT_INVESTMENT_COST) or 0.0)


def _remaining_investment(runtime: EconomyRuntime) -> float | None:
    investment = _investment_cost(runtime)
    if investment <= 0:
        return None
    return investment - runtime.values.get("net_result_total", 0.0)


def _roi(runtime: EconomyRuntime) -> float | None:
    investment = _investment_cost(runtime)
    if investment <= 0:
        return None
    return runtime.values.get("net_result_total", 0.0) / investment * 100.0


def _battery_efficiency_percent(runtime: EconomyRuntime) -> float | None:
    efficiency = runtime.battery_efficiency()
    if efficiency is None:
        return None
    return efficiency * 100.0


def _build_sensors(entry: ConfigEntry) -> list[SensorDescription]:
    sensors: list[SensorDescription] = [
        SensorDescription("current_buy_price", "Aktuellt köppris totalt", PRICE_UNIT, None, SensorStateClass.MEASUREMENT, lambda r: r.current_prices.get("buy_total")),
        SensorDescription("current_sell_price", "Aktuell ersättning såld el", PRICE_UNIT, None, SensorStateClass.MEASUREMENT, lambda r: r.current_prices.get("sell_price")),
        SensorDescription("current_grid_import_fee", "Aktuell överföringsavgift", PRICE_UNIT, None, SensorStateClass.MEASUREMENT, lambda r: r.current_prices.get("grid_import")),
        SensorDescription("current_grid_benefit", "Aktuell nätnytta", PRICE_UNIT, None, SensorStateClass.MEASUREMENT, lambda r: r.current_prices.get("grid_benefit_price")),
        SensorDescription("battery_efficiency", "Verkningsgrad batteri", PERCENTAGE, None, SensorStateClass.MEASUREMENT, _battery_efficiency_percent),
        SensorDescription("data_quality", "Datakvalitet", None, None, None, lambda r: r.data_quality_state()),
        SensorDescription("initial_settlement_status", "Engångsavräkning", None, None, None, lambda r: "Utförd" if r.initial_settlement_done else "Ej utförd"),
    ]

    for metric, name in VISIBLE_PERIOD_METRICS.items():
        sensors.extend(
            [
                SensorDescription(f"{metric}_today", f"{name} idag", CURRENCY, SensorDeviceClass.MONETARY, SensorStateClass.TOTAL, lambda r, k=f"{metric}_today": r.values.get(k)),
                SensorDescription(f"{metric}_month", f"{name} denna månad", CURRENCY, SensorDeviceClass.MONETARY, SensorStateClass.TOTAL, lambda r, k=f"{metric}_month": r.values.get(k)),
                SensorDescription(f"{metric}_total", f"{name} total", CURRENCY, SensorDeviceClass.MONETARY, SensorStateClass.TOTAL, lambda r, k=f"{metric}_total": r.values.get(k)),
            ]
        )

    if float(_cfg(entry).get(CONF_INVESTMENT_COST, DEFAULT_INVESTMENT_COST) or 0.0) > 0:
        sensors.extend(
            [
                SensorDescription("remaining_investment", "Kvarvarande investering", CURRENCY, SensorDeviceClass.MONETARY, None, _remaining_investment),
                SensorDescription("roi_percent", "ROI procent", PERCENTAGE, None, SensorStateClass.MEASUREMENT, _roi),
            ]
        )

    return sensors


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    stored = hass.data[DOMAIN][entry.entry_id]
    runtime: EconomyRuntime = stored["runtime"]

    entities = [EconomySensor(runtime, desc) for desc in _build_sensors(entry)]
    for ent in entities:
        runtime.attach(ent)

    async_add_entities(entities)
    await runtime.async_start()


class EconomySensor(RestoreEntity, SensorEntity):
    """Economy sensor with restore support."""

    _attr_has_entity_name = True

    def __init__(self, runtime: EconomyRuntime, description: SensorDescription) -> None:
        self.runtime = runtime
        self.description = description
        cfg = _cfg(runtime.entry)
        self._attr_unique_id = f"{runtime.entry.entry_id}_{description.key}"
        self._attr_name = description.name
        self._attr_native_unit_of_measurement = description.unit
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class
        self._attr_device_info = {
            "identifiers": {(DOMAIN, runtime.entry.entry_id)},
            "name": cfg.get(CONF_NAME, DEFAULT_NAME),
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is None or last_state.state in ("unknown", "unavailable"):
            return
        try:
            value = float(str(last_state.state).replace(",", "."))
        except (TypeError, ValueError):
            value = 0.0
        self.runtime.restore_value(self.description.key, value, dict(last_state.attributes))

    @property
    def native_value(self) -> StateType:
        value = self.description.value_fn(self.runtime)
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return round(value, 4)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            "calculation_date": self.runtime.current_date,
            "calculation_month": self.runtime.current_month,
            "restore_protected": self.description.key.endswith("_total"),
        }

        if self.description.key == "data_quality":
            state = self.runtime.data_quality_state()
            attrs["unit_warnings"] = self.runtime.unit_warnings
            attrs["ignored_sensors"] = self.runtime.ignored_sensors
            attrs["delta_warnings"] = self.runtime.delta_warnings
            attrs["pending_solar_production_delta_kwh"] = round(self.runtime.pending_solar_production_delta_kwh, 4)

            if state == "OK":
                attrs["status_reason"] = "Inga aktiva varningar. Pending solar production delta är endast diagnostik."
            elif state == "Varning":
                attrs["status_reason"] = "Minst en aktiv unit_warning, ignored_sensor eller delta_warning finns."
            else:
                attrs["status_reason"] = "En obligatorisk sensor saknas i konfigurationen."

            return attrs

        if self.description.key == "initial_settlement_status":
            attrs["initial_settlement_done"] = self.runtime.initial_settlement_done
            attrs["initial_settlement_time"] = self.runtime.initial_settlement_time
            attrs["initial_settlement_kwh"] = self.runtime.initial_settlement_kwh
            attrs["initial_settlement_value"] = self.runtime.initial_settlement_value
            attrs["last_result"] = self.runtime.initial_settlement_last_result
            attrs["last_error"] = self.runtime.initial_settlement_last_error
            attrs["storage_source"] = "config_entry_options"
            attrs["calculation"] = "producerad_solenergi - exporterad_energi = historisk_egenforbrukad_solel"
            attrs["value_formula"] = "historisk_egenforbrukad_solel * (fast_overforingsavgift + energiskatt) * moms"
            attrs["reset_service"] = "solar_battery_economy.reset_initial_settlement"
            attrs["reset_requires"] = 'confirm: "RESET"'
            return attrs

        if self.description.key.startswith("current_") or self.description.key in {
            "import_cost_today",
            "import_cost_month",
            "import_cost_total",
            "export_revenue_today",
            "export_revenue_month",
            "export_revenue_total",
            "grid_benefit_today",
            "grid_benefit_month",
            "grid_benefit_total",
            "self_consumed_value_today",
            "self_consumed_value_month",
            "self_consumed_value_total",
            "net_result_today",
            "net_result_month",
            "net_result_total",
        }:
            attrs.update(
                {
                    "normalised_energy_unit": "kWh",
                    "normalised_price_unit": "SEK/kWh",
                    "spot_price": round(self.runtime.current_prices.get("spot", 0.0), 4),
                    "buy_energy_price": round(self.runtime.current_prices.get("buy_energy", 0.0), 4),
                    "grid_import_fee": round(self.runtime.current_prices.get("grid_import", 0.0), 4),
                    "energy_tax": round(self.runtime.current_prices.get("energy_tax", 0.0), 4),
                    "sell_energy_price": round(self.runtime.current_prices.get("sell_energy", 0.0), 4),
                    "export_vat_percent": round(self.runtime.current_prices.get("export_vat_factor", 0.0) * 100.0, 4),
                    "grid_benefit_price": round(self.runtime.current_prices.get("grid_benefit_price", 0.0), 4),
                }
            )

        if self.description.key == "net_result_total":
            attrs["definition"] = "exportintäkt + nätnytta + värde egenförbrukad solel. Värde egenförbrukad solel beräknas från producerad energi minus exporterad energi. Importkostnad redovisas separat."
            attrs["initial_settlement_included"] = self.runtime.initial_settlement_done
            if self.runtime.initial_settlement_done:
                attrs["initial_settlement_value"] = self.runtime.initial_settlement_value
                attrs["initial_settlement_kwh"] = self.runtime.initial_settlement_kwh

        if self.description.key == "self_consumed_value_total":
            attrs["initial_settlement_included"] = self.runtime.initial_settlement_done
            if self.runtime.initial_settlement_done:
                attrs["initial_settlement_value"] = self.runtime.initial_settlement_value
                attrs["initial_settlement_kwh"] = self.runtime.initial_settlement_kwh

        if self.description.key == "battery_efficiency":
            cfg = _cfg(self.runtime.entry)
            charge, charge_source, charge_unit = _normalised_battery_energy_state(
                self.runtime.hass,
                cfg.get(CONF_BATTERY_CHARGE_ENERGY),
                ("sensor.rembattery_charge", "sensor.battery_charge"),
            )
            discharge, discharge_source, discharge_unit = _normalised_battery_energy_state(
                self.runtime.hass,
                cfg.get(CONF_BATTERY_DISCHARGE_ENERGY),
                ("sensor.rembattery_discharge", "sensor.battery_discharge"),
            )

            attrs["battery_efficiency_source"] = "battery_discharge_kwh / battery_charge_kwh"
            attrs["battery_efficiency_model"] = "Direkt från valda in-sensorers aktuella mätarställningar, utan baseline."
            attrs["battery_charge_kwh"] = charge
            attrs["battery_discharge_kwh"] = discharge
            attrs["battery_charge_source_entity"] = charge_source
            attrs["battery_discharge_source_entity"] = discharge_source
            attrs["battery_charge_source_unit"] = charge_unit
            attrs["battery_discharge_source_unit"] = discharge_unit

            if not cfg.get(CONF_BATTERY_CHARGE_ENERGY) or not cfg.get(CONF_BATTERY_DISCHARGE_ENERGY):
                attrs["battery_efficiency_status"] = "Batterimätare saknas. Sensorn är inte relevant utan batteri."
            elif charge is None or discharge is None:
                attrs["battery_efficiency_status"] = "Kan inte läsa en eller båda batterimätarna."
            elif charge <= 0:
                attrs["battery_efficiency_status"] = "Batteriladdningsmätaren är 0 eller negativ."
            elif discharge / charge > 1.0:
                attrs["battery_efficiency_status"] = "Över 100 %. Kontrollera om batterimätarna har olika historisk baslinje."
            else:
                attrs["battery_efficiency_status"] = "OK"

        if self.runtime.delta_warnings and self.description.key.endswith("_total"):
            attrs["delta_warnings"] = self.runtime.delta_warnings

        if _investment_cost(self.runtime) > 0 and self.description.key in {"remaining_investment", "roi_percent"}:
            attrs["investment_cost"] = _investment_cost(self.runtime)

        return attrs
