"""Erzeugt den Wochenbericht als eigenständige HTML-Seite aus results.json."""
from __future__ import annotations

import json
from pathlib import Path

_CSS = (Path(__file__).with_name("report.css")).read_text(encoding="utf-8")

TEMPLATE = r"""<title>Sortiments Scout Vitalabo</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=Source+Sans+3:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>__CSS__</style>

<div class="wrap">
  <header class="top">
    <div class="eyebrow" id="h-eyebrow"></div>
    <h1>Sortiments Scout Vitalabo</h1>
    <p class="lede">Wöchentlicher Vorschlag für den Einkauf: welche Nahrungsergänzungs-Marken sich am Markt nachweislich gut verkaufen, bei Vitalabo aber fehlen, und welche Wirkstoffe gerade als Trend aufkommen.</p>
    <div class="facts" id="h-facts"></div>
    <div class="mockbanner" id="nollm" hidden>Testlauf ohne KI: Marken sind grob per Heuristik erkannt, Fit und Trends nicht bewertet.</div>
  </header>

  <nav class="tabs" role="tablist">
    <button role="tab" data-tab="marken">Marken-Lücken<span class="count" id="c-m"></span></button>
    <button role="tab" data-tab="trends">Trends<span class="count" id="c-t"></span></button>
    <button role="tab" data-tab="gefuehrt">Bereits geführt<span class="count" id="c-g"></span></button>
    <button role="tab" data-tab="methode">So funktioniert's</button>
    <button role="tab" data-tab="annahmen">Annahmen &amp; Fragen</button>
  </nav>

  <section data-panel="marken">
    <div class="intro">
      <h2>Marken mit gemessener Nachfrage, die Vitalabo nicht führt</h2>
      <p class="muted" id="m-intro"></p>
    </div>
    <div class="toolbar"><div class="legend"><span><i style="background:var(--c-demand)"></i>Nachfrage (gemessen)</span><span><i style="background:var(--c-ecom)"></i>E-Commerce-Fit</span><span><i style="background:var(--c-fit)"></i>niceshops-Fit</span></div></div>
    <div class="list" id="list-m"></div>
  </section>

  <section data-panel="trends" hidden>
    <div class="intro">
      <h2>Wirkstoffe und Konzepte in den Listen</h2>
      <p class="muted">Aus jedem Produkttitel extrahiert das Sprachmodell den zentralen Wirkstoff. Viele Neuerscheinungen zu einem Wirkstoff sind ein Frühsignal; ein hoher No-Name-Anteil deutet eher auf einen Hype. „Bei Vitalabo“ zählt Produkte im Export, deren Name die Suchbegriffe enthält: Lücke 0, dünn 1–9, abgedeckt ab 10. Varianten wie „Kreatin Monohydrat“ werden unter „Kreatin“ zusammengefasst.</p>
    </div>
    <div class="tablewrap"><table>
      <thead><tr><th>Wirkstoff / Konzept</th><th style="text-align:right">Produkte</th><th style="text-align:right">davon neu</th><th style="text-align:right">No-Name</th><th>Bei Vitalabo</th><th>Einschätzung</th><th class="col-int">Interesse 24 Monate</th></tr></thead>
      <tbody id="tbl-t"></tbody>
    </table></div>
  </section>

  <section data-panel="gefuehrt" hidden>
    <div class="intro">
      <h2>Starke Marken, die Vitalabo bereits führt</h2>
      <p class="muted">Gegenprobe für den Abgleich: Diese Marken stehen ebenfalls in den Listen und wurden korrekt als geführt erkannt, auch wenn Amazon den Namen übersetzt.</p>
    </div>
    <div class="tablewrap"><table>
      <thead><tr><th>Marke in den Listen</th><th>Bei Vitalabo als</th><th style="text-align:right">Produkte</th><th style="text-align:right">Bester Rang</th><th style="text-align:right">Bewertungen</th></tr></thead>
      <tbody id="tbl-g"></tbody>
    </table></div>
  </section>

  <section data-panel="methode" hidden>
    <div class="prose">
      <section>
        <h2>Täglich sammeln, wöchentlich auswerten</h2>
        <div class="flow">
          <div class="fcol"><span class="tag">täglich</span>
            <div class="fbox">Amazon.de Bestseller + Neuerscheinungen<small>Vitamine, Mineralien &amp; Ergänzungsmittel · Apify</small></div>
            <div class="fbox">iHerb Top-Seller<small>Supplements · im Prototyp manuell</small></div>
            <div class="fbox dashed">weitere Signale<small>z. B. Suchen ohne Treffer, Keepa</small></div></div>
          <div class="farrow">→</div>
          <div class="fcol"><span class="tag">wöchentlich</span>
            <div class="fbox">KI normalisiert<small>Marke, Wirkstoff, Warengruppe</small></div>
            <div class="fbox">Verdichten über 7 Tage<small>Rang, Beständigkeit, Bewertungen</small></div></div>
          <div class="farrow">→</div>
          <div class="fcol"><span class="tag">Abgleich</span>
            <div class="fbox">Vitalabo-Bestand<small>Export + Markenliste der Website</small></div>
            <div class="fbox">KI bewertet Fit<small>mit Websuche und Quellen</small></div></div>
          <div class="farrow">→</div>
          <div class="fcol"><span class="tag">Ergebnis</span>
            <div class="fbox accent">Priorisierte Liste für den Einkauf<small>dieser Bericht</small></div></div>
        </div>
      </section>
      <section>
        <h2>Ablauf der wöchentlichen Auswertung</h2>
        <ol class="steps">
          <li><div><b>Signale laden</b>Alle Tagesstände der letzten 7 Tage aus jeder Quelle.</div></li>
          <li><div><b>Normalisieren</b>Ein günstiges Modell liest jeden Produkttitel und liefert Marke, Wirkstoff, Suchbegriffe und Warengruppe. Das ist nötig, weil Amazon Marken teils übersetzt („Double Heart“ ist Doppelherz) und viele Titel keine klare Struktur haben.</div></li>
          <li><div><b>Verdichten</b>Pro Produkt und Marke: bester Rang je Liste, an wie vielen Tagen in der Liste, Bewertungsanzahl. Daraus entsteht die Signalstärke.</div></li>
          <li><div><b>Abgleichen</b>Marken gegen Export und Markenliste von vitalabo.at; Wirkstoffe über Suchbegriffe gegen die Produktnamen im Export.</div></li>
          <li><div><b>Fit bewerten</b>Ein starkes Modell mit Websuche recherchiert für die stärksten Lücken Hersteller, Vertriebsweg und Beziehbarkeit und bewertet E-Commerce- und niceshops-Fit. Für Trends schätzt es ein: echter Trend oder Hype, regulatorische Risiken.</div></li>
          <li><div><b>Priorisieren und berichten</b>Gewichtung im Code, nicht im Modell. Ergebnis als results.json und als diese Seite.</div></li>
        </ol>
      </section>
      <section>
        <h2>Wie priorisiert wird</h2>
        <pre id="formula"></pre>
        <ul>
          <li><b>Nachfrage (gemessen):</b> Signalstärke der Marke relativ zur stärksten Lücke der Woche. Pro Produkt zählt der Rang relativ zur Listenlänge, Bestseller voll, Neuerscheinungen zu 80 %, multipliziert mit dem Anteil der Tage, an denen es in der Liste stand.</li>
          <li><b>E-Commerce-Fit:</b> versandfähig, nicht apotheken- oder verschreibungspflichtig, Wiederkauf und Abo-Eignung, Warenkorbwert.</li>
          <li><b>niceshops-Fit:</b> Premium oder Nische, ergänzt statt kannibalisiert, als Händler beziehbar, passt zur Zielgruppe.</li>
        </ul>
      </section>
      <section>
        <h2>Betrieb und Übertragbarkeit</h2>
        <p>Zwei Befehle: <code>--step collect</code> täglich, <code>--step weekly</code> wöchentlich. In der niceshops-Infrastruktur würde ich beides als Container-Job laufen lassen (z. B. Google Cloud Run Jobs mit Cloud Scheduler), Schlüssel im Secret Manager, den Bericht als Digest in Slack oder Teams. Alles Shop-Spezifische steht in einer Konfigurationsdatei: Positionierung, Amazon-Kategorie, Quellen, Export-Spalten, Gewichte, Modelle. Ein neuer Shop braucht eine neue Datei, keinen neuen Code.</p>
      </section>
      <section>
        <h2>Dieser Lauf</h2>
        <dl class="kv" id="runinfo"></dl>
      </section>
    </div>
  </section>

  <section data-panel="annahmen" hidden>
    <div class="prose">
      <section>
        <h2>Annahmen</h2>
        <ul>
          <li><b>Umfang:</b> Für das MVP nur Nahrungsergänzung (Vitamine, Mineralien, Ergänzungsmittel), keine Sport- und Diätnahrung.</li>
          <li><b>Nachfrage-Proxy:</b> Amazon.de-Bestseller- und Neuheitenlisten sowie die iHerb-Top-Seller. Ränge sind keine Stückzahlen; die Bewertungsanzahl dient als grober Mengen-Hinweis.</li>
          <li><b>Track Record:</b> Dieser Bericht beruht auf einer einzigen Momentaufnahme. Beständigkeit und Aufsteiger werden erst mit täglichen Ständen messbar; der Code ist dafür ausgelegt.</li>
          <li><b>Bestand:</b> Der Export ist ein Teilsortiment. Als geführt gilt eine Marke, wenn sie im Export oder auf vitalabo.at/marken steht.</li>
          <li><b>Beziehbarkeit:</b> Hohe Nachfrage heißt nicht, dass eine Marke an Händler liefert. Reine Direktvertriebs- oder Amazon-Marken werden im niceshops-Fit abgewertet und als „Beziehbarkeit unklar“ markiert.</li>
          <li><b>Amazon ist nicht der Gesamtmarkt:</b> Premiummarken mit Apotheken- oder Therapeutenvertrieb sind dort unterrepräsentiert.</li>
          <li><b>iHerb:</b> Die Top 10 sind im Prototyp manuell erfasst; ein automatischer Abruf ist noch nicht nachgewiesen (Bot-Schutz).</li>
        </ul>
      </section>
      <section>
        <h2>Erkenntnisse aus dem Bau</h2>
        <ul>
          <li>Die Amazon-Kategorie „Nahrungsergänzung“ ist in Wahrheit Sport- und Diätnahrung. Vitamine liegen in einer eigenen Kategorie.</li>
          <li>Die Liste „Movers &amp; Shakers“ liefert mit dem Scraper auf amazon.de keine Daten. Tägliche Momentaufnahmen ersetzen sie: Aufsteiger werden aus dem Rangverlauf berechnet.</li>
          <li>Der Scraper liefert Seiten teils doppelt; die Pipeline dedupliziert nach Liste und Rang.</li>
          <li>Amazon übersetzt Markennamen. Ein reiner Textabgleich würde Doppelherz als Lücke melden; deshalb normalisiert ein Sprachmodell.</li>
        </ul>
      </section>
      <section>
        <h2>Fragen an eure Expert:innen</h2>
        <div class="qgroup"><h3>Einkauf</h3><ul>
          <li>Gibt es Marken, die bewusst nicht gelistet oder ausgelistet wurden? Die gehören als Sperrliste in die Konfiguration.</li>
          <li>Welche Kriterien entscheiden über eine Listung: Marge, Mindestmenge, Exklusivität, Distributor?</li>
          <li>Liefern Direktvertriebsmarken wie natural elements oder Sunday Natural überhaupt an Händler, oder gab es schon Kontakt?</li>
        </ul></div>
        <div class="qgroup"><h3>Daten</h3><ul>
          <li>Kann der Scout auf Shop-Suchen ohne Treffer zugreifen? Das wäre das stärkste Signal für latente Nachfrage der eigenen Kund:innen.</li>
          <li>Gibt es eine interne Warengruppenstruktur und Umsatz je Warengruppe?</li>
          <li>Gibt es Lizenzen für Keepa, Sistrix oder ähnliche Marktdaten?</li>
        </ul></div>
        <div class="qgroup"><h3>Regulatorik und Prozess</h3><ul>
          <li>Welche Wirkstoffe sind tabu oder heikel (Novel Food, Health Claims, Höchstmengen je Land)?</li>
          <li>Wer arbeitet mit dem Bericht, und in welchem Kanal soll er ankommen? Wie viele Vorschläge pro Woche sind prüfbar?</li>
        </ul></div>
      </section>
      <section>
        <h2>Nächste Schritte</h2>
        <ol>
          <li><b>Betrieb:</b> Täglicher Sammler und wöchentliche Auswertung als geplanter Job, Kostenlimit, Digest in den Team-Kanal.</li>
          <li><b>Bessere Amazon-Daten:</b> Keepa-API (ab 49 € pro Monat) liefert Kaufzähler, Rangverlauf und 30/90-Tage-Durchschnitte; das tägliche Scrapen entfällt.</li>
          <li><b>Eigene Signale:</b> Suchen ohne Treffer, Search Console, Kundenanfragen.</li>
          <li><b>Feedback-Schleife:</b> Der Einkauf markiert Vorschläge als gelistet, abgelehnt oder beobachten. Das speist die Sperrliste und kalibriert die Gewichte. Erfolgsmaß: Anteil gelisteter Vorschläge und deren Umsatz nach 3 Monaten.</li>
          <li><b>Rollout:</b> weitere Kategorien, Märkte (Amazon.fr, .it) und Shops über die Konfiguration.</li>
        </ol>
      </section>
    </div>
  </section>

  <footer id="foot"></footer>
</div>

<script>
const DATA = __DATA__;
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const m = DATA.meta, sm = DATA.summary;
const fmtDate = d => new Date(d + "T12:00:00").toLocaleDateString("de-AT", {day: "2-digit", month: "2-digit", year: "numeric"});
const nf = v => v == null ? "–" : Number(v).toLocaleString("de-AT");
const LIST = {"new-releases": "Neuerscheinungen", "bestsellers": "Bestseller", "topsellers": "Top-Seller"};
const SRC = {"amazon": "Amazon.de", "iherb": "iHerb"};

$("#h-eyebrow").textContent = `KW ${m.week} · ${fmtDate(m.date)}`;
const srcTxt = Object.entries(m.signals).map(([k, v]) => `${SRC[k] || k} ${v.items}`).join(", ");
$("#h-facts").innerHTML = [[nf(sm.n_relevant), "Supplements in den Listen"], [sm.n_brands, "Marken erkannt"],
  [DATA.brand_gaps.length, "Marken-Lücken bewertet"], [DATA.trends.length, "Wirkstoffe"], [sm.days, sm.days === 1 ? "Tagesstand" : "Tagesstände"]]
  .map(([v, l]) => `<span><b>${esc(v)}</b> ${esc(l)}</span>`).join("");
if (!m.llm) $("#nollm").hidden = false;
$("#c-m").textContent = DATA.brand_gaps.length; $("#c-t").textContent = DATA.trends.length; $("#c-g").textContent = DATA.brands_carried.length;
$("#m-intro").textContent = `Von ${sm.n_brands} Marken in den Listen (${srcTxt} Einträge) führt Vitalabo ${sm.n_brands_carried}. ` +
  `Auf sie entfallen ${sm.share_signal_carried} % der gemessenen Signalstärke; der Rest liegt bei Marken, die fehlen. Zeile öffnen für Belege, Vertriebsweg und Begründung.`;

function spark(vals, w = 110, h = 26) {
  if (!vals || vals.length < 2) return "";
  const max = Math.max(...vals), min = Math.min(...vals), r = max - min || 1, n = vals.length;
  const pts = vals.map((v, i) => [2 + i * (w - 4) / (n - 1), 3 + (h - 6) * (1 - (v - min) / r)]);
  const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" "), l = pts[n - 1];
  return `<svg class="spark" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-label="Verlauf über ${n} Monate"><path class="ar" d="${d} L${l[0].toFixed(1)} ${h} L2 ${h} Z"></path><path class="ln" d="${d}"></path><circle class="pt" cx="${l[0].toFixed(1)}" cy="${l[1].toFixed(1)}" r="3.5"><title>${nf(vals[n - 1])} Aufrufe im letzten Monat</title></circle></svg>`;
}
const pct = v => v == null ? "" : `<span class="delta ${v >= 0 ? "up" : "down"}">${v >= 0 ? "+" : "−"}${Math.abs(v)} %</span>`;
const bar = (v, c, l) => `<div class="bar" title="${l}: ${v}/5"><span style="width:${v * 20}%;background:var(${c})"></span></div>`;
const host = u => { try { return new URL(u).hostname.replace(/^www\./, ""); } catch (e) { return u; } };

$("#list-m").innerHTML = DATA.brand_gaps.map(b => { const f = b.fit || {}, sc = f.scores || {};
  const bez = f.beziehbar ? `<span class="chip ${f.beziehbar === "ja" ? "new" : "low"}">beziehbar: ${esc(f.beziehbar)}</span>` : "";
  return `<details class="item"><summary>
    <span class="rank">${b.rank}</span>
    <span class="who"><span class="name">${esc(b.brand)}</span>
      <span class="chips"><span class="chip">${esc(b.category)}</span>${b.sources.map(s => `<span class="chip amz">${SRC[s] || s}</span>`).join("")}<span class="chip">${b.n_products} ${b.n_products === 1 ? "Produkt" : "Produkte"}${b.n_new ? `, ${b.n_new} neu` : ""}</span>${bez}${b.fit_estimated ? `<span class="chip low">Fit nicht bewertet</span>` : ""}</span></span>
    <div class="scorebox"><div class="prio" title="Priorität 0–100">${b.priority}</div>${bar(b.score_demand, "--c-demand", "Nachfrage")}${bar(b.score_ecommerce, "--c-ecom", "E-Commerce-Fit")}${bar(b.score_niceshops, "--c-fit", "niceshops-Fit")}</div>
  </summary><div class="body">
    ${f.beschreibung ? `<p>${esc(f.beschreibung)}</p>` : ""}${f.begruendung ? `<p>${esc(f.begruendung)}</p>` : ""}
    <div class="grid3">
      <div class="crit" style="border-top-color:var(--c-demand)"><span class="k">Nachfrage · gemessen</span><span class="v">${b.score_demand}/5</span><span>Bester Rang ${b.best_rank}, ${nf(b.reviews)} Bewertungen, Signalstärke ${b.signal}</span></div>
      <div class="crit" style="border-top-color:var(--c-ecom)"><span class="k">E-Commerce-Fit</span><span class="v">${b.score_ecommerce}/5</span><span>${esc((sc.ecommerce_fit || {}).grund || "nicht bewertet (Standardwert 3)")}</span></div>
      <div class="crit" style="border-top-color:var(--c-fit)"><span class="k">niceshops-Fit</span><span class="v">${b.score_niceshops}/5</span><span>${esc((sc.niceshops_fit || {}).grund || "nicht bewertet (Standardwert 3)")}</span></div>
    </div>
    <dl class="kv">
      ${f.vertrieb ? `<dt>Vertrieb</dt><dd>${esc(f.vertrieb)}</dd>` : ""}${f.herkunft ? `<dt>Herkunft</dt><dd>${esc(f.herkunft)}</dd>` : ""}
      <dt>In den Listen</dt><dd><ul class="prodlist">${b.products.map(p => `<li><a href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.name.slice(0, 95))}</a> <span class="muted mono">${SRC[p.source]} ${Object.entries(p.best).map(([l, r]) => `${LIST[l] || l} #${r}`).join(" · ")}${p.reviews ? ` · ${nf(p.reviews)} Bew.` : ""}</span></li>`).join("")}</ul></dd>
      ${(f.quellen || []).length ? `<dt>Quellen</dt><dd><div class="src">${f.quellen.map(u => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(host(u))}</a>`).join("")}</div></dd>` : ""}
    </dl>
  </div></details>`; }).join("") || `<p class="muted">Keine Lücken in dieser Woche.</p>`;

const COV = {"Lücke": "low", "dünn": "", "abgedeckt": "new"};
const hasInt = DATA.trends.some(t => t.interest);
$("#tbl-t").innerHTML = DATA.trends.map(t => { const a = t.assessment || {}, i = t.interest;
  return `<tr><td><b>${esc(t.term)}</b><br><span class="muted" style="font-size:.85rem">${esc((t.products[0] || {}).name?.slice(0, 80) || "")}</span></td>
  <td class="n">${t.n_products}</td><td class="n">${t.n_new}</td><td class="n">${Math.round(t.no_name_share * 100)} %</td>
  <td><span class="chip ${COV[t.coverage]}">${esc(t.coverage)}</span> <span class="muted mono">${t.vitalabo_hits}</span></td>
  <td>${a.einschaetzung ? `<b>${esc(a.einschaetzung)}</b> · ${esc(a.empfehlung || "")}<br><span class="muted" style="font-size:.85rem">${esc(a.begruendung || "")}${a.regulatorik && a.regulatorik !== "–" ? ` Regulatorik: ${esc(a.regulatorik)}` : ""}</span>` : `<span class="muted">–</span>`}</td>
  ${hasInt ? `<td>${i ? `<div class="trendcell">${spark(i.values)}${pct(i.growth_12m)}</div>` : `<span class="muted">–</span>`}</td>` : ""}</tr>`; }).join("");
if (!hasInt) document.querySelectorAll(".col-int").forEach(e => e.remove());

$("#tbl-g").innerHTML = DATA.brands_carried.map(b => `<tr><td>${esc(b.brand)}</td><td>${esc(b.carried_as)}</td><td class="n">${b.n_products}</td><td class="n">${b.best_rank}</td><td class="n">${nf(b.reviews)}</td></tr>`).join("");

const w = m.weights;
$("#formula").textContent = `Priorität = (${w.demand} × Nachfrage + ${w.ecommerce_fit} × E-Commerce-Fit + ${w.niceshops_fit} × niceshops-Fit − 1) / 4 × 100`;
const st = m.stats || {};
$("#runinfo").innerHTML = [
  ["Stichtag", `${fmtDate(m.date)} (KW ${m.week}), Fenster ${m.window_days} Tage`],
  ["Signale", Object.entries(m.signals).map(([k, v]) => `${SRC[k] || k}: ${v.items} Einträge aus ${v.dates.length} ${v.dates.length === 1 ? "Tagesstand" : "Tagesständen"}`).join("; ")],
  ["Amazon-Kategorie", esc(m.amazon_category)],
  ["Vitalabo-Bestand", `${nf(m.vitalabo_products)} Produkte im Export, ${m.vitalabo_brands} Marken (Export + Website)`],
  ["Modelle", m.models ? `Normalisierung <span class="mono">${esc(m.models.classify)}</span>, Recherche <span class="mono">${esc(m.models.research)}</span>` : "keine (Testlauf)"],
  ["API-Aufrufe", m.stats ? `${st.calls} (${st.cached} aus Cache), ca. ${Number(st.cost_usd).toFixed(2)} USD` : "–"],
].map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");
$("#foot").textContent = `Prototyp für die Bewerbung als KI Enabler:in bei niceshops · erzeugt am ${fmtDate(m.date)}. Vorschläge sind Empfehlungen zur Prüfung durch den Einkauf.`;

const tabs = [...document.querySelectorAll("[role=tab]")];
function show(n) { tabs.forEach(t => t.setAttribute("aria-selected", t.dataset.tab === n)); document.querySelectorAll("[data-panel]").forEach(p => p.hidden = p.dataset.panel !== n); }
tabs.forEach(t => t.addEventListener("click", () => { show(t.dataset.tab); try { history.replaceState(null, "", "#" + t.dataset.tab); } catch (e) {} }));
show(tabs.some(t => t.dataset.tab === location.hash.slice(1)) ? location.hash.slice(1) : "marken");
</script>
"""

HEAD = '<!doctype html>\n<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'


def render(results: dict, full_document: bool = True) -> str:
    data = json.dumps(results, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.replace("__CSS__", _CSS).replace("__DATA__", data)
    if not full_document:
        return page
    return HEAD + page.replace('<div class="wrap">', '</head><body>\n<div class="wrap">', 1) + "\n</body></html>\n"
