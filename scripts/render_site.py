import json
from pathlib import Path

DATA = Path("docs/data/prices.json")
OUT = Path("docs/index.html")

HTML = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Fuel prices — Tallinn</title>

  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; }}
    .topbar {{ display:flex; justify-content:space-between; align-items:center; }}
    .lang button {{ margin-left:8px; padding:6px 10px; cursor:pointer; }}
    .meta {{ color:#555; margin:16px 0; line-height:1.5; }}
    table {{ border-collapse: collapse; width:100%; max-width:980px; }}
    th, td {{ border:1px solid #ddd; padding:10px; text-align:left; }}
    th {{ background:#f6f6f6; }}
    .num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
    .up {{ color:#b00020; }}
    .down {{ color:#0a7a0a; }}
    .same {{ color:#666; }}
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
  <span id="sourceLabel"></span>: <a href="{source}">{source}</a><br/>
  <span id="asofLabel"></span>: <b>{as_of}</b><br/>
  <span id="updatedLabel"></span> (UTC): <b>{fetched_at}</b>
</div>

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
    station: "Сеть / станция"
  }},
  et: {{
    title: "Kütusehinnad Tallinn",
    asof: "Andmed “seisuga”",
    updated: "Uuendatud",
    station: "Võrk / tankla"
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
  document.getElementById("sourceLabel").innerText = t.source
  document.getElementById("asofLabel").innerText = t.asof
  document.getElementById("updatedLabel").innerText = t.updated
  document.getElementById("stationHeader").innerText = t.station
}}

const savedLang = localStorage.getItem("lang") || "ru"
applyLang(savedLang)
</script>

</body>
</html>
"""

def badge(trend, delta):
    if delta is None:
        return "●"
    if trend == "up":
        return f"<span class='up'>▲ +{delta:.3f}</span>"
    if trend == "down":
        return f"<span class='down'>▼ {delta:.3f}</span>"
    return "<span class='same'>● 0.000</span>"

def cell(price, trend, delta):
    return f"{price:.3f} {badge(trend, delta)}"

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
            f"<td class='num'>{cell(p['95'], t.get('95'), d.get('95'))}</td>"
            f"<td class='num'>{cell(p['98'], t.get('98'), d.get('98'))}</td>"
            f"<td class='num'>{cell(p['diesel'], t.get('diesel'), d.get('diesel'))}</td>"
            "</tr>"
        )

    OUT.write_text(
        HTML.format(
            source=data["source"],
            as_of=data.get("as_of") or "—",
            fetched_at=data["fetched_at_utc"],
            rows="\n".join(rows),
        ),
        encoding="utf-8",
    )

if __name__ == "__main__":
    main()
