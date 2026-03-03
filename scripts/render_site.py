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

def cell(price: float, trend: str, delta):
    return f"<span class='cell'><span>{price:.3f}</span><span class='delta'>{badge(trend, delta)}</span></span>"

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
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; }}
    .topbar {{ display:flex; justify-content:space-between; align-items:center; gap:12px; }}
    .lang button {{ margin-left:8px; padding:6px 10px; cursor:pointer; }}
    .meta {{ color:#555; margin:16px 0; line-height:1.5; }}

    #map {{ height: 360px; width: 100%; max-width: 980px; border:1px solid #ddd; border-radius: 10px; }}

    table {{ border-collapse: collapse; width:100%; max-width:980px; margin-top: 16px; }}
    th, td {{ border:1px solid #ddd; padding:10px; text-align:left; vertical-align: middle; }}
    th {{ background:#f6f6f6; }}
    .num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
    .cell {{ display:inline-flex; gap:10px; align-items:baseline; justify-content:flex-end; width:100%; }}
    .delta {{ font-size:12px; }}
    .up {{ color:#b00020; }}
    .down {{ color:#0a7a0a; }}
    .same {{ color:#666; }}
    .section-title {{ margin: 16px 0 8px; font-weight: 700; }}
  </style>
</head>

<body>

<div class="topbar">
  <h1 id="title"></h1>
  <div class="lang">
    <button onclick="setLang('ru')">RU</button>
    <button onclick="setLang('et')">ET</button>
  </div>
</div>

<div class="meta">
  <span id="asofLabel"></span>: <b>{as_of}</b><br/>
  <span id="updatedLabel"></span> (UTC): <b>{fetched_at}</b>
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
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>

<script>
const translations = {{
  ru: {{
    title: "Цены на топливо в Таллинн",
    asof: "Данные “as of”",
    updated: "Обновлено",
    station: "Сеть / станция",
    mapTitle: "Карта заправок"
  }},
  et: {{
    title: "Kütusehinnad Tallinnas",
    asof: "Andmed “seisuga”",
    updated: "Uuendatud",
    station: "Võrk / tankla",
    mapTitle: "Tanklate kaart"
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
}}

const savedLang = localStorage.getItem("lang") || "ru"
applyLang(savedLang)

// ----- Map -----
const stations = {stations_json};

// Tallinn center
const map = L.map('map').setView([59.4370, 24.7536], 11);

L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors'
}}).addTo(map);

let anyMarker = false;

stations.forEach(s => {{
  if (!s.location) return;
  anyMarker = true;
  const lat = s.location.lat;
  const lon = s.location.lon;

  const popup = `
    <b>${{s.station}}</b><br/>
    95: ${{s.prices["95"].toFixed(3)}}<br/>
    98: ${{s.prices["98"].toFixed(3)}}<br/>
    Diesel: ${{s.prices["diesel"].toFixed(3)}}
  `;

  L.marker([lat, lon]).addTo(map).bindPopup(popup);
}});

if (!anyMarker) {{
  // если вдруг координат нет — покажем весь Таллинн без маркеров
  map.setView([59.4370, 24.7536], 11);
}}
</script>

</body>
</html>
"""

def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))

    rows = []
    for it in data["items"]:
        p = it["prices"]
        t = it.get("trends", {})
        d = it.get("deltas", {})
        rows.append(
            "<tr>"
            f"<td>{it['station']}</td>"
            f"<td class='num'>{cell(p['95'], t.get('95','new'), d.get('95'))}</td>"
            f"<td class='num'>{cell(p['98'], t.get('98','new'), d.get('98'))}</td>"
            f"<td class='num'>{cell(p['diesel'], t.get('diesel','new'), d.get('diesel'))}</td>"
            "</tr>"
        )

    stations_json = json.dumps(
        [
            {
                "station": it["station"],
                "location": it.get("location"),
                "prices": it["prices"],
            }
            for it in data["items"]
        ],
        ensure_ascii=False
    )

    OUT.write_text(
        HTML.format(
            as_of=data.get("as_of") or "—",
            fetched_at=data["fetched_at_utc"],
            rows="\n".join(rows),
            stations_json=stations_json,
        ),
        encoding="utf-8",
    )
    print(f"Rendered {OUT}")

if __name__ == "__main__":
    main()
