"""Constants for Sol- och batteriekonomi."""

DOMAIN = "solar_battery_economy"
PLATFORMS = ["sensor", "button"]

MANUFACTURER = "Jimmy med ChatGPT"
MODEL = "Solar Battery Economy"

CONF_NAME = "name"

# Data point entity ids selected in the GUI.
CONF_IMPORT_ENERGY = "import_energy_entity"
CONF_EXPORT_ENERGY = "export_energy_entity"
CONF_HOME_CONSUMPTION_ENERGY = "home_consumption_energy_entity"
CONF_SOLAR_PRODUCTION_ENERGY = "solar_production_energy_entity"
CONF_BATTERY_CHARGE_ENERGY = "battery_charge_energy_entity"
CONF_BATTERY_DISCHARGE_ENERGY = "battery_discharge_energy_entity"
CONF_SPOT_PRICE = "spot_price_entity"

# Contract fields. Stored internally as SEK/kWh, except percent and SEK investment.
CONF_BUY_PRICE_MODE = "buy_price_mode"
CONF_BUY_PRICE_ADJUSTMENT = "buy_price_adjustment"
CONF_SELL_PRICE_MODE = "sell_price_mode"
CONF_SELL_PRICE_ADJUSTMENT = "sell_price_adjustment"
CONF_GRID_IMPORT_MODE = "grid_import_mode"
CONF_GRID_IMPORT_FIXED = "grid_import_fixed"
CONF_GRID_IMPORT_PERCENT_OF_SPOT = "grid_import_percent_of_spot"
CONF_ENERGY_TAX = "energy_tax"
CONF_VAT_PERCENT = "vat_percent"
CONF_EXPORT_VAT_PERCENT = "export_vat_percent"
CONF_INVESTMENT_COST = "investment_cost"
CONF_INITIAL_SETTLEMENT_DONE = "initial_settlement_done"
CONF_INITIAL_SETTLEMENT_TIME = "initial_settlement_time"
CONF_INITIAL_SETTLEMENT_KWH = "initial_settlement_kwh"
CONF_INITIAL_SETTLEMENT_VALUE = "initial_settlement_value"

CONF_GRID_BENEFIT_ENABLED = "grid_benefit_enabled"
CONF_GRID_BENEFIT_FIXED_ORE = "grid_benefit_fixed_ore"
CONF_GRID_BENEFIT_SPOT_PERCENT = "grid_benefit_spot_percent"
CONF_GRID_BENEFIT_SPOT_MULTIPLIER = "grid_benefit_spot_multiplier"

MODE_SPOT = "spot"
MODE_SPOT_PLUS = "spot_plus"
MODE_SPOT_MINUS = "spot_minus"
MODE_FIXED = "fixed"
MODE_FIXED_PLUS_PERCENT_SPOT = "fixed_plus_percent_spot"

DEFAULT_NAME = "solekonomi"
DEFAULT_BUY_PRICE_MODE = MODE_SPOT_PLUS
DEFAULT_SELL_PRICE_MODE = MODE_SPOT_PLUS
DEFAULT_GRID_IMPORT_MODE = MODE_FIXED_PLUS_PERCENT_SPOT

# Internal defaults are SEK/kWh.
DEFAULT_BUY_PRICE_ADJUSTMENT = 0.0
DEFAULT_SELL_PRICE_ADJUSTMENT = 0.0
DEFAULT_GRID_IMPORT_FIXED = 0.18
DEFAULT_GRID_IMPORT_PERCENT_OF_SPOT = 5.0
DEFAULT_ENERGY_TAX = 0.36
DEFAULT_VAT_PERCENT = 25.0
DEFAULT_EXPORT_VAT_PERCENT = 0.0
DEFAULT_INVESTMENT_COST = 0.0

# Large meter deltas are accepted but flagged in attributes.
LARGE_DELTA_WARNING_KWH = 1000.0

DEFAULT_GRID_BENEFIT_ENABLED = False
DEFAULT_GRID_BENEFIT_FIXED_ORE = 6.6
DEFAULT_GRID_BENEFIT_SPOT_MULTIPLIER = 0.0561
DEFAULT_GRID_BENEFIT_SPOT_PERCENT = 5.61
