# HA Benchmark 0.7.0

## Deutsch

### Zweck und Sicherheit

HA Benchmark R4 misst sieben definierte Home-Assistant-Workloads praxisnäher als R3. R4 ist zunächst
unkalibriert: Bis neue Green-Referenzserien vorliegen, werden Rohwerte, aber keine Indizes angezeigt.
R3-Ergebnisse bleiben lokal erhalten und in der öffentlichen R3-Rangliste vergleichbar.

**Light** ist für einen kontrollierten Lauf auf einem Produktivsystem gedacht. Auch Light erzeugt
kurzzeitig Last und temporäre Schreibdaten. Nicht während Backups, Updates, Recorder-Bereinigung
oder hoher Automationslast starten. **Full** erzeugt erheblich mehr Last und darf nur auf
Testgeräten verwendet werden; es muss in der App-Konfiguration ausdrücklich freigeschaltet sein.

Für einen guten Community-Wert das System zunächst in den Leerlauf bringen, drei identische Läufe
durchführen und alle drei gemeinsam teilen. Ein Dreier-Eintrag erhält ein Qualitäts-Symbol und nutzt
den Median. Das bedeutet höhere Wiederholbarkeit, aber keine unabhängige Verifizierung.

### Ergebnis verstehen

Jede Kachel zeigt ihren Anteil am Gesamtindex und öffnet per Klick eine Erklärung, typische
Anwendungsfälle sowie Rohwerte. Höher ist beim Index immer besser. Der Gesamtindex ist das
gewichtete geometrische Mittel aus:

| Kategorie | Anteil |
|---|---:|
| Core Events | 15 % |
| State Changes | 20 % |
| Entity-Verarbeitung | 5 % |
| Frische JSON States | 10 % |
| Recorder-Speicher | 20 % |
| API-Latenz | 10 % |
| Parallele Core-Last | 20 % |

Temperatur, Leistung, Energie und Linux-PSI sind ausschließlich Diagnoseinformationen und werden
nicht bewertet. PSI (Pressure Stall Information) zeigt den Zeitanteil, in dem Aufgaben wegen CPU,
Speicher oder I/O warten mussten; es ist keine Auslastungsanzeige. Nahe 0 % ist unauffällig,
dauerhaft mehrere Prozent weisen auf Ressourcenkonkurrenz hin. Während des absichtlich belastenden
Tests ist ein einzelner höherer Wert noch kein Fehler. Es gibt keinen universellen kritischen Wert
für alle HA-Geräte. Die
Temperatur- und Energiekacheln erklären Messquelle und Grenzen ebenfalls per Klick. Die vollständige,
zweisprachige Beschreibung ist in der Oberfläche rechts oben unter **Methodik R4** verlinkt.

### Konfiguration

- **Full-Benchmark erlauben:** Schutzschalter für das intensive Profil.
- **Lokaler Gerätename:** erscheint nur lokal und in lokalen Exporten; er wird nie geteilt.
- **Gerätetyp:** `Automatisch` erkennt eindeutige Geräte. Ist die Erkennung unsicher, fragt die App
  vor dem ersten Lauf einmalig nach. Alternativ kann der Typ hier fest gewählt werden.
- **Prozessormodell:** manuelle Ergänzung, wenn HAOS es nicht erkennt.
- **Speicherart/-größe:** Kontext zum getesteten App-Datenlaufwerk; `0` bedeutet unbekannt.
- **Temperatur-Entität:** optionaler Sensor, z. B. `sensor.cpu_temperature`. Ohne Eintrag versucht
  die App Linux-Sysfs. Nicht jede Plattform gibt diesen Wert an den Container weiter.
- **Leistungs-Entität:** optionaler Sensor in W oder kW, idealerweise eine Messsteckdose am Netzteil.

### Share & Compare

R4-Läufe können erst nach Abschluss der Green-Kalibrierung veröffentlicht werden. R3-Läufe lassen sich
weiterhin teilen. Im Verlauf genau einen oder drei R3-Läufe derselben Methodik, Kalibrierung, desselben Profils und Systems
markieren, **Share & Compare** öffnen, optional eine Modellbezeichnung und einen Alias eintragen und
die Datenvorschau prüfen. Erst die abschließende Zustimmung sendet die angezeigten Daten an
`https://benchmark.smartdomo.de`.

Nicht übertragen werden der lokale Gerätename, Hostname, IP-Adresse, Entity-IDs, Tokens,
Konfigurationen oder andere HA-Zustände. Temperatur und Energie werden nur bei aktivierter Option
mitgesendet. Die Veröffentlichung erscheint sofort und kann nachträglich moderiert werden.

Nach dem Teilen wird ein privater Löschschlüssel einmal angezeigt und zusätzlich im App-Datenspeicher
gesichert. Den Schlüssel herunterladen und getrennt vom öffentlichen Link verwahren. Ohne Konto und
ohne diesen Schlüssel kann eine selbstständige Löschung nicht autorisiert werden.

### Protokoll und Fehlerbehebung

Das App-Protokoll nennt Start, Profil, Fortschritt, Abschlussindex, Laufzeit, fehlgeschlagene Kategorie,
Abbruch und Veröffentlichung-ID. Es protokolliert keine Löschschlüssel, Sensorzustände oder
HTTP-Anfragepfade. Bei Problemen unter **Einstellungen → Apps → HA Benchmark → Protokoll** nachsehen.

- **Full bleibt deaktiviert:** Schutzschalter speichern und App neu starten.
- **Temperatur nicht verfügbar:** HAOS gibt den Sensor nicht frei; Temperatur-Entität konfigurieren.
- **Energie nicht verfügbar:** Leistungssensor muss einen numerischen Wert in W oder kW liefern.
- **Teilen nicht möglich:** Internetzugang/DNS des HA-Systems sowie identische Laufdaten prüfen.
- **Messung streut:** Hintergrundlast entfernen, Gerät abkühlen lassen und drei Läufe verwenden.

## English

### Purpose and safety

HA Benchmark R4 measures seven defined Home Assistant workloads with more representative data than
R3. R4 initially remains uncalibrated: raw measurements are shown, but no indices, until new Green
reference series are available. Existing R3 results remain available in the public R3 ranking.

**Light** is intended for a controlled run on a production system, but still creates temporary load
and writes. Avoid backups, updates, recorder maintenance and busy automation periods. **Full** creates
substantially more load, is for test devices only and requires explicit enablement in configuration.

For a higher-quality community result, let the system idle and share three identical runs together.
The entry receives a repeated-run badge and uses the median. It is more repeatable, not independently
verified.

Each result tile shows its overall weight, index and raw value, and opens an explanation and use cases.
After calibration, higher indices are better. Planned weights are Core Events 15%, State Changes 20%,
entity processing 5%, fresh JSON States 10%, Recorder storage 20%, API latency 10%, and parallel Core
load 20%.
Temperature, power, energy and Linux PSI are informational and are not scored. PSI (Pressure Stall
Information) measures time in which tasks were stalled for CPU, memory or I/O; it is not utilization.
Values near zero are unobtrusive, while sustained values of several percent indicate contention.
A temporary higher value during the intentional benchmark load is not by itself a fault. Open **Methodology R4**
at the top right for the complete bilingual method, formulas and limitations.

The configuration labels explain the Full safety switch, controlled device type, local-only device name, optional CPU model,
storage type and size, and optional temperature/power entities. Without a temperature entity the app
tries Linux sysfs first; not every device exposes it to the container. A power entity must report W or
kW and is best sourced from a metering plug at the power supply.

R4 publishing is enabled only after Green calibration. For the existing R3 **Share & Compare**, select exactly one or three entries with matching methodology, calibration,
profile and system, optionally enter a model name and alias, then inspect the preview. Nothing is transmitted until final consent. Local
device names, hostnames, IPs, entity IDs, tokens, configuration and HA states are excluded. Environment
values are optional. Publication is immediate and subject to later moderation.

The private deletion key is displayed once and also retained in app storage. Download it and keep it
separate from the public link. The log records benchmark lifecycle and publication IDs, but never
deletion keys, sensor states or HTTP request paths. Find it under **Settings → Apps → HA Benchmark → Log**.
