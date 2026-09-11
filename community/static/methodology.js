'use strict';
const language=document.getElementById('language'),queryLanguage=new URLSearchParams(location.search).get('lang'),saved=localStorage.getItem('ha-benchmark-language'),browser=(navigator.languages?.[0]||navigator.language||'en').toLowerCase();
language.value=['de','en'].includes(queryLanguage)?queryLanguage:['de','en'].includes(saved)?saved:browser.startsWith('de')?'de':'en';
function theme(){document.documentElement.dataset.theme=matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light'}theme();matchMedia('(prefers-color-scheme:dark)').addEventListener('change',theme);
const weights=`<div class="table-wrap"><table><thead><tr><th>Category / Kategorie</th><th>Weight / Anteil</th></tr></thead><tbody><tr><td>Core events</td><td>15 %</td></tr><tr><td>State changes</td><td>20 %</td></tr><tr><td>Entity processing</td><td>5 %</td></tr><tr><td>Fresh JSON states</td><td>10 %</td></tr><tr><td>Recorder storage</td><td>20 %</td></tr><tr><td>API latency</td><td>10 %</td></tr><tr><td>Parallel Core load</td><td>20 %</td></tr></tbody></table></div>`;
const de=`
<h1>Benchmark-Methodik R4</h1>
<h2>Status</h2>
<p>R4 ist mit fünf Light- und fünf Full-Läufen auf einem Home Assistant Green kalibriert. Die Referenz <strong>GREEN-CORE-2026-09-D</strong> basiert auf Home Assistant Core 2026.9.1, HAOS 18.2 und Supervisor 2026.09.0.</p>
<h2>Ziel und Aussagekraft</h2>
<p>Der Benchmark misst die Rechen- und Speicherleistung für sieben klar definierte Home-Assistant-nahe Arbeitslasten. Er bildet keine vollständige Installation mit individuellen Integrationen, Automationen und Apps nach. Der Smartdomo Index beschreibt daher Leistungsreserven unter diesen Testbedingungen, nicht die allgemeine Eignung eines Geräts für jeden Haushalt.</p>
<p>Die Arbeitsbestände umfassen hunderte synthetische Entitäten und kombinieren wiederkehrende mit neu erzeugten Daten. Dadurch dominieren reine Cache-Treffer das Ergebnis weniger stark. Preis, Energieeffizienz, Marktverbreitung und Langzeitzuverlässigkeit fließen nicht in den Index ein.</p>
<h2>Gewichtung</h2>${weights}
<p>Die veröffentlichten Gewichte sind für diese Methodik fest. Der Recorder-nahe Speichertest, State-Events und die parallele Last erhalten zusammen 60 %, weil Speicherreaktionen, Zustandsverarbeitung und gleichzeitig laufende Prozesse für größere Home-Assistant-Systeme besonders relevant sind.</p>
<h2>Core Events</h2>
<p>Eine isolierte Home-Assistant-Core-Instanz registriert für jeden von acht synthetischen Ereignistypen einen Callback. Der Test erzeugt 24.000 Events im Light- beziehungsweise 120.000 Events im Full-Profil. Sequenznummer, Entity-ID und Wert ändern sich bei jedem Event. Nach jeweils 1.000 Events wartet der Test, bis die Event-Warteschlange abgearbeitet ist. Erzeugung und Callback-Verarbeitung liegen vollständig innerhalb der Messzeit.</p>
<p>Die Kategorie misst den Durchsatz des HA-Event-Bus unter kontrollierten Bedingungen. Recorder, WebSocket-Übertragung und reale Integrationen sind dabei nicht aktiv.</p>
<h2>State Changes</h2>
<p>Der Test erzeugt synthetische <code>state_changed</code>-Events für 400 Entity-IDs im Light- und 1.000 Entity-IDs im Full-Profil. Für jedes Event werden zwei neue State-Objekte angelegt: eines repräsentiert den vorherigen Zustand (<code>old_state</code>), das andere den neuen Zustand (<code>new_state</code>). Zustandswert und Sequenzattribut ändern sich fortlaufend.</p>
<p>Ein Callback überwacht den gesamten Entity-Bestand. Zusätzlich sind 14 kleinere Entity-Gruppen registriert, deren Callbacks einen typischen Zugriff auf Zustand und Attribute ausführen. Da der Test zyklisch alle Entity-IDs verwendet, wird jede dieser 14 Gruppen während des Laufs angesprochen. Es handelt sich jedoch nicht um vollständige Automationen: Der echte HA-Zustandsautomat, der Recorder und WebSocket-Updates werden durch diesen Test nicht ausgeführt.</p>
<h2>Entity-Verarbeitung und JSON</h2>
<p>Die Entity-Verarbeitung führt pro Durchlauf zwei Core-Funktionen aus: die Prüfung eines Include-/Exclude-Filters und die Validierung der Entity-ID. 80 % der IDs stammen aus einem wiederkehrenden Arbeitsbestand; 20 % werden neu erzeugt. Angezeigt werden vollständig bearbeitete Prüfpaarungen pro Sekunde.</p>
<p>Der JSON-Test erzeugt in jedem Batch neue Home-Assistant-State-Objekte samt Attributen und serialisiert anschließend die gesamte Liste mit dem JSON-Encoder von Home Assistant. Gemessen werden Objekterzeugung und Serialisierung gemeinsam.</p>
<h2>Parallele Core-Last</h2>
<p>Der Test nutzt höchstens zwei Prozesse im Light- und vier Prozesse im Full-Profil, jedoch nie mehr als verfügbare logische CPUs. Jeder Prozess erzeugt und serialisiert eigene State-Objekte. Prozessstart, Modulimport und ein kurzer Aufwärmlauf erfolgen vor der Zeitmessung.</p>
<p>Die Kategorie misst den kombinierten Mehrprozess-Durchsatz. Sie macht damit zusätzliche CPU-Kerne sichtbar, wie sie parallel laufenden Apps oder anderen Prozessen zugutekommen können. Sie misst nicht den Home-Assistant-Event-Loop selbst und sagt nicht aus, dass einzelne Core-Aufgaben automatisch mehrere Kerne nutzen.</p>
<h2>Recorder-naher Speicher</h2>
<p>Der Test legt auf dem App-Datenlaufwerk eine temporäre SQLite-Datenbank mit State-ähnlichen Datensätzen und Index an. Verwendet werden WAL-Modus, <code>synchronous=FULL</code>, deaktivierte automatische Checkpoints und viele explizite Transaktionen. Light schreibt 6 MiB Nutzdaten in 100 Commits und führt 1.000 zufällige Primärschlüssel-Lesezugriffe aus; Full verwendet 64 MiB, 1.000 Commits und 5.000 Lesezugriffe.</p>
<p>Der Speicherindex kombiniert Schreibdurchsatz (25 %), Commit-Latenz p95 (40 %), Random-Read-Latenz p95 (20 %) und Dauer des abschließenden WAL-Checkpoints (15 %). Vor den Lesezugriffen fordert der Test das Betriebssystem auf, die Datei aus dem Cache zu nehmen. Das ist nur eine Best-Effort-Anforderung und garantiert keine physisch kalten Lesezugriffe.</p>
<p>Der Test bildet wichtige Recorder-Eigenschaften nach, verwendet aber nicht Home Assistants echten Recorder. Er misst weder Lebensdauer noch Stromausfallsicherheit des Speichermediums.</p>
<h2>HA API</h2>
<p>Diese Kategorie ist als einzige direkt mit der laufenden Home-Assistant-Instanz verbunden. Sie misst die vollständige Antwortzeit mehrerer authentifizierter Aufrufe des Core-API-Endpunkts aus dem App-Container und verwendet den Median. Light führt 10, Full 30 Aufrufe aus. Das Ergebnis enthält neben der Core-Reaktion auch den lokalen Supervisor-/Container-Netzwerkpfad.</p>
<h2>Berechnung</h2>
<p>Jede Rohmetrik wird zunächst auf Home Assistant Green = 100 normiert. Für Durchsatzwerte gilt <code>100 × Messwert / Green-Referenz</code>; für Latenzen gilt <code>100 × Green-Referenz / Messwert</code>. Ein Kategorieindex von 200 bedeutet somit den doppelten Durchsatz oder die halbe Latenz der jeweiligen Green-Referenz – nicht zwangsläufig ein doppelt so schnelles Gesamtsystem.</p>
<p>Der Smartdomo Index ist das gewichtete geometrische Mittel der sieben Kategorieindizes. Dadurch kann ein einzelner sehr hoher Wert eine schwache Kategorie weniger stark überdecken als bei einem arithmetischen Mittel.</p>
<h2>Temperatur, Energie und PSI</h2>
<p>Diese Werte dienen ausschließlich der Einordnung und beeinflussen den Index nicht. Die Temperatur wird während des gesamten Benchmarks über einen konfigurierten HA-Sensor oder – sofern verfügbar – über eine Linux-Temperaturschnittstelle erfasst. Für die elektrische Leistungsaufnahme ist ein konfigurierter HA-Sensor erforderlich. Der Energieverbrauch wird aus dessen Messwerten über die Laufzeit angenähert.</p>
<p>Linux Pressure Stall Information (PSI) gibt an, welcher Anteil der Benchmarkzeit Aufgaben wegen fehlender CPU-Zeit, Arbeitsspeicher oder I/O-Ressourcen warten mussten. PSI misst Wartezeit, nicht die normale Auslastung.</p>
<h2>Kalibrierung und Vergleichbarkeit</h2>
<p>Methodik-ID: <strong>CORE-2026.9.1-R4</strong>. Für Light und Full wurde jeweils der Median aus fünf vollständigen Green-Läufen als Referenz verwendet. Die daraus zurückgerechneten Gesamtindizes lagen bei Light zwischen 98 und 101 und bei Full zwischen 99 und 101.</p>
<p>Vergleichbar sind nur Ergebnisse mit identischer Methodik-ID, Kalibrierungs-ID und identischem Profil. Ein Community-Eintrag aus drei kompatiblen Läufen verwendet deren Median und erhält ein Qualitätskennzeichen. Das verbessert die Wiederholbarkeit, stellt aber keine unabhängige Verifikation der Hardwareangaben dar.</p>`;
const en=`
<h1>Benchmark methodology R4</h1>
<h2>Status</h2>
<p>R4 is calibrated from five Light and five Full runs on one Home Assistant Green. Reference <strong>GREEN-CORE-2026-09-D</strong> is based on Home Assistant Core 2026.9.1, HAOS 18.2 and Supervisor 2026.09.0.</p>
<h2>Purpose and scope</h2>
<p>The benchmark measures compute and storage performance across seven clearly defined Home-Assistant-related workloads. It does not reproduce a complete installation with its individual integrations, automations and apps. The Smartdomo Index therefore describes performance headroom under these test conditions, not universal suitability for every household.</p>
<p>Working sets contain hundreds of synthetic entities and combine recurring with newly generated data, reducing the dominance of pure cache hits. Price, energy efficiency, installed-base statistics and long-term reliability are not part of the index.</p>
<h2>Weights</h2>${weights}
<p>The published weights are fixed for this methodology. Recorder-like storage, state events and parallel load together account for 60%, reflecting the importance of storage response, state processing and concurrently running processes in larger Home Assistant systems.</p>
<h2>Core events</h2>
<p>An isolated Home Assistant Core instance registers one callback for each of eight synthetic event types. The test creates 24,000 events in Light and 120,000 in Full. Sequence number, entity ID and value change with every event. After each 1,000 events, the test waits for the event queue to drain. Event creation and callback processing are both inside the timed interval.</p>
<p>This category measures controlled HA event-bus throughput. Recorder activity, WebSocket delivery and real integrations are not active.</p>
<h2>State changes</h2>
<p>The test creates synthetic <code>state_changed</code> events for 400 entity IDs in Light and 1,000 in Full. Two fresh State objects are created for every event: one represents the previous state (<code>old_state</code>) and the other the new state (<code>new_state</code>). State values and sequence attributes change continuously.</p>
<p>One callback tracks the full entity set. Fourteen smaller entity groups are also registered; their callbacks perform a representative state and attribute lookup. Because the test cycles through every entity ID, each of these groups receives events during the run. These are not complete automations: the real HA state machine, Recorder and WebSocket updates are not executed by this test.</p>
<h2>Entity processing and JSON</h2>
<p>Each entity-processing iteration invokes two Core functions: include/exclude filtering and entity-ID validation. 80% of IDs come from a recurring working set and 20% are newly generated. The reported rate is completed check pairs per second.</p>
<p>For every JSON batch, the test creates fresh Home Assistant State objects and attributes, then serializes the full list with Home Assistant's JSON encoder. Object creation and serialization are timed together.</p>
<h2>Parallel Core load</h2>
<p>The test uses at most two processes in Light and four in Full, never more than the available logical CPUs. Each process creates and serializes its own State objects. Process startup, module import and a short warm-up run occur before timing begins.</p>
<p>This category measures combined multiprocess throughput, exposing CPU capacity that may benefit concurrently running apps or other processes. It does not measure the Home Assistant event loop itself and does not imply that an individual Core task automatically uses multiple cores.</p>
<h2>Recorder-like storage</h2>
<p>The test creates a temporary SQLite database with State-like rows and an index on the app data volume. It uses WAL mode, <code>synchronous=FULL</code>, disabled automatic checkpoints and many explicit transactions. Light writes 6 MiB of payload in 100 commits and performs 1,000 random primary-key reads; Full uses 64 MiB, 1,000 commits and 5,000 reads.</p>
<p>The storage index combines write throughput (25%), commit latency p95 (40%), random-read latency p95 (20%) and final WAL-checkpoint duration (15%). Before reading, the benchmark asks the operating system to evict the file from cache. This is a best-effort request and cannot guarantee physically cold reads.</p>
<p>The workload reproduces important Recorder characteristics but does not run Home Assistant's actual Recorder. It measures neither storage endurance nor power-loss safety.</p>
<h2>HA API</h2>
<p>This is the only category connected directly to the running Home Assistant instance. It measures complete response time for authenticated Core API requests from the app container and reports the median. Light performs 10 requests and Full 30. The result includes the Core response plus the local Supervisor/container network path.</p>
<h2>Calculation</h2>
<p>Each raw metric is first normalized to Home Assistant Green = 100. Throughput metrics use <code>100 × measured value / Green reference</code>; latency metrics use <code>100 × Green reference / measured value</code>. A category index of 200 therefore represents twice the throughput or half the latency of the corresponding Green reference—not necessarily a system that feels twice as fast overall.</p>
<p>The Smartdomo Index is the weighted geometric mean of the seven category indices. Compared with an arithmetic mean, this makes it harder for one exceptionally high result to conceal a weak category.</p>
<h2>Temperature, energy and PSI</h2>
<p>These values provide context only and do not affect the index. Temperature is sampled throughout the benchmark from a configured HA sensor or, where available, a Linux temperature interface. Power requires a configured HA sensor. Energy consumption is approximated by integrating its samples over the run.</p>
<p>Linux Pressure Stall Information (PSI) reports the share of benchmark time during which tasks had to wait for CPU time, memory or I/O resources. PSI measures stalled time, not ordinary utilization.</p>
<h2>Calibration and comparison</h2>
<p>Methodology ID: <strong>CORE-2026.9.1-R4</strong>. The reference for each profile is the median of five complete Green runs. Recalculated overall indices across the source series ranged from 98 to 101 for Light and 99 to 101 for Full.</p>
<p>Results are comparable only when methodology ID, calibration ID and profile match. A community entry based on three compatible runs uses their median and receives a quality marker. This improves repeatability but does not independently verify the submitted hardware information.</p>`;
function render(){document.documentElement.lang=language.value;document.getElementById('back').textContent=language.value==='de'?'Zurück':'Back';document.getElementById('method').innerHTML=language.value==='de'?de:en}language.onchange=()=>{localStorage.setItem('ha-benchmark-language',language.value);render()};render();
