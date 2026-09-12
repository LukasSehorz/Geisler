"""Geodata fetching with on-disk cache (OpenStreetMap: Nominatim + Overpass, ODbL).

All raw API responses are stored in ./cache so reruns never hit the APIs again.
"""
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
UA = "GeisslerWebsiteMap/1.0 (build script; Gartengestaltung Geissler website)"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
OVERPASS = "https://overpass-api.de/api/interpreter"

_last_nominatim = [0.0]


def _cache_path(kind, key):
    h = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    safe = "".join(c if c.isalnum() else "_" for c in key)[:60]
    return os.path.join(CACHE, f"{kind}__{safe}__{h}.json")


def _get(url, data=None, timeout=180):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


def nominatim(q, polygon=False, limit=5, extra=None):
    params = {"format": "json", "q": q, "limit": str(limit), "addressdetails": "1"}
    if polygon:
        params.update({"polygon_geojson": "1", "polygon_threshold": "0.0005"})
    if extra:
        params.update(extra)
    url = NOMINATIM + "?" + urllib.parse.urlencode(params)
    path = _cache_path("nominatim", url)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    wait = 1.1 - (time.time() - _last_nominatim[0])
    if wait > 0:
        time.sleep(wait)
    txt = _get(url)
    _last_nominatim[0] = time.time()
    os.makedirs(CACHE, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    return json.loads(txt)


def overpass(query):
    path = _cache_path("overpass", query)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    txt = None
    for attempt in range(4):
        try:
            txt = _get(OVERPASS, data=data, timeout=300)
            break
        except Exception as e:  # rate limit / timeout -> back off
            print("  overpass retry", attempt, e)
            time.sleep(10 * (attempt + 1))
    if txt is None:
        raise RuntimeError("Overpass failed")
    os.makedirs(CACHE, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)
    return json.loads(txt)


# --------------------------------------------------------------------------- boundaries
BOUNDARIES = {
    # key: (query, expected display_name fragment, role)
    "lk_miltenberg": ("Landkreis Miltenberg", "Landkreis Miltenberg", "main"),
    "lk_aschaffenburg": ("Landkreis Aschaffenburg", "Landkreis Aschaffenburg", "service"),
    "st_aschaffenburg": ("Aschaffenburg, Bayern", "Aschaffenburg", "service"),
    # light context
    "lk_main_spessart": ("Landkreis Main-Spessart", "Main-Spessart", "context"),
    "main_kinzig": ("Main-Kinzig-Kreis", "Main-Kinzig-Kreis", "context"),
    "odenwaldkreis": ("Odenwaldkreis", "Odenwaldkreis", "context"),
    "darmstadt_dieburg": ("Landkreis Darmstadt-Dieburg", "Darmstadt-Dieburg", "context"),
    "neckar_odenwald": ("Neckar-Odenwald-Kreis", "Neckar-Odenwald-Kreis", "context"),
    "main_tauber": ("Main-Tauber-Kreis", "Main-Tauber-Kreis", "context"),
    "lk_offenbach": ("Landkreis Offenbach", "Landkreis Offenbach", "context"),
    "bergstrasse": ("Kreis Bergstraße", "Bergstraße", "context"),
    "st_darmstadt": ("Darmstadt, Hessen", "Darmstadt", "context"),
    "st_offenbach": ("Offenbach am Main, Hessen", "Offenbach", "context"),
    "st_frankfurt": ("Frankfurt am Main", "Frankfurt", "context"),
    "wetteraukreis": ("Wetteraukreis", "Wetteraukreis", "context"),
    "lk_wuerzburg": ("Landkreis Würzburg", "Landkreis Würzburg", "context"),
    "vogelsbergkreis": ("Vogelsbergkreis", "Vogelsbergkreis", "context"),
    "lk_bad_kissingen": ("Landkreis Bad Kissingen", "Bad Kissingen", "context"),
    "lk_fulda": ("Landkreis Fulda", "Landkreis Fulda", "context"),
    "rhein_neckar": ("Rhein-Neckar-Kreis", "Rhein-Neckar-Kreis", "context"),
    "gross_gerau": ("Kreis Groß-Gerau", "Groß-Gerau", "context"),
}


def fetch_boundaries():
    out = {}
    for key, (q, frag, role) in BOUNDARIES.items():
        res = nominatim(q, polygon=True, limit=5)
        pick = None
        for r in res:
            gj = r.get("geojson", {})
            if (r.get("class") == "boundary" and r.get("type") == "administrative"
                    and gj.get("type") in ("Polygon", "MultiPolygon")
                    and frag.split(",")[0] in r.get("display_name", "")):
                pick = r
                break
        if not pick:
            print(f"  ! boundary not found: {key} ({q})")
            continue
        out[key] = {"name": pick["name"], "role": role, "geojson": pick["geojson"],
                    "display_name": pick["display_name"]}
    return out


# --------------------------------------------------------------------------- towns
TOWNS = [
    "Eschau", "Aschaffenburg", "Miltenberg", "Obernburg am Main", "Elsenfeld",
    "Erlenbach am Main", "Klingenberg am Main", "Wörth am Main", "Großwallstadt",
    "Kleinwallstadt", "Sulzbach am Main", "Großostheim", "Mömlingen", "Amorbach",
    "Bürgstadt", "Kleinheubach", "Mespelbrunn", "Heimbuchenthal", "Dammbach",
    "Leidersbach", "Mönchberg", "Röllbach", "Faulbach", "Stadtprozelten",
    "Dorfprozelten", "Collenberg", "Weilbach", "Laufach", "Hösbach", "Goldbach",
    "Alzenau",
]
REGION_BBOX = (49.50, 50.15, 8.85, 9.70)  # lat_min, lat_max, lon_min, lon_max
OK_DISTRICTS = ("Landkreis Miltenberg", "Landkreis Aschaffenburg", "Aschaffenburg")


def fetch_place_nodes():
    """Exact village/town centre nodes (place=*) from Overpass, keyed by name."""
    names = "|".join(TOWNS)
    s, n, w, e = REGION_BBOX[0], REGION_BBOX[1], REGION_BBOX[2], REGION_BBOX[3]
    q = f"""[out:json][timeout:120];
node["place"~"^(city|town|village|suburb)$"]["name"~"^({names})$"]({s},{w},{n},{e});
out;"""
    out = {}
    for el in overpass(q).get("elements", []):
        t = el.get("tags", {})
        pop = t.get("population", "").replace(".", "").strip()
        out[t["name"]] = {"lat": el["lat"], "lon": el["lon"], "osm": f'node/{el["id"]}',
                          "place": t.get("place"), "population": int(pop) if pop.isdigit() else 0}
    return out


def fetch_towns():
    towns = []
    nodes = fetch_place_nodes()
    for name in TOWNS:
        res = nominatim(f"{name}, Bayern, Deutschland", limit=8)
        cands = []
        for r in res:
            lat, lon = float(r["lat"]), float(r["lon"])
            dn = r.get("display_name", "")
            if not (REGION_BBOX[0] <= lat <= REGION_BBOX[1] and REGION_BBOX[2] <= lon <= REGION_BBOX[3]):
                continue
            if not any(d in dn for d in OK_DISTRICTS):
                continue
            if r.get("name") != name:
                continue
            # prefer the place node (village centre) over the municipality centroid
            score = 0 if r.get("class") == "place" else 1
            cands.append((score, -float(r.get("importance") or 0), r))
        if not cands:
            print(f"  ! town dropped (no valid geocode): {name}")
            continue
        cands.sort(key=lambda c: (c[0], c[1]))
        r = cands[0][2]
        t = {"name": name, "lat": float(r["lat"]), "lon": float(r["lon"]),
             "osm": f'{r["osm_type"]}/{r["osm_id"]}', "class": r.get("class"),
             "type": r.get("type"), "display_name": r["display_name"], "population": 0}
        node = nodes.get(name)
        # use the place node when it agrees with the verified Nominatim hit (< 6 km apart)
        if node and abs(node["lat"] - t["lat"]) < 0.055 and abs(node["lon"] - t["lon"]) < 0.08:
            t.update({"lat": node["lat"], "lon": node["lon"], "osm": node["osm"],
                      "class": "place", "type": node["place"], "population": node["population"]})
        towns.append(t)
    return towns


def fetch_company():
    res = nominatim("Elsavastraße 3, 63863 Eschau, Deutschland", limit=3)
    for r in res:
        if "Eschau" in r.get("display_name", ""):
            return {"lat": float(r["lat"]), "lon": float(r["lon"]), "display_name": r["display_name"]}
    return None


# --------------------------------------------------------------------------- rivers
RIVER_BBOX = (49.40, 8.35, 50.25, 10.05)  # south, west, north, east (covers both crops)


def fetch_rivers():
    s, w, n, e = RIVER_BBOX
    q_main = f"""[out:json][timeout:180];
way["waterway"="river"]["name"="Main"]({s},{w},{n},{e});
out geom;"""
    q_streams = f"""[out:json][timeout:180];
way["waterway"~"^(river|stream)$"]["name"~"^(Mud|Elsava|Aschaff|Kahl|Gersprenz|Erf|Mümling)$"]({s},{w},{n},{e});
out geom;"""
    main = overpass(q_main)
    streams = overpass(q_streams)

    def lines(res):
        out = []
        for el in res.get("elements", []):
            g = el.get("geometry")
            if g and len(g) > 1:
                out.append({"name": el.get("tags", {}).get("name"),
                            "waterway": el.get("tags", {}).get("waterway"),
                            "coords": [(p["lat"], p["lon"]) for p in g]})
        return out

    return {"main": lines(main), "streams": lines(streams)}


def fetch_all():
    print("Fetching boundaries …")
    b = fetch_boundaries()
    print(f"  {len(b)} boundaries")
    print("Fetching towns …")
    t = fetch_towns()
    print(f"  {len(t)} towns")
    c = fetch_company()
    print("Fetching rivers …")
    r = fetch_rivers()
    print(f"  Main ways: {len(r['main'])}, stream ways: {len(r['streams'])}")
    return {"boundaries": b, "towns": t, "company": c, "rivers": r}


if __name__ == "__main__":
    d = fetch_all()
    for t in d["towns"]:
        print(f'{t["name"]:22s} {t["lat"]:.4f} {t["lon"]:.4f} {t["class"]}/{t["type"]}  {t["display_name"][:70]}')
    print("company", d["company"])
    for k, v in d["boundaries"].items():
        print(k, v["name"], v["geojson"]["type"], v["display_name"][:60])
