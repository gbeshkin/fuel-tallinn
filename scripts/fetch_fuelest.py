import requests
import json
from pathlib import Path
from datetime import datetime, timezone

URL = "https://fuelest.ee/Home/GetLatestPriceData?countryId=1"
OUT = Path("docs/prices.json")

def fetch():
    r = requests.get(URL, timeout=30)
    r.raise_for_status()
    return r.json()["data"]["priceInfo"]

def main():
    rows = fetch()

    stations = {}

    for row in rows:
        address = row.get("address", "")
        if "tallinn" not in address.lower():
            continue

        sid = row["stationId"]

        st = stations.setdefault(sid, {
            "station": row["displayName"],
            "source": "fuelest",
            "location": {
                "lat": None,
                "lon": None
            },
            "prices": {},
            "deltas": {},
            "trends": {}
        })

        fuel = row["name"].lower()
        price = row["price"]

        if "95" in fuel:
            key = "95"
        elif "98" in fuel:
            key = "98"
        elif "diisel" in fuel:
            key = "diesel"
        elif "cng" in fuel:
            key = "cng"
        else:
            continue

        st["prices"][key] = price
        st["deltas"][key] = 0.0
        st["trends"][key] = "same"

    payload = {
        "source": {"fuelest": URL},
        "as_of": datetime.now().strftime("%-m/%-d/%y"),
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "region": "Tallinn",
        "items": list(stations.values())
    }

    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("Saved:", len(payload["items"]), "stations")

if __name__ == "__main__":
    main()