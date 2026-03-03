import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

URL_1182 = "https://www.1182.ee/fuelprices"
OUT = Path("docs/data/prices.json")

STATION_COORDS = {
    "Krooning Hiiu Pärnu mnt 327a": {"lat": 59.3779, "lon": 24.6666},
    "Alexela Ehitajate tee 114c": {"lat": 59.4247, "lon": 24.6813},
    "Olerex Laki 29": {"lat": 59.4258, "lon": 24.7230},
    "Circle K Sõpruse pst. 200b": {"lat": 59.4036, "lon": 24.7373},
}

def _clean_num(s: str) -> Optional[float]:
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    s = s.replace(",", ".")
    cleaned = re.sub(r"[^0-9.]", "", s)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None

def _trend(delta: Optional[float], eps: float = 0.0005) -> str:
    if delta is None:
        return "new"
    if delta > eps:
        return "up"
    if delta < -eps:
        return "down"
    return "same"

def _load_prev_prices() -> Dict[str, Dict[str, Any]]:

    prev_by_station: Dict[str, Dict[str, Any]] = {}
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8"))
            for it in prev.get("items", []):
                prev_by_station[it["station"]] = it.get("prices", {}) or {}
        except Exception:
            pass
    return prev_by_station

def fetch_1182_items(prev_by_station: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    r = requests.get(URL_1182, timeout=30, headers={"User-Agent": "fuel-tallinn-bot/1.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    text = soup.get_text("\n")
    m = re.search(r"Fuel prices as of\s+([0-9]{1,2}/[0-9]{1,2}/[0-9]{2})", text)
    as_of = m.group(1) if m else None

    table = soup.find("table")
    if not table:
        raise RuntimeError("Не нашёл <table> на 1182. Возможно изменилась вёрстка.")

    rows: List[List[str]] = []
    for tr in table.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)

    header = rows[0]
    stations = header[:]
    if stations and stations[0].lower() in ("", "fuel", "fuel prices"):
        stations = stations[1:]

    def row_map(label: str) -> Optional[List[str]]:
        for rr in rows:
            if rr and rr[0].strip().lower() == label.lower():
                return rr[1:]
        return None

    p95 = row_map("95")
    p98 = row_map("98")
    diesel = row_map("Diesel")

    if not (p95 and p98 and diesel):
        raise RuntimeError("Не нашёл строки 95/98/Diesel на 1182. Возможно изменилась таблица.")

    items: List[Dict[str, Any]] = []
    n = min(len(stations), len(p95), len(p98), len(diesel))
    for i in range(n):
        station = stations[i].strip()

        cur = {
            "95": _clean_num(p95[i]),
            "98": _clean_num(p98[i]),
            "diesel": _clean_num(diesel[i]),
        }

        prev_prices = prev_by_station.get(station, {})
        deltas: Dict[str, Optional[float]] = {}
        trends: Dict[str, str] = {}

        for k, v in cur.items():
            if v is None:
                deltas[k] = None
                trends[k] = "new"
                continue
            if k in prev_prices and prev_prices.get(k) is not None:
                try:
                    d = round(float(v) - float(prev_prices[k]), 3)
                except Exception:
                    d = None
                deltas[k] = d
                trends[k] = _trend(d)
            else:
                deltas[k] = None
                trends[k] = "new"

        items.append({
            "station": station,
            "source": "1182",
            "location": STATION_COORDS.get(station),
            "prices": cur,
            "deltas": deltas,
            "trends": trends,
        })

    for it in items:
        it["_as_of_1182"] = as_of

    return items

def _try_parse_json(x: Any) -> Optional[Any]:
    if x is None:
        return None
    if isinstance(x, (dict, list)):
        return x
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except Exception:
            return None
    return None

def _looks_like_station_list(obj: Any) -> bool:

    if not isinstance(obj, list) or len(obj) == 0:
        return False
    if not isinstance(obj[0], dict):
        return False
    keys = set(obj[0].keys())
    return (
        ("address" in keys or "displayName" in keys) and
        (("lat" in keys and "lon" in keys) or ("lat" in keys and "lng" in keys) or ("latitude" in keys))
    )

def _extract_cng_from_station_obj(st: Dict[str, Any]) -> Optional[float]:

    for k in ("cng", "CNG"):
        if k in st:
            return _clean_num(st.get(k))

    for arr_key in ("fuelInfos", "fuels", "prices", "fuelInfo", "fuelPrices"):
        arr = st.get(arr_key)
        if isinstance(arr, list):
            for fi in arr:
                if not isinstance(fi, dict):
                    continue
                name = str(fi.get("name") or fi.get("displayName") or fi.get("fuelTypeName") or "").upper()
                code = str(fi.get("code") or fi.get("fuelCode") or "").upper()
                ftid = str(fi.get("fuelTypeId") or fi.get("typeId") or "")
                if "CNG" in name or code == "CNG" or ftid in ("9",):
                    # цена может быть в price/value/amount
                    for pk in ("price", "value", "amount"):
                        if pk in fi:
                            return _clean_num(fi.get(pk))
    return None

def _is_tallinn_station(st: Dict[str, Any]) -> bool:

    city = str(st.get("city") or st.get("municipality") or st.get("town") or "").lower()
    if "tallinn" in city:
        return True
    addr = str(st.get("address") or st.get("displayName") or st.get("name") or "").lower()
    return "tallinn" in addr


def main():
    prev_by_station = _load_prev_prices()

    items_1182 = fetch_1182_items(prev_by_station)

    as_of_1182 = None
    for it in items_1182:
        as_of_1182 = it.pop("_as_of_1182", None)
        if as_of_1182:
            break


    payload = {
        "source": {
            "1182": URL_1182,
        },
        "as_of": as_of_1182,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "region": "Tallinn",
        "items": items_1182,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {OUT} with {len(payload['items'])} stations (1182={len(items_1182)})")

if __name__ == "__main__":
    main()