'use strict';
const language=document.getElementById('language'),queryLanguage=new URLSearchParams(location.search).get('lang'),saved=localStorage.getItem('ha-benchmark-language'),browser=(navigator.languages?.[0]||navigator.language||'en').toLowerCase();
language.value=['de','en'].includes(queryLanguage)?queryLanguage:['de','en'].includes(saved)?saved:browser.startsWith('de')?'de':'en';
function theme(){document.documentElement.dataset.theme=matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light'}theme();matchMedia('(prefers-color-scheme:dark)').addEventListener('change',theme);
const weights=`<div class="table-wrap"><table><thead><tr><th>Category / Kategorie</th><th>Weight / Anteil</th></tr></thead><tbody><tr><td>Core events</td><td>15 %</td></tr><tr><td>State changes</td><td>20 %</td></tr><tr><td>Entity processing</td><td>5 %</td></tr><tr><td>Fresh JSON states</td><td>10 %</td></tr><tr><td>Recorder storage</td><td>20 %</td></tr><tr><td>API latency</td><td>10 %</td></tr><tr><td>Parallel Core load</td><td>20 %</td></tr></tbody></table></div>`;
const de=`
<h1>Benchmark-Methodik R4</h1>
<h2>Status</h2>
<p>R4 ist mit fünf Light- und fünf Full-Läufen auf Home Assistant Green kalibriert. Die Referenz <strong>GREEN-CORE-2026-09-D</strong> verwendet Home Assistant Core 2026.9.1, HAOS 18.2 und Supervisor 2026.09.0. R4 ist wegen grundlegend veränderter Arbeitslasten nicht mit R3 vergleichbar.</p>
<h2>Ziel der Überarbeitung</h2>
<p>R4 misst definierte Home-Assistant-Leistung statt allgemeiner Eignung. Die Arbeitsmengen orientieren sich an Installationen mit hunderten Entitäten und kombinieren wiederkehrende mit neuen Daten. Reine Python-Cache-Treffer beeinflussen das Ergebnis damit deutlich weniger. Gerätepreis, Marktverbreitung und Eignungsklassen sind nicht Bestandteil von R4.</p>
<h2>Gewichtung</h2>${weights}
<p>Die Gewichte sind fest veröffentlicht und werden nicht an Hersteller oder gewünschte Rangfolgen angepasst.</p>
<h2>Core Events</h2>
<p>Acht Ereignistypen werden mit variierenden Nutzdaten in begrenzten Bursts erzeugt und vollständig verarbeitet. Light verwendet 24.000, Full 120.000 Events. Erzeugung und Abarbeitung liegen innerhalb der Messzeit.</p>
<h2>State Changes</h2>
<p>Die Zustandsänderungen verteilen sich auf 400 Entitäten im Light- und 1.000 Entitäten im Full-Profil. Jedes Ereignis erhält neue alte und neue Home-Assistant-State-Objekte mit wechselnden Werten und Attributen. Alle registrierten Entity-Listener werden tatsächlich angesprochen.</p>
<h2>Entity-Verarbeitung und JSON</h2>
<p>Entity-Verarbeitung kombiniert Include-/Exclude-Filter und ID-Prüfung. 80 % der IDs stammen aus einem wiederkehrenden Arbeitsbestand, 20 % sind neu. JSON erzeugt in jedem Batch neue State-Objekte und Attribute.</p>
<h2>Parallele Core-Last</h2>
<p>Bis zu zwei Worker im Light- und vier Worker im Full-Profil erzeugen und serialisieren gleichzeitig frische State-Objekte in getrennten Prozessen. Prozessstart und Modulimport liegen außerhalb der Messzeit. Diese Kategorie bildet Mehrkern-Kapazität für gleichzeitig laufende HA-nahe Aufgaben und Apps ab; sie behauptet nicht, dass der ereignisgesteuerte Core selbst multithreaded arbeitet.</p>
<h2>Recorder-Speicher und API</h2>
<p>Der SQLite-Test verwendet WAL und synchronous=FULL. Innerhalb der Speicherkategorie gelten: Schreiben 25 %, Commit-p95 40 %, zufälliges Lesen-p95 20 %, Checkpoint 15 %. Die API-Kategorie misst die mediane Antwortzeit der laufenden HA-Instanz. Light verwendet 6 MiB/100 Commits/1.000 Reads; Full 64 MiB/1.000 Commits/5.000 Reads.</p>
<h2>Berechnung</h2>
<p>Durchsatzindex = 100 × Messwert / Green-Referenz. Latenzindex = 100 × Green-Referenz / Messwert. Der Smartdomo Index ist das gewichtete geometrische Mittel. Temperatur, Energie und Linux PSI bleiben reine Diagnosewerte.</p>
<h2>Kalibrierung und Vergleichbarkeit</h2>
<p>Methodik-ID: <strong>CORE-2026.9.1-R4</strong>. Verwendet wurden die Mediane von fünf vollständigen Green-Läufen je Profil. Mit der veröffentlichten Ganzzahlberechnung lagen die resultierenden Gesamtindizes der Referenzserie bei Light zwischen 98 und 101 sowie bei Full zwischen 99 und 101. Der längere erste Light-Gesamtlauf wurde nicht ausgeschlossen, da seine bewerteten Einzelmetriken plausibel waren und die Gesamtdauer nicht in den Index eingeht.</p>
<p>Rangliste und Gerätevergleich trennen R4 und R3 strikt nach Methodik, Kalibrierung und Profil. Drei kompatible Läufe erhalten ein Qualitätskennzeichen; dies verbessert die Wiederholbarkeit, ist aber keine unabhängige Hardware-Verifikation.</p>`;
const en=`
<h1>Benchmark methodology R4</h1>
<h2>Status</h2>
<p>R4 is calibrated from five Light and five Full runs on Home Assistant Green. Reference <strong>GREEN-CORE-2026-09-D</strong> uses Home Assistant Core 2026.9.1, HAOS 18.2 and Supervisor 2026.09.0. R4 is not comparable with R3 because its workloads changed substantially.</p>
<h2>Revision goal</h2>
<p>R4 measures defined Home Assistant performance rather than general suitability. Workloads represent installations with hundreds of entities and combine recurring with new data, substantially reducing the influence of pure Python cache hits. Device price, installed-base statistics and suitability classes are outside R4.</p>
<h2>Weights</h2>${weights}
<p>The weights are fixed and published. They are not adjusted for manufacturers or desired rankings.</p>
<h2>Core events</h2>
<p>Eight event types with varying payloads are generated and fully processed in bounded bursts. Light uses 24,000 and Full 120,000 events. Creation and processing are both inside the timed interval.</p>
<h2>State changes</h2>
<p>State changes are distributed across 400 entities in Light and 1,000 in Full. Every event receives new old and new Home Assistant State objects with varying values and attributes. All registered entity listeners are exercised.</p>
<h2>Entity processing and JSON</h2>
<p>Entity processing combines include/exclude filtering and ID validation. 80% of IDs come from a recurring working set and 20% are new. Every JSON batch creates new State objects and attributes.</p>
<h2>Parallel Core load</h2>
<p>Up to two workers in Light and four in Full concurrently create and serialize fresh State objects in separate processes. Process startup and module import are outside the timed interval. This category captures multicore capacity for concurrent HA-adjacent work and apps; it does not claim that the event-driven Core itself is multithreaded.</p>
<h2>Recorder storage and API</h2>
<p>The SQLite test uses WAL and synchronous=FULL. Inside storage: write throughput 25%, commit p95 40%, random-read p95 20%, checkpoint 15%. API measures median response time of the live HA instance. Light uses 6 MiB/100 commits/1,000 reads; Full uses 64 MiB/1,000 commits/5,000 reads.</p>
<h2>Calculation</h2>
<p>Throughput index = 100 × measured value / Green reference. Latency index = 100 × Green reference / measured value. The Smartdomo Index is the weighted geometric mean. Temperature, energy and Linux PSI remain diagnostic only.</p>
<h2>Calibration and comparison</h2>
<p>Methodology ID: <strong>CORE-2026.9.1-R4</strong>. References are the medians of five complete Green runs per profile. With the released integer calculation, resulting overall indices in the reference series ranged from 98 to 101 for Light and 99 to 101 for Full. The longer first Light run was retained because its scored metrics were plausible and total duration does not affect the index.</p>
<p>The ranking and device comparison strictly separate R4 and R3 by methodology, calibration and profile. Three compatible runs receive a quality marker; this improves repeatability but is not independent hardware verification.</p>`;
function render(){document.documentElement.lang=language.value;document.getElementById('back').textContent=language.value==='de'?'Zurück':'Back';document.getElementById('method').innerHTML=language.value==='de'?de:en}language.onchange=()=>{localStorage.setItem('ha-benchmark-language',language.value);render()};render();
