import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://www.1182.ee/fuelprices"
OUT = Path("docs/data/prices.json")

def _clean_num(s: str):
    s = s.strip().replace(",", ".")
    return float(re.sub(r"[^0-9.]", "", s))

def _trend(delta: float, eps: float = 0.0005):
    # eps ~ половина тысячной, чтобы не мигало на микросдвигах парсинга/форматирования
    if delta > eps:
        return "up"
    if delta < -eps:
        return "down"
    return "same"

def main():
    # загрузим предыдущие данные (если есть)
    prev_by_station = {}
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8"))
            for it in prev.get("items", []):
                prev_by_station[it["station"]] = it.get("prices", {})
        except Exception:
            prev_by_station = {}

    r = requests.get(URL, timeout=30, headers={"User-Agent": "fuel-tallinn-bot/1.0"})
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    text = soup.get_text("\n")
    m = re.search(r"Fuel prices as of\s+([0-9]{1,2}/[0-9]{1,2}/[0-9]{2})", text)
    as_of = m.group(1) if m else None

    table = soup.find("table")
    if not table:
        raise RuntimeError("Не нашёл <table> на странице. Возможно изменилась вёрстка.")

    rows = []
    for tr in table.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)

    header = rows[0]
    stations = header[:]
    if stations and stations[0].lower() in ("", "fuel", "fuel prices"):
        stations = stations[1:]

    def row_map(label: str):
        for rr in rows:
            if rr and rr[0].strip().lower() == label.lower():
                return rr[1:]
        return None

    p95 = row_map("95")
    p98 = row_map("98")
    diesel = row_map("Diesel")

    if not (p95 and p98 and diesel):
        raise RuntimeError("Не нашёл строки 95/98/Diesel. Возможно изменилась таблица.")

    items = []
    n = min(len(stations), len(p95), len(p98), len(diesel))
    for i in range(n):
        station = stations[i]
        cur = {
            "95": _clean_num(p95[i]),
            "98": _clean_num(p98[i]),
            "diesel": _clean_num(diesel[i]),
        }
        prev_prices = prev_by_station.get(station, {})

        deltas = {}
        trends = {}
        for k in ("95", "98", "diesel"):
            if k in prev_prices:
                d = round(cur[k] - float(prev_prices[k]), 3)
                deltas[k] = d
                trends[k] = _trend(d)
            else:
                deltas[k] = None
                trends[k] = "new"

        items.append({
            "station": station,
            "prices": cur,
            "deltas": deltas,   # разница к прошлому запуску
            "trends": trends,   # up/down/same/new
        })

    payload = {
        "as_of": as_of,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "region": "Tallinn",
        "items": items,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {OUT} with {len(items)} stations")

if __name__ == "__main__":
    main()
