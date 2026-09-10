# Changelog

## 0.6.1

- Community-Installer startet einen bereits laufenden Dienst nach einem Update zuverlässig neu
- Keine Änderung an Benchmark-Methodik R3 oder Green-Kalibrierung C

## 0.6.0

- Neuer responsiver Hell-/Dunkelmodus nach Browser- oder Home-Assistant-Einstellung
- Englisch als Standard; Deutsch wird bei deutscher Browser-/HA-Sprache automatisch gewählt
- Smartdomo Index und Kategorieindizes anklickbar mit Formel, Gewicht, Rohwert und Anwendungsbezug
- Diagnosebereich kleiner und klar als „nur Information, keine Bewertung“ gekennzeichnet
- Ausführlichere Einordnung von Temperatur, Leistung, Energie und Linux PSI
- Kontrollierte kurze Gerätetypen mit konservativer Erkennung und einmaliger Auswahl bei Unklarheit
- Ranking mit getrennten RAM-/Massenspeicher-Spalten sowie Filtern für Gerät, Speicher, HA Core und Alias
- Gerätevergleich zeigt Gewichte, Kategorieindex und tatsächlichen Messwert mit Einheit
- Methodenbasierte Kompatibilität über App-Versionen hinweg und Stabilitätsanzeige für Dreiermessungen
- Mobile Navigation und Datei-Export für die Home Assistant Companion App robust überarbeitet
- Neues Benchmark-Symbol für App und Store sowie Favicon für die Community-Seite
- Atomare lokale Ergebnisspeicherung, gehärtete Rate-Limit-Ermittlung und erweiterte Protokollierung

## 0.5.0

- Zweisprachige Oberfläche, Dokumentation und verständliche Konfigurationsbeschreibungen
- Originale Smartdomo-Logos dezent als App-Icon, Store-Logo und Footer-Marke
- Methodik R3 direkt rechts oben verlinkt; Gewichte auf allen Ergebnis- und Diagnosekacheln
- Anklickbare Erklärungen für Temperatur, Leistung, Energie und Linux PSI
- Share & Compare mit expliziter Datenvorschau und Einwilligung
- Öffentliche Einzel- oder Dreiermessung; Median und Qualitätskennzeichen für drei Läufe
- Optionaler Alias, separates öffentliches Gerätemodell und privater Löschschlüssel ohne Konto
- Öffentliche Rangliste, Detailvergleich, Selbstlöschung sowie nachträgliche Moderation
- Datensparsame Serverprotokolle, Upload-Limit, Eingabevalidierung, Backups und Lösch-Tombstones
- Bestehende `/ha-dashboard`-Apache-Konfiguration bleibt beim Community-Installer unangetastet

## 0.4.1

- Home Assistant Green für Methodik R3 als Index 100 kalibriert
- Getrennte Medianreferenzen aus sechs stabilen Light- und sechs Full-Läufen
- Kalibrierung `GREEN-CORE-2026-09-C` auf HAOS 18.2 und Core 2026.9.1
- Vier getrennte Green-Referenzen für den Recorder-Speicherindex

## 0.4.0

- Recorder-Speichertest auf `SQLite WAL` mit `synchronous=FULL` umgestellt
- Kleine dauerhaft synchronisierte Transaktionen statt eines cache- und CPU-lastigen Ops/s-Mischwerts
- Getrennte Rohwerte für Schreibdurchsatz, Commit-Median/p95/p99, Random-Read-Median/p95/p99 und WAL-Checkpoint
- Best-Effort-Freigabe des Linux-Dateicaches vor den Zufallslesezugriffen
- Speicherindex aus vier gewichteten Teilindizes; Commit-p95 erhält innerhalb der Speicherkategorie den größten Anteil
- Temporärer Spitzenbedarf und detaillierte Speicherwerte in JSON, CSV und der anklickbaren Ergebniskarte
- Methodik-ID `CORE-2026.9.1-R3`; Green-Kalibrierung bis zu neuen Referenzläufen zurückgesetzt

## 0.3.2

- Home Assistant Green als Index 100 kalibriert
- Getrennte Medianreferenzen aus jeweils fünf Light- und Full-Läufen
- Kalibrierung `GREEN-CORE-2026-09-B`
- Stabile Methodik-ID `CORE-2026.9.1-R2` für spätere Vergleichs- und Rankingfunktionen
- Methodik-ID im JSON- und CSV-Export

## 0.3.1

- Event- und State-Durchsatz misst jetzt die vollständige Erzeugungs- und Verarbeitungszeit
- Kurzer Warm-up vor beiden asynchronen Core-Tests
- JSON-State-Test verwendet den Median aus drei Durchläufen mit definierter Garbage Collection
- Automatische CPU-/SoC-Temperaturerkennung über Linux-Sysfs mit HA-Entität als Alternative
- 0.3.0-Referenzmessungen wegen der korrigierten Zeitbasis verworfen

## 0.3.0

- Messengine auf isolierte, parameterisierte Home-Assistant-Core-Benchmarks umgestellt
- Core Events, State Changes, Entity-Filter, Entity-ID-Prüfung und JSON-State-Serialisierung
- Sequenziellen Datenträgertest durch Recorder-nahen SQLite-Test ersetzt
- REST-API-Latenz nur noch einmal gewertet
- Optionale Temperatur- und Leistungssensoren; Maximaltemperatur, Temperaturanstieg, Durchschnitts-/Spitzenleistung und Energieverbrauch
- Linux Pressure Stall Information (CPU, Speicher und I/O) als ungewichteter Diagnosewert
- Gewicht jeder Kategorie direkt auf der Ergebniskarte
- Index vorübergehend deaktiviert, bis neue Green-Referenzmessungen vorliegen

## 0.2.0

- Jede Kategorie auf Home Assistant Green = 100 indexiert
- Getrennte Referenzwerte für Light und Full
- Gesamtindex als gewichtetes geometrisches Mittel
- Anklickbare Ergebniskarten mit Interpretation und Anwendungsfällen
- Systemübersicht mit Gerät, CPU, RAM, Speicher, HAOS, Core und Supervisor
- Erweiterter CSV- und JSON-Export
- Abwärtskompatible Anzeige vorhandener 0.1.0-Ergebnisse

## 0.1.0

- Erster MVP mit Light- und Full-Profil
- CPU-, Speicher-, Datenträger-, Event-, State-, Template- und API-Latenztests
- Lokale Historie sowie JSON- und CSV-Export
- Schutzschalter für Full-Benchmark
