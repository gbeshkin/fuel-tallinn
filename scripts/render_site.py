import json
from pathlib import Path

DATA = Path("docs/data/prices.json")
OUT = Path("docs/index.html")

def badge(trend: str, delta):
    if trend == "up":
        return f"<span class='up'>▲ +{delta:.3f}</span>"
    if trend == "down":
        return f"<span class='down'>▼ {delta:.3f}</span>"
    if trend == "same":
        return "<span class='same'>● 0.000</span>"
    if trend == "new":
        return "<span class='new'>● new</span>"
    return ""

HTML = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Цены на топливо — Таллинн</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; }}
    .meta {{ color: #555; margin-bottom: 16px; line-height: 1.5; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 980px; }}
    th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; vertical-align: middle; }}
    th {{ background: #f6f6f6; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
    .cell {{ display: inline-flex; gap: 10px; align-items: baseline; justify-content: flex-end; width: 100%; }}
    .delta {{ font-size: 12px; }}
    .up {{ color: #b00020; }}
    .down {{ color: #0a7a0a; }}
    .same {{ color: #666; }}
    .new {{ color: #666; }}
  </style>
</head>
<body>
  <h1>Цены на топливо — Таллинн</h1>
  <div class="meta">
    Источник: <a href="{source}">{source}</a><br/>
    Данные “as of”: <b>{as_of}</b><br/>
    Обновлено (UTC): <b>{fetched_at}</b>
  </div>

  <table>
    <thead>
      <tr>
        <th>Сеть / станция</th>
        <th class="num">95</th>
        <th class="num">98</th>
        <th class="num">Diesel</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</body>
</html>
"""

def cell(price: float, trend: str, delta):
    if delta is None:
        return f"<span class='cell'><span>{price:.3f}</span><span class='delta new'>● —</span></span>"
    return f"<span class='cell'><span>{price:.3f}</span><span class='delta'>{badge(trend, delta)}</span></span>"

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

    OUT.write_text(
        HTML.format(
            source=data["source"],
            as_of=data.get("as_of") or "—",
            fetched_at=data["fetched_at_utc"],
            rows="\n".join(rows),
        ),
        encoding="utf-8",
    )
    print(f"Rendered {OUT}")

if __name__ == "__main__":
    main()