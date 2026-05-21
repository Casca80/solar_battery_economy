# Sol- och batteriekonomi

Version: 0.3.28

## Reviderad engångsavräkning och egenförbrukning

- Engångsavräkningen använder nu historisk egenförbrukad solel värderad med fast överföringsavgift + energiskatt + moms.
- Rörlig överföringsavgift/spotdel används inte i engångsavräkningen.
- Mätare för egenkonsumerad el är valfri.
- Om mätare för egenkonsumerad el är vald används den för löpande värde av egenförbrukad solel.
- Om den saknas används tidigare fallback med solproduktion minus export.

# Sol- och batteriekonomi

Version: 0.3.29

## Fix för batteriverkningsgrad

- Batteriverkningsgrad använder energimätare för laddning/urladdning.
- Om vald batterisensor saknar energienhet försöker integrationen använda `sensor.rembattery_charge` och `sensor.rembattery_discharge`.
- Valfria batterisensorer med fel enhet ska inte längre ge datakvalitetsvarning.
- Sensorns attribut visar vilken batterikälla som faktiskt användes.

# Sol- och batteriekonomi

Version: 0.3.27

## Fix för datakvalitet och batteriverkningsgrad

- Datakvalitet visar nu tydligare `status_reason`.
- `pending_solar_production_delta_kwh` är endast diagnostik.
- Batteriverkningsgrad visar direkt beräknat värde även om det blir över 100 %, eftersom batterimätare kan ha olika historisk baslinje.
- Batteriverkningsgrad har nu diagnostikattribut för laddad/urladdad energi.

# Sol- och batteriekonomi

Version: 0.3.26

## Svenska översättningar uppdaterade

`translations/sv.json` har uppdaterats med reviderade texter för config flow och options flow.

# Sol- och batteriekonomi

Version: 0.3.25

## English translation added

`translations/en.json` has been added for config flow and options flow.

# Sol- och batteriekonomi

Version: 0.3.24

## Fix för engångsavräkning

Engångsavräkning använder nu config entry options som primär statuskälla.

Fixar:
- gammal RestoreEntity-status från knappen kan inte längre låsa eller låsa upp avräkningen felaktigt
- misslyckad avräkning visas i status-sensorns attribut
- historisk egenförbrukning skyddas med max(0, producerat - exporterad)
- status-sensorn visar last_result och last_error

# Sol- och batteriekonomi

Version: 0.3.23

## Exportmoms inkopplad i beräkningar

Fältet `Moms på export/såld el (%)` används nu i beräkningarna.

Påverkar:
- aktuell ersättning för såld el
- exportintäkt
- aktuell nätnytta
- nätnytta

Standard är 0 %, vilket passar normalfallet för icke momsregistrerad privatperson.

Manifestet är uppdaterat med GitHub-länkar enligt begäran. Manifestets versionsfält är satt till 0.3.21 enligt begäran.

# Sol- och batteriekonomi

Version: 0.3.22

## Konfigurationsändring för moms

Befintligt momsfält har förtydligats till:
- Moms på import/köpt el (%)

Nytt fält:
- Moms på export/såld el (%)

Standardvärde för exportmoms är 0 %.

Beräkningarna är inte ändrade i denna version.

# Sol- och batteriekonomi

Version: 0.3.21

## Fix för reset-service

Reset-servicen för engångsavräkning är förenklad och mer defensiv.

Använd:

```yaml
action: solar_battery_economy.reset_initial_settlement
data:
  confirm: RESET
```

Om flera instanser finns kan `entry_id` anges, annars försöker servicen resetta alla laddade instanser.

# Sol- och batteriekonomi

Version: 0.3.20

## Säkrare engångsavräkning

Engångsavräkning sparas nu även i config entry options, inte bara via RestoreEntity.

Tillagt:
- sensor.sol_och_batteriekonomi_engangsavrakning
- service: solar_battery_economy.reset_initial_settlement
- services.yaml

Reset kräver uttrycklig bekräftelse:

confirm: "RESET"

Vid reset dras tidigare avräkningsvärde bort från totalsensorn för egenförbrukad solel och ekonomisk nytta räknas om.

# Sol- och batteriekonomi

Version: 0.3.19

## Korrigerad egenförbrukning

Värde av egenförbrukad solel räknas inte längre på all producerad solel.

Tidigare förenklade modell:
produktion_delta_kWh * aktuellt köppris totalt

Ny modell:
egenförbrukning_delta_kWh = max(0, produktion_delta_kWh - export_delta_kWh)

värde egenförbrukad solel =
egenförbrukning_delta_kWh * aktuellt köppris totalt

Detta minskar risken för dubbelräkning där exporterad solel tidigare både kunde ge exportintäkt/nätnytta och samtidigt räknas som egenförbrukad solel.

# Sol- och batteriekonomi

Version: 0.3.18

## Nätnytta inkluderad i ekonomisk nytta

Nätnytta ingår nu i ekonomisk nytta:

ekonomisk nytta =
exportintäkt + nätnytta + värde egenförbrukad solel

Eftersom ROI och kvarvarande investering bygger på ekonomisk nytta total ingår nätnytta även där när investeringskostnad är större än 0.

Importkostnad redovisas fortsatt separat.
Batteriverkningsgrad påverkar fortsatt inte ekonomisk nytta eller ROI.

# Sol- och batteriekonomi

Version: 0.3.17

## Nätnyttesensorer aktiverade

Denna version aktiverar nätnyttesensorerna igen:

- sensor.sol_och_batteriekonomi_aktuell_natnytta
- sensor.sol_och_batteriekonomi_natnytta_idag
- sensor.sol_och_batteriekonomi_natnytta_denna_manad
- sensor.sol_och_batteriekonomi_natnytta_total

Nätnytta räknas på exportdelta.

I denna version påverkar nätnytta fortfarande inte ekonomisk nytta eller ROI.
Det görs först efter verifiering av att nätnyttesensorerna räknar rätt.

# Sol- och batteriekonomi

Version: 0.3.16

## Kontrollerat nästa steg för nätnytta

Denna version behåller de fungerande configfälten från v0.3.15 och kopplar in nätnyttans runtime-beräkning internt.

Inga nya sensorer skapas ännu och nätnytta påverkar ännu inte ekonomisk nytta eller ROI.

Syftet är att verifiera att exportdelta kan beräkna nätnytta utan att störa config flow eller befintliga sensorer.

# Sol- och batteriekonomi

Version: 0.3.15

## Fix

Rättar importfelet:
cannot import name 'CONF_GRID_BENEFIT_SPOT_PERCENT'

v0.3.14 saknade konstanten i const.py.

# Sol- och batteriekonomi

Version: 0.3.14

## Testrelease för nätnytta i config flow

Denna version gör endast steg 1-5 i återinförandet av nätnytta.

Tillagt i konfiguration och rekonfiguration:
- Nätnytta fast del (öre/kWh)
- Nätnytta procent av spotpris

Viktigt:
- Ingen ny nätnyttesensor skapas i denna testrelease.
- Ingen nätnytteberäkning kopplas in i ekonomisk nytta i denna testrelease.
- Syftet är endast att verifiera att initial konfiguration och rekonfigurering fungerar med två extra numeriska fält.

# Sol- och batteriekonomi

Version: 0.3.13

## Stabil fix

Denna version bygger från senast bekräftat fungerande v0.3.11.

Nätnyttefälten i config flow är borttagna igen eftersom v0.3.12 återinförde 400 Bad Request vid konfiguration.

Nätnytta ska testas isolerat innan den läggs tillbaka i huvudversionen.

# Sol- och batteriekonomi

Version: 0.3.11

## Stabiliseringsrelease

Denna version återställer config flow till den senast kända fungerande strukturen från v0.3.3.

Nätnyttefält i konfigurationsformuläret är tillfälligt borttagna för att isolera 400 Bad Request-felet.
Runtime-stöd för nätnytta finns kvar men är inte exponerat i formuläret i denna version.

Syftet är att initial konfiguration och rekonfigurering ska fungera igen.

# Sol- och batteriekonomi

Version: 0.3.10

## Fix i 0.3.10

- NumberSelectorConfig får inte längre unit_of_measurement="".
- Tom enhet görs om till None.
- Detta är avsett att rätta 400 Bad Request i config flow.

# Sol- och batteriekonomi

Version: 0.3.9

## Fix i 0.3.9

Denna version fokuserar på att config flow ska kunna laddas igen.

- sensor.py importeras inte längre indirekt när config flow laddas.
- Select-fält är förenklade för bättre kompatibilitet.
- PERCENTAGE definieras lokalt.
- Kvarvarande investering har korrekt state_class.




# Sol- och batteriekonomi

Version: 0.3.8
Author: Jimmy med ChatGPT

## Fix i 0.3.8

- Kvarvarande investering har korrigerad state_class.
- Nätnytta Ja/Nej använder select i stället för BooleanSelector i options flow.
- Config flow är mer defensiv mot tomma eller felaktiga numeric defaults.
- Paketet exkluderar __pycache__ och *.pyc.




# Sol- och batteriekonomi

Version: 0.3.7
Author: Jimmy med ChatGPT

## Viktiga ändringar i 0.3.7

- Ekonomisk batteriförlust är borttagen.
- Batteriförlust påverkar inte längre ekonomisk nytta.
- Batteriförlust påverkar inte längre ROI.
- Tidigare sensor för batteriförlustkostnad tas bort.
- Batteriets verkningsgrad räknas direkt från valda in-sensorer:
  batteriurladdning / batteriladdning * 100.
- Sensorn heter:
  sensor.sol_och_batteriekonomi_verkningsgrad_batteri
- Ny datakvalitetssensor:
  sensor.sol_och_batteriekonomi_datakvalitet
- ROI och kvarvarande investering skapas endast om investeringskostnad är större än 0.
- Paketet exkluderar __pycache__ och *.pyc.

## Datakvalitet

Datakvalitetssensorn visar:
- OK
- Varning
- Fel

Attribut visar:
- unit_warnings
- ignored_sensors
- delta_warnings

Okända energi- eller prisenheter ignoreras för att undvika felberäkningar.

## Ekonomisk nytta

Ekonomisk nytta beräknas nu som:

exportintäkt
+ nätnytta
+ värde av egenförbrukad solel

Importkostnad redovisas separat.
Batteriverkningsgrad är en teknisk mätning och påverkar inte ekonomisk nytta.
