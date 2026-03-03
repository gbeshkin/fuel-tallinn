import json
from pathlib import Path

DATA = Path("docs/data/prices.json")
OUT = Path("docs/index.html")

def badge(trend: str, delta):
    if delta is None:
        return "<span class='same'>● —</span>"
    if trend == "up":
        return f"<span class='up'>▲ +{delta:.3f}</span>"
    if trend == "down":
        return f"<span class='down'>▼ {delta:.3f}</span>"
    return "<span class='same'>● 0.000</span>"

def cell(price, trend: str, delta):
    if price is None:
        return "<span class='same'>—</span>"
    return f"<span class='cell'><span class='price'>{float(price):.3f}</span><span class='delta'>{badge(trend, delta)}</span></span>"

HTML = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Fuel prices — Tallinn</title>

  <!-- Leaflet (карта) -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

  <style>
    :root {{
      --border:#ddd;
      --muted:#555;
      --bghead:#f6f6f6;
      --up:#b00020;
      --down:#0a7a0a;
      --same:#666;
    }}

    body {{
      font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial;
      margin: 24px;
    }}

    .wrap {{
      max-width: 980px;
    }}

    .topbar {{
      display:flex;
      justify-content:space-between;
      align-items:flex-start;
      gap:12px;
      flex-wrap: wrap;
    }}

    h1 {{
      margin: 0;
      font-size: 44px;
      line-height: 1.05;
    }}

    .lang {{
      display:flex;
      gap:8px;
      align-items:center;
    }}

    .lang button {{
      padding:8px 12px;
      border:1px solid var(--border);
      background:white;
      border-radius:10px;
      cursor:pointer;
      font-weight:600;
    }}

    .lang button.active {{
      background: #111;
      color: #fff;
      border-color: #111;
    }}

    .meta {{
      color: var(--muted);
      margin: 14px 0 16px;
      line-height: 1.5;
      font-size: 16px;
    }}

    .section-title {{
      margin: 14px 0 8px;
      font-weight: 800;
      font-size: 18px;
    }}

    #map {{
      height: 360px;
      width: 100%;
      border:1px solid var(--border);
      border-radius: 14px;
      overflow: hidden;
    }}

    table {{
      border-collapse: collapse;
      width:100%;
      margin-top: 16px;
    }}
    th, td {{
      border:1px solid var(--border);
      padding:12px 12px;
      text-align:left;
      vertical-align: middle;
    }}
    th {{
      background: var(--bghead);
      font-size: 18px;
    }}
    td {{
      font-size: 18px;
    }}
    .num {{
      text-align:right;
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
      width: 160px;
    }}

    .cell {{
      display:inline-flex;
      gap:10px;
      align-items: baseline;
      justify-content:flex-end;
      width:100%;
    }}
    .price {{
      font-weight: 700;
    }}
    .delta {{
      font-size: 12px;
    }}
    .up {{ color: var(--up); }}
    .down {{ color: var(--down); }}
    .same {{ color: var(--same); }}

    .cards {{
      display:none;
      margin-top: 14px;
      gap: 12px;
    }}
    .card {{
      border:1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      background: #fff;
    }}
    .card h3 {{
      margin: 0 0 12px 0;
      font-size: 18px;
      line-height: 1.2;
    }}
    .grid {{
      display:grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px 12px;
    }}
    .kv {{
      display:flex;
      justify-content:space-between;
      gap: 10px;
      padding: 10px 10px;
      border:1px solid var(--border);
      border-radius: 12px;
      background: #fafafa;
      font-variant-numeric: tabular-nums;
    }}
    .k {{
      color: var(--muted);
      font-weight: 700;
    }}
    .v {{
      text-align:right;
    }}

    @media (max-width: 820px) {{
      h1 {{ font-size: 34px; }}
      th, td {{ font-size: 16px; }}
      .num {{ width: 140px; }}
      #map {{ height: 300px; }}
    }}

    @media (max-width: 620px) {{
      body {{ margin: 16px; }}
      h1 {{ font-size: 30px; }}
      .meta {{ font-size: 14px; }}
      #map {{ height: 240px; }}
      table {{ display:none; }}
      .cards {{ display:flex; flex-direction: column; }}
    }}
  </style>
</head>

<body>
  <div class="wrap">

    <div class="topbar">
      <h1 id="title"></h1>
      <div class="lang">
        <button id="btn-ru" onclick="setLang('ru')">RU</button>
        <button id="btn-et" onclick="setLang('et')">ET</button>
      </div>
    </div>

    <div class="meta">
      <span id="asofLabel"></span>: <b>{as_of}</b><br/>
      <span id="updatedLabel"></span> (UTC): <b>{fetched_at}</b><br/>
      <span id="noteCng"></span>: <span id="cngUnit"></span>
    </div>

    <div class="section-title" id="mapTitle"></div>
    <div id="map"></div>

    <table>
      <thead>
        <tr>
          <th id="stationHeader"></th>
          <th class="num">95</th>
          <th class="num">98</th>
          <th class="num">Diesel</th>
          <th class="num">CNG</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>

    <div class="cards" id="cards">
      {cards}
    </div>

  </div>

<script>
const translations = {{
  ru: {{
    title: "Цены на топливо в Таллинне",
    asof: "Данные “as of”",
    updated: "Обновлено",
    station: "Сеть / станция",
    mapTitle: "Карта заправок",
    cngNote: "CNG",
    cngUnit: "в FuelEst обычно в €/кг"
  }},
  et: {{
    title: "Kütusehinnad Tallinnas",
    asof: "Andmed “seisuga”",
    updated: "Uuendatud",
    station: "Võrk / tankla",
    mapTitle: "Tanklate kaart",
    cngNote: "CNG",
    cngUnit: "FuelEst-is tavaliselt €/kg"
  }}
}}

function setLang(lang) {{
  localStorage.setItem("lang", lang)
  applyLang(lang)
}}

function applyLang(lang) {{
  const t = translations[lang]
  document.documentElement.lang = lang

  document.getElementById("title").innerText = t.title
  document.getElementById("asofLabel").innerText = t.asof
  document.getElementById("updatedLabel").innerText = t.updated
  document.getElementById("stationHeader").innerText = t.station
  document.getElementById("mapTitle").innerText = t.mapTitle
  document.getElementById("noteCng").innerText = t.cngNote
  document.getElementById("cngUnit").innerText = t.cngUnit

  document.getElementById("btn-ru").classList.toggle("active", lang === "ru")
  document.getElementById("btn-et").classList.toggle("active", lang === "et")
}}

const savedLang = localStorage.getItem("lang") || "ru"
applyLang(savedLang)

// ----- Map -----
const stations = {stations_json};

const map = L.map('map').setView([59.4370, 24.7536], 11);

L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors'
}}).addTo(map);

function fmt3(v) {{
  if (v === undefined || v === null || Number.isNaN(v)) return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return "—";
  return n.toFixed(3);
}}

let anyMarker = false;
const bounds = [];

stations.forEach(s => {{
  if (!s.location) return;
  anyMarker = true;

  const p95 = (s.prices && s.prices["95"] !== null) ? fmt3(s.prices["95"]) : "—";
  const p98 = (s.prices && s.prices["98"] !== null) ? fmt3(s.prices["98"]) : "—";
  const diesel = (s.prices && s.prices["diesel"] !== null) ? fmt3(s.prices["diesel"]) : "—";

  const hasCng = (s.prices && s.prices["cng"] !== undefined && s.prices["cng"] !== null);
  const cng = hasCng ? (fmt3(s.prices["cng"]) + " (€/кг)") : "—";

  const popup = `
    <b>${{s.station}}</b><br/>
    95: ${{p95}}<br/>
    98: ${{p98}}<br/>
    Diesel: ${{diesel}}<br/>
    CNG: ${{cng}}
  `;

  const marker = L.marker([s.location.lat, s.location.lon]).addTo(map).bindPopup(popup);
  bounds.push([s.location.lat, s.location.lon]);
}});

if (anyMarker && bounds.length > 1) {{
  map.fitBounds(bounds, {{ padding: [20, 20] }});
}} else {{
  map.setView([59.4370, 24.7536], 11);
}}
</script>

</body>
</html>
"""

def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))

    rows = []
    cards = []

    for it in data["items"]:
        p = it["prices"]
        t = it.get("trends", {})
        d = it.get("deltas", {})

        rows.append(
            "<tr>"
            f"<td>{it['station']}</td>"
            f"<td class='num'>{cell(p.get('95'), t.get('95','new'), d.get('95'))}</td>"
            f"<td class='num'>{cell(p.get('98'), t.get('98','new'), d.get('98'))}</td>"
            f"<td class='num'>{cell(p.get('diesel'), t.get('diesel','new'), d.get('diesel'))}</td>"
            f"<td class='num'>{cell(p.get('cng'), t.get('cng','new'), d.get('cng'))}</td>"
            "</tr>"
        )

        cards.append(
            "<div class='card'>"
            f"<h3>{it['station']}</h3>"
            "<div class='grid'>"
            f"<div class='kv'><div class='k'>95</div><div class='v'>{cell(p.get('95'), t.get('95','new'), d.get('95'))}</div></div>"
            f"<div class='kv'><div class='k'>98</div><div class='v'>{cell(p.get('98'), t.get('98','new'), d.get('98'))}</div></div>"
            f"<div class='kv'><div class='k'>Diesel</div><div class='v'>{cell(p.get('diesel'), t.get('diesel','new'), d.get('diesel'))}</div></div>"
            f"<div class='kv'><div class='k'>CNG</div><div class='v'>{cell(p.get('cng'), t.get('cng','new'), d.get('cng'))}</div></div>"
            "</div>"
            "</div>"
        )

    stations_json = json.dumps(
        [
            {"station": it["station"], "location": it.get("location"), "prices": it["prices"]}
            for it in data["items"]
        ],
        ensure_ascii=False
    )

    OUT.write_text(
        HTML.format(
            as_of=data.get("as_of") or "—",
            fetched_at=data["fetched_at_utc"],
            rows="\n".join(rows),
            cards="\n".join(cards),
            stations_json=stations_json,
        ),
        encoding="utf-8",
    )
    print(f"Rendered {OUT}")

if __name__ == "__main__":
    main()