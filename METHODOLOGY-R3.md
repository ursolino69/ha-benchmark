# Benchmark-Methodik R3 · App-Version 0.6.1

## Ziel und Engine

HA Benchmark misst Home-Assistant-relevante Arbeit statt allgemeiner Rechenleistung. Version 0.6.1 führt Mikrobenchmarks mit einem fest eingebauten Home Assistant Core 2026.9.1 direkt im App-Container aus. Damit bleibt die getestete Core-Implementierung über verschiedene Zielsysteme konstant.

Die Core-Tests orientieren sich am [offiziellen Benchmark-Skript von Home Assistant Core](https://github.com/home-assistant/core/blob/dev/homeassistant/scripts/benchmark/__init__.py). Bei Events und State Changes umfasst die Zeitmessung sowohl Erzeugung als auch Verarbeitung. Hinzu kommen die Latenz der tatsächlich laufenden Home-Assistant-API und ein Recorder-naher SQLite-Test auf dem App-Datenlaufwerk.

## Kategorien und Gewichtung

| Kategorie | Gewicht | Gemessene HA-Arbeit |
|---|---:|---|
| Core Events | 20 % | Interner Event-Bus und Listener-Ausführung |
| State Changes | 20 % | State-Change-Events mit registrierten Entity-Listenern |
| Entity-Filter | 10 % | Include-/Exclude-Filter für Domains, Entitäten und Globs |
| Entity-IDs | 5 % | Validierung von Entity-IDs als kleine, häufige Core-Operation |
| JSON States | 15 % | Serialisierung echter Core-State-Objekte |
| Recorder-Speicher | 20 % | Dauerhafte SQLite-Commits, Schreiben, Zufallslesen und WAL-Checkpoint |
| HA API | 10 % | Mediane Antwortzeit der laufenden Core-REST-API |

Der Gesamtindex wird nach der Green-Kalibrierung als gewichtetes geometrisches Mittel berechnet. Das reduziert die Wirkung einzelner extremer Teilwerte und belohnt ein ausgewogenes System. Bei Latenzen wird das Verhältnis umgekehrt, weil weniger Millisekunden besser sind.

## Recorder-Speichertest R3

SQLite verwendet `journal_mode=WAL`, `synchronous=FULL` und deaktivierte automatische Checkpoints. Die App schreibt 2-KiB-Datensätze in viele kleine Transaktionen. Jeder gemessene Commit fordert damit eine dauerhafte Synchronisation durch SQLite und das Betriebssystem an. Anschließend wird ein expliziter WAL-Checkpoint ausgeführt. Vor den Zufallslesezugriffen wird der Datenbank-Handle geschlossen und die Freigabe des Linux-Dateicaches mit `POSIX_FADV_DONTNEED` angefordert, sofern dies im Container verfügbar ist. Diese Freigabe ist Best Effort und keine Garantie, dass jeder Lesezugriff das physische Medium erreicht.

Der Recorder-Speicherindex ist selbst ein geometrisches Mittel aus vier Teilindizes:

| Teilmessung | Anteil am Speicherindex | Richtung | Bedeutung |
|---|---:|---|---|
| Commit p95 | 40 % | niedriger besser | ungünstige Latenz der dauerhaften kleinen Transaktionen |
| Schreibdurchsatz | 25 % | höher besser | Nutzdaten pro gesamter Schreibphase |
| Random Read p95 | 20 % | niedriger besser | ungünstige Latenz verstreuter Datensätze nach Cache-Freigabeversuch |
| WAL-Checkpoint | 15 % | niedriger besser | Übernahme des WAL in die Hauptdatenbank |

Der Speicherindex trägt anschließend mit 20 % zum Gesamtindex bei. Eine schnelle SD-Karte kann in einzelnen Teilwerten gut abschneiden, ihre typische Schwäche bei Synchronisationslatenz und Streuung wird aber wesentlich deutlicher sichtbar als im früheren gemischten Ops/s-Test. Haltbarkeit, Stromausfallsicherheit und Alterung werden weiterhin nicht geprüft.

## Green-Kalibrierung

Kalibrierung `GREEN-CORE-2026-09-C`, Methodik `CORE-2026.9.1-R3`: sechs Light- und sechs Full-Läufe auf einem Home Assistant Green mit Home Assistant OS 18.2, Core 2026.9.1 und Supervisor 2026.09.0. Der Median jeder Kategorie und Speicher-Teilmessung bildet Index 100. Ein vorheriger Light-Lauf wurde ausgeschlossen, weil seine Gesamtdauer mit 14,25 Sekunden mehr als doppelt so hoch wie die stabile Messgruppe war und zu Beginn erhöhter CPU-Druck gemessen wurde.

| Kategorie | Light = 100 | Full = 100 |
|---|---:|---:|
| Core Events | 49.907/s | 49.543/s |
| State Changes | 35.642,5/s | 35.549,5/s |
| Entity-Filter | 767.060,5/s | 771.039,5/s |
| Entity-IDs | 1.631.954,5/s | 1.621.901,5/s |
| JSON States | 276.875,5/s | 279.900,5/s |
| Speicher: Schreiben | 11,935 MiB/s | 10,765 MiB/s |
| Speicher: Commit p95 | 4,1095 ms | 5,3895 ms |
| Speicher: Random Read p95 | 0,4142 ms | 0,28905 ms |
| Speicher: WAL-Checkpoint | 162,92 ms | 1.657,5 ms |
| HA API | 18,535 ms | 18,675 ms |

Light-Result-IDs: `445c99c58753`, `f828297de964`, `0648efa0efd6`, `1850e369d1a4`, `f7dc13733227`, `d990a495fdb0`. Full-Result-IDs: `d5139fccaec4`, `370107630315`, `43740a71af97`, `2b80c89b7e4a`, `101d288b1f45`, `b8c1b67ffe50`.

0.4.1 bis 0.6.1 verwenden dieselbe R3-Engine und Kalibrierung. Die öffentliche Rangliste
gruppiert deshalb nach Profil, Methodik-ID und Kalibrierung statt nach App-Version. Ergebnisse aus
0.4.0 oder älter sind nicht kompatibel.

## Profile

| Parameter | Light | Full |
|---|---:|---:|
| Core Events | 50.000 | 250.000 |
| State Events | 25.000 | 100.000 |
| registrierte State-Listener | 250 | 1.000 |
| Entity-Filter-Aufrufe | 50.000 | 250.000 |
| Entity-ID-Prüfungen | 250.000 | 1.000.000 |
| serialisierte States | 20.000 | 100.000 |
| SQLite-Nutzdaten | 6 MiB | 64 MiB |
| dauerhafte SQLite-Commits | 100 | 1.000 |
| SQLite-Zufallslesezugriffe | 1.000 | 5.000 |
| API-Aufrufe | 8 | 30 |

Light begrenzt Last und temporäre Daten und ist für kontrollierte Läufe auf Produktivsystemen vorgesehen. Durch WAL und Hauptdatenbank liegt der kurzfristige Platzbedarf über der Nutzdatenmenge und wird im Resultat als `peak_temporary_mib` protokolliert. Full ist nur für Testsysteme freigebbar.

## Diagnosewerte ohne Gewicht

- CPU-/SoC-Temperatur aus Linux-Sysfs oder einer konfigurierten HA-Entität
- optionale Durchschnitts- und Spitzenleistung sowie integrierte Energie aus einem Sensor in W oder kW
- Linux Pressure Stall Information (PSI) für CPU-, Speicher- und I/O-Druck

Diese Werte sind reine Diagnoseinformationen und werden nicht bewertet. Temperatur hängt stark von
Kühlung und Umgebung ab. Eine Leistungsmessung kann je nach Sensor das Gesamtsystem oder nur einen
Teil davon umfassen. Linux PSI misst den Anteil der Zeit, in der mindestens eine Aufgabe (`some`) oder
alle nicht-idlen Aufgaben (`full`) auf CPU, Speicher oder I/O warten mussten. Es ist keine
Auslastungsanzeige und keine Hardware-Leistungskennzahl. Nahe 0 % ist unauffällig; dauerhaft mehrere
Prozent weisen auf Ressourcenkonkurrenz hin. Der Benchmark erzeugt selbst Druck, daher ist ein einzelner
höherer Testwert nicht automatisch kritisch.

## Reproduzierbarkeit

- Nur dieselbe Methodik-ID, Kalibrierung, dasselbe Profil und dieselbe Engine-Core-Version vergleichen.
- Keine Backups, Updates oder Datenbankbereinigungen während eines Laufs.
- Das System vorher einige Minuten im Leerlauf stabilisieren.
- Mindestens drei Läufe durchführen und je Kategorie sowie insgesamt den Median verwenden.
- Für eine Referenzkalibrierung mindestens fünf Läufe pro Profil verwenden.
- Kühlung, Speichermedium, Home-Assistant-Version und laufende Apps dokumentieren.
- Light und Full niemals in derselben Rangliste führen.

## Nebenwirkungen und Grenzen

Die Core-Mikrobenchmarks laufen in einer isolierten Home-Assistant-Instanz innerhalb der Benchmark-App und verändern keine Entitäten der produktiven Instanz. SQLite arbeitet ausschließlich mit einer temporären Datenbank im App-Datenverzeichnis und löscht sie anschließend. Nur der API-Test fragt die laufende Home-Assistant-Instanz ab; er verändert keine Daten.

Der Benchmark bildet wichtige Core-Pfade ab, aber nicht jede Integration, Funklatenz, langfristige Recorder-Datenbank, SD-Karten-Haltbarkeit oder Dashboard-Konfiguration. Das Ergebnis ist ein vergleichbarer Index für die definierte Methodik, keine Garantie für jeden realen Anwendungsfall.
