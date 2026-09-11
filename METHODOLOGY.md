# Benchmark-Methodik R4 · App-Version 0.8.2

## Status

R4 ist mit fünf kontrollierten Home-Assistant-Green-Läufen je Profil kalibriert. Die Referenz
`GREEN-CORE-2026-09-D` verwendet die Mediane der Rohmetriken. Rangliste und Gerätevergleich erlauben
nur Ergebnisse dieser Methodik und Kalibrierung.

## Ziel und Abgrenzung

R4 misst definierte Home-Assistant-Leistung, nicht Preis, Marktverbreitung oder die allgemeine
Eignung eines Geräts. Die isolierte Messengine verwendet Home Assistant Core 2026.9.1 auf allen
Zielsystemen. Nur der API-Test fragt die laufende Home-Assistant-Instanz ab.

Die Methodik vermeidet vier typische Verzerrungen synthetischer Benchmarks:

- State-Events verteilen sich über hunderte Entity-IDs; neben einem übergreifenden Callback werden
  alle 14 zusätzlich registrierten Entity-Gruppen während des Tests angesprochen.
- Events, Zustände und Attribute ändern sich statt dass dasselbe Objekt tausendfach wiederholt wird.
- Entity-Prüfungen verwenden 80 % wiederkehrende und 20 % neue IDs statt nahezu reiner Cache-Treffer.
- Eine getrennte Prozesslast macht verfügbare Mehrkern-Kapazität sichtbar.

## Kategorien und Gewichtung

| Kategorie | Anteil | R4-Arbeitslast |
|---|---:|---|
| Core Events | 15 % | Acht Eventtypen, wechselnde Nutzdaten, vollständige Burst-Verarbeitung |
| State Changes | 20 % | Wechselnde alte/neue State-Objekte über 400 bzw. 1.000 Entitäten |
| Entity-Verarbeitung | 5 % | Filter und ID-Prüfung mit gemischtem Arbeitsbestand |
| JSON States | 10 % | Je Batch neu erzeugte State-Objekte und Attribute |
| Recorder-Speicher | 20 % | Dauerhafte SQLite-Commits, Schreiben, Zufallslesen, WAL-Checkpoint |
| HA API | 10 % | Mediane Antwortzeit der laufenden REST-API |
| Parallele Core-Last | 20 % | Gleichzeitige State-Erzeugung/-Serialisierung in getrennten Prozessen |

Für die Indexberechnung gilt:

- Durchsatzindex = `100 × Messwert / Green-Referenz`
- Latenzindex = `100 × Green-Referenz / Messwert`
- Smartdomo Index = gewichtetes geometrisches Mittel der Kategorieindizes

## Profile

| Parameter | Light | Full |
|---|---:|---:|
| Core Events | 24.000 | 120.000 |
| State Changes | 12.000 | 60.000 |
| Entity-Arbeitsbestand | 400 | 1.000 |
| Entity-Operationspaare | 40.000 | 200.000 |
| JSON-Batches × Entitäten | 50 × 400 | 100 × 1.000 |
| parallele Worker (maximal) | 2 | 4 |
| parallele Batches × Entitäten je Worker | 80 × 400 | 180 × 600 |
| SQLite-Nutzdaten | 6 MiB | 64 MiB |
| dauerhafte SQLite-Commits | 100 | 1.000 |
| SQLite-Zufallslesezugriffe | 1.000 | 5.000 |
| API-Aufrufe | 10 | 30 |

Light begrenzt Arbeitsspeicher und temporäre Schreibdaten und darf kontrolliert auf einem ruhigen
Produktivsystem laufen. Full erzeugt deutlich höhere Last und ist ausschließlich für Testsysteme.

## Testdetails

### Core Events und State Changes

Core Events misst einen isolierten HA-Event-Bus mit acht Ereignistypen und jeweils einem Callback.
Erzeugung und Callback-Verarbeitung liegen innerhalb der Messzeit. Regelmäßige
`async_block_till_done`-Grenzen begrenzen die Warteschlange.

State Changes erzeugt synthetische `state_changed`-Events für den gesamten Entity-Bestand. Zu jedem
Event gehören zwei neu angelegte State-Objekte: `old_state` repräsentiert den vorherigen und
`new_state` den neuen Zustand. Ein Callback überwacht alle Entity-IDs; 14 kleinere Gruppen führen
zusätzlich typische Zustands- und Attributzugriffe aus. Der Test verwendet nicht den echten
HA-Zustandsautomaten und aktiviert weder Recorder noch WebSocket-Updates oder vollständige Automationen.

### Entity-Verarbeitung und JSON

Ein Entity-Operationspaar besteht aus Include-/Exclude-Filterung und `valid_entity_id`. Vier von fünf
IDs stammen aus einem wiederkehrenden Bestand, jede fünfte ist neu. JSON misst sowohl die Erzeugung
neuer Core-State-Objekte als auch deren Serialisierung mit Home Assistants JSON-Encoder.

### Parallele Core-Last

Getrennte Prozesse erzeugen und serialisieren gleichzeitig frische Core-State-Objekte. Prozessstart
und Modulimport werden vor der Zeitmessung aufgewärmt. Die Kategorie bildet Mehrkern-Reserve für
parallel laufende Apps und HA-nahe Aufgaben ab. Sie behauptet nicht, dass Home Assistants Event-Loop
selbst mehrere Kerne parallel nutzt.

### Recorder-Speicher

Auf dem App-Datenlaufwerk wird eine temporäre SQLite-Datenbank mit State-ähnlichen Datensätzen und
einem Index angelegt. SQLite verwendet `journal_mode=WAL`, `synchronous=FULL` und deaktivierte automatische Checkpoints.
Der Speicherindex setzt sich nach der Kalibrierung aus Commit-p95 (40 %), Schreibdurchsatz (25 %),
Random-Read-p95 (20 %) und WAL-Checkpoint (15 %) zusammen. Cache-Freigabe wird per
`POSIX_FADV_DONTNEED` angefordert, garantiert aber keine physisch kalten Zugriffe. Haltbarkeit und
Stromausfallsicherheit werden nicht geprüft. Die Arbeitslast ist Recorder-nah, führt aber nicht Home
Assistants tatsächlichen Recorder aus.

### HA API

Der API-Test misst als einzige Kategorie die laufende Home-Assistant-Instanz. Er verwendet den Median
aus 10 beziehungsweise 30 authentifizierten Core-API-Aufrufen aus dem App-Container. Gemessen werden
Core-Antwortzeit und lokaler Supervisor-/Container-Netzwerkpfad gemeinsam.

## Diagnosewerte

Temperatur, elektrische Leistungsaufnahme, Energie und Linux Pressure Stall Information (PSI) sind reine Informationen und
gehen nicht in den Index ein. Der Energieverbrauch wird aus den während des Laufs erfassten
Leistungswerten angenähert. PSI misst Wartezeit wegen fehlender CPU-Zeit, Arbeitsspeicher- oder
I/O-Ressourcen und ist keine normale Auslastungsanzeige.

## Kalibrierungsprotokoll

Die Referenz wurde aus fünf Light- und fünf Full-Läufen auf demselben Home Assistant Green mit Core
2026.9.1, HAOS 18.2 und Supervisor 2026.09.0 gebildet. Alle zehn gültigen R4-Läufe wurden verwendet;
es gab keine Ausschlüsse. Je Rohmetrik gilt der Median als Green = 100. Referenzwerte, Lauf-IDs,
Streuung und Grenzen sind im [R4-Kalibrierungsbericht](CALIBRATION-R4.md) dokumentiert.
