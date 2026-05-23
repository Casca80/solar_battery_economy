# Sol- och batteriekonomi

Version: 0.3.30

Custom integration för Home Assistant som räknar ekonomisk nytta av solproduktion, såld el, nätnytta, egenförbrukad solel, importkostnad, investering/ROI och batteriverkningsgrad.

## Installation

Kopiera mappen:

```text
custom_components/solar_battery_economy
```

till din Home Assistant-konfiguration:

```text
config/custom_components/solar_battery_economy
```

Starta därefter om Home Assistant.

## Konfiguration

Lägg till integrationen via:

```text
Inställningar -> Enheter och tjänster -> Lägg till integration -> Sol- och batteriekonomi
```

Du väljer sensorer för:

- inköpt/importerad energi
- såld/exporterad energi
- solproduktion
- spotpris
- egenkonsumerad solel, valfri
- batteriladdning, valfri
- batteriurladdning, valfri

Alla energimätare ska vara ackumulerande energisensorer, helst med `Wh`, `kWh` eller `MWh`.

Spotprissensorn stöder:

- `SEK/kWh`
- `kr/kWh`
- `öre/kWh`
- `SEK/MWh`
- `kr/MWh`

## Prisfält

Fält med enheten `öre/kWh` anges i öre/kWh exklusive moms.

Exempel:

```text
5
```

betyder:

```text
5 öre/kWh = 0,05 SEK/kWh
```

Integrationens sensorer visar resultat i `SEK/kWh` eller `SEK`.

## Ekonomisk nytta

Ekonomisk nytta beräknas som:

```text
exportintäkt
+ nätnytta
+ värde egenförbrukad solel
```

Importkostnad redovisas separat och dras inte av från ekonomisk nytta.

## Löpande egenförbrukning

Om en mätare för egenkonsumerad solel är vald används den som primär källa.

Om den saknas används fallback:

```text
egenförbrukning_delta = max(0, solproduktion_delta - export_delta)
```

Värdet beräknas med aktuellt totalt köppris:

```text
egenförbrukning_delta_kWh * aktuellt köppris totalt
```

## Engångsavräkning

Engångsavräkningen är tänkt för äldre anläggningar där Home Assistant börjar mäta efter att solanläggningen redan varit i drift.

Den räknar fram historisk egenförbrukad solel:

```text
max(0, total solproduktion - total export)
```

Den historiska egenförbrukningen värderas konservativt:

```text
historisk egenförbrukad kWh
* (fast överföringsavgift + energiskatt)
* moms
```

Rörlig överföringsavgift och spotpris tas inte med i engångsavräkningen.

Engångsavräkningen:

- kan köras med knappen `Kör engångsavräkning`
- läggs bara på totalsensorerna
- påverkar inte idag- eller månadssensorer
- sparas i config entry options
- återställs inte från gamla RestoreEntity-attribut

Det finns även en reset-service:

```yaml
action: solar_battery_economy.reset_initial_settlement
data:
  confirm: RESET
```

Om flera instanser finns kan `entry_id` anges.

## Batteriverkningsgrad

Batteriverkningsgrad beräknas direkt från ackumulerade energimätare:

```text
batteriurladdning_kWh / batteriladdning_kWh * 100
```

Välj lifetime/total energy-sensorer, inte effekt-sensorer.

Bra exempel:

```text
sensor.fronius_symo_gen24_10_0_storage_charging_lifetime_energy
sensor.fronius_symo_gen24_10_0_storage_discharging_lifetime_energy
```

I en Remote HA-speglad sandbox kan motsvarande heta:

```text
sensor.remfronius_symo_gen24_10_0_storage_charging_lifetime_energy
sensor.remfronius_symo_gen24_10_0_storage_discharging_lifetime_energy
```

Om vald batterisensor saknar energienhet försöker integrationen använda vanliga fallback-sensorer:

```text
sensor.rembattery_charge
sensor.rembattery_discharge
sensor.battery_charge
sensor.battery_discharge
```

Batterisensorer är valfria. Felaktiga eller saknade batterisensorer ska inte ge datakvalitetsvarning för hela integrationen.

## Datakvalitet

Datakvalitetssensorn kan visa:

- `OK`
- `Varning`
- `Fel`

Attribut visar bland annat:

- `unit_warnings`
- `ignored_sensors`
- `delta_warnings`
- `status_reason`
- `pending_solar_production_delta_kwh`

`pending_solar_production_delta_kwh` är diagnostik och ger inte i sig själv varning.

## Skapade sensorer

Integrationens sensorer omfattar bland annat:

- aktuellt köppris totalt
- aktuell ersättning såld el
- aktuell överföringsavgift
- aktuell nätnytta
- datakvalitet
- engångsavräkning
- batteriverkningsgrad
- importkostnad idag, denna månad och total
- exportintäkt idag, denna månad och total
- nätnytta idag, denna månad och total
- värde egenförbrukad solel idag, denna månad och total
- ekonomisk nytta idag, denna månad och total
- kvarvarande investering, om investeringskostnad är större än 0
- ROI procent, om investeringskostnad är större än 0

## Viktigt vid uppdatering

Efter kodändringar i `custom_components` krävs full omstart av Home Assistant.

Enbart omladdning av integrationen räcker inte alltid, särskilt när:

- Python-kod har ändrats
- `manifest.json` version har ändrats
- RestoreEntity/config entry-beteende har ändrats

## Felsökning

Om batteriverkningsgrad är `unknown`, kontrollera att valda batterisensorer:

- finns
- har numeriskt state
- har energienhet, till exempel `Wh` eller `kWh`
- är ackumulerande energi, inte momentan effekt

Om engångsavräkning verkar låst:

- kontrollera status-sensorn `Engångsavräkning`
- använd reset-servicen med `confirm: RESET`
- starta om Home Assistant

Om datakvalitet visar `Varning`, öppna sensorns attribut och läs `status_reason`, `unit_warnings`, `ignored_sensors` och `delta_warnings`.
