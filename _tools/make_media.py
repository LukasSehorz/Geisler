#!/usr/bin/env python3
"""Generate src/media.json – image assignments for every page/section."""
import json, os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
G = json.load(open(ROOT / "_data/gallery.json"))
C = json.load(open(ROOT / "_data/content.json"))
IM = {i["file"]: i for i in G["images"]}
REC = G["recommendations"]
REGION = json.load(open(ROOT / "_data/einzugsgebiet.json")) if (ROOT / "_data/einzugsgebiet.json").exists() else {}

def gal(f, alt=None, focus=None):
    i = IM.get(f)
    assert i, f"missing gallery image {f}"
    return {"src": f"gal:{f}", "focus": focus or [i["focus"]["x"], i["focus"]["y"]], "alt": alt or i["alt"], "w": i["width"], "h": i["height"]}

def gen(name, alt, focus=(0.5, 0.5)):
    assert (ROOT / "_gen" / f"{name}.png").exists(), name
    return {"src": f"gen:{name}.png", "focus": list(focus), "alt": alt, "w": 2048, "h": 1152}

def recs(slug):
    out = []
    for r in REC.get("services", {}).get(slug, []):
        f = r["file"] if isinstance(r, dict) else r
        i = IM.get(f)
        if i and not i.get("stock_photo") and not i.get("duplicate_of"):
            out.append(f)
    return out

NAMES = {s["slug"]: s["name"] for s in C["services"]}
NAMES.update({p["slug"]: p["name"] for p in C["smartgarden"]["pages"]})

TILE = {
    "garten-pflege": gen("svc_pflege_portrait", "Frisch geschnittene Buchskugeln und blühende Stauden an einer sauberen Rasenkante"),
    "bepflanzungen": gal("galerie_bepflanzungen__iefe58676240357cc.jpg"),
    "teichanlagen-wasserelemente": gal("galerie_teichanlagen_wasserelemente__ib6a700d535657f12.jpg"),
    "dachbegruenung-regenwassernutzung": gen("svc_dach_portrait", "Blühende Sedum-Dachbegrünung mit Kiesstreifen"),
    "rasen": gen("svc_rasen_portrait", "Dichter, frisch gemähter Rasen im Morgenlicht"),
    "beton-natursteinbelaege": gal("galerie_belagsarbeiten__i165b62483b5aa3b0.jpg"),
    "sichtschutz-zaeune": gal("galerie_sichtschutz_zaun__i50fbc725907fc8c6.jpg"),
    "bagger-erdarbeiten": gen("svc_erdarbeiten_portrait", "Minibagger modelliert frischen Boden auf einer Gartenbaustelle"),
    "hangbefestigung-mauerbau": gal("galerie_hangsicherung_mauerbau__i9870264be2f2fc77.jpg"),
    "treppenanlagen": None,
    "poolbau": gen("svc_pool_portrait", "Poolrand aus hellem Naturstein mit Gräsern im Abendlicht"),
    "maehroboter": gen("svc_maehroboter_portrait", "Mähroboter auf gepflegtem Rasen neben einem Staudenbeet"),
    "bewaesserung": gen("svc_bewaesserung_portrait", "Versenkregner verteilt feine Wassertropfen über den Rasen"),
    "lichtdesign": gen("svc_licht_portrait", "Mehrstämmiger Baum, nachts von einem Gartenstrahler beleuchtet"),
}
HERO = {
    "garten-pflege": gen("svc_pflege_hero", "Gepflegter Garten mit geschnittenen Hecken und blühenden Beeten"),
    "bepflanzungen": gen("svc_bepflanzung_hero", "Üppige Staudenbeete mit Allium, Katzenminze und Gräsern"),
    "teichanlagen-wasserelemente": gen("svc_teich_hero", "Naturteich mit Seerosen und Sandsteinfindlingen"),
    "dachbegruenung-regenwassernutzung": gen("svc_dach_hero", "Blühende extensive Dachbegrünung auf einem Flachdach"),
    "rasen": gen("svc_rasen_hero", "Frisch verlegter Fertigrasen in einem neu angelegten Garten"),
    "beton-natursteinbelaege": gen("svc_belaege_hero", "Terrasse aus großformatigen hellen Natursteinplatten"),
    "sichtschutz-zaeune": gen("svc_sichtschutz_hero", "Sichtschutz aus Gabionen, Holzlamellen und Cortenstahl"),
    "bagger-erdarbeiten": gen("svc_erdarbeiten_hero", "Minibagger bei Erdarbeiten für einen neuen Garten"),
    "hangbefestigung-mauerbau": gen("svc_hang_hero", "Terrassierter Hanggarten mit Sandsteinmauern"),
    "treppenanlagen": gen("svc_treppen_hero", "Breite Gartentreppe aus Naturstein zwischen Gräsern"),
    "poolbau": gen("svc_pool_hero", "Pool mit Natursteinumrandung in einem gestalteten Garten"),
    "maehroboter": gen("svc_maehroboter_hero", "Mähroboter auf einem gepflegten Rasen im Abendlicht"),
    "bewaesserung": gen("svc_bewaesserung_hero", "Automatische Rasenbewässerung am frühen Morgen"),
    "lichtdesign": gen("svc_licht_hero", "Beleuchteter Garten zur blauen Stunde"),
}
EXTRA = {  # generated fallbacks for shifted images / feature
    "garten-pflege": ["svc_pflege_portrait"], "dachbegruenung-regenwassernutzung": ["svc_dach_portrait"],
    "rasen": ["svc_rasen_portrait"], "bagger-erdarbeiten": ["svc_erdarbeiten_portrait"],
    "poolbau": ["svc_pool_detail", "svc_pool_portrait"], "maehroboter": ["svc_maehroboter_portrait"],
    "bewaesserung": ["svc_bewaesserung_portrait"], "lichtdesign": ["svc_licht_detail", "svc_licht_portrait"],
}

def build_service(slug):
    r = recs(slug)
    hires = [f for f in r if IM[f]["width"] >= 1400]
    tile = TILE.get(slug) or (gal(hires[0]) if hires else gal(r[0]))
    TILE[slug] = tile
    images, feature, slider = [], None, []
    pool = [f for f in hires if f"gal:{f}" != tile["src"]] + [f for f in hires if f"gal:{f}" == tile["src"]]
    for f in pool:
        if len(images) < 2: images.append(gal(f))
    gens = EXTRA.get(slug, [])
    for gname in gens:
        if len(images) < 2 and f"gen:{gname}.png" != tile["src"]:
            images.append(gen(gname, NAMES[slug]))
    for gname in gens:
        if len(images) < 2:
            images.append(gen(gname, NAMES[slug]))
    if len(images) < 2:
        images.append(tile)
    used = {i["src"] for i in images}
    for f in hires:
        if f"gal:{f}" not in used and IM[f].get("portrait_ok"):
            feature = gal(f); break
    if not feature:
        for gname in gens:
            if f"gen:{gname}.png" not in used:
                feature = gen(gname, NAMES[slug]); break
    if not feature:
        feature = tile
    slider = [gal(f) for f in r if IM[f]["width"] >= 2000]
    return {"hero": HERO[slug], "tile": tile, "images": images, "feature": feature, "slider": slider}

services = {s["slug"]: build_service(s["slug"]) for s in C["services"]}
smart = {p["slug"]: build_service(p["slug"]) for p in C["smartgarden"]["pages"]}
services["poolbau"]["images"] = [gen("svc_pool_detail", "Sandsteinwand mit Schwallwasser über einem Pool"), gen("svc_pool_portrait", "Poolrand aus hellem Naturstein mit Gräsern")]
services["poolbau"]["feature"] = gen("svc_pool_hero", "Pool mit Natursteinumrandung und Sandsteinmauer im Abendlicht", (0.42, 0.6))
services["poolbau"]["slider"] = []
smart["lichtdesign"]["images"] = [gen("svc_licht_detail", "Natursteinstufen mit integrierter LED-Stufenbeleuchtung"), gen("svc_licht_portrait", "Beleuchteter Baum und Gräser bei Nacht")]
smart["lichtdesign"]["slider"] = []
smart["lichtdesign"]["feature"] = gen("svc_licht_portrait", "Beleuchteter Baum und Gräser bei Nacht")
smart["maehroboter"]["images"] = [gen("svc_maehroboter_portrait", "Mähroboter neben einem Staudenbeet"), gen("svc_rasen_portrait", "Dichter Rasen im Morgenlicht")]
smart["bewaesserung"]["images"] = [gen("svc_bewaesserung_portrait", "Versenkregner im Gegenlicht"), gal("galerie_bepflanzungen__i1f0405c633a45b1d.jpg")]

# never show the feature image twice on a detail page: fall back to a portrait crop of the hero
for group in (services, smart):
    for slug, v in group.items():
        if v["feature"]["src"] in {i["src"] for i in v["images"]}:
            h = v["hero"]
            v["feature"] = {**h, "focus": [0.5, 0.58]}

HOME_USED = {t["src"] for t in TILE.values() if t} | {
    "gal:galerie_bepflanzungen__i40a2c7788ae4896d.jpg", "gal:galerie_sichtschutz_zaun__i2bdb6a7ffdb4198a.jpg",
    "gal:galerie_bepflanzungen__i1f0405c633a45b1d.jpg", "gal:galerie_bepflanzungen__i59de44877f9e306f.jpg",
    "gal:galerie_bepflanzungen__i42bf4141ecff4e35.jpg", "gal:unsere_gaerten__i99a1f086519e5b01.jpg",
    "gal:galerie_bepflanzungen__i8a5079ae951f6f57.jpg", "gal:galerie_belagsarbeiten__i637bbf9020cd919f.jpg",
    "gal:galerie_hangsicherung_mauerbau__i84ca8c988c745380.jpg", "gal:galerie_hangsicherung_mauerbau__i66504980e7052caa.jpg"}
# gallery category covers
cats = C["gallery"]["categories"]
covers = []
for key, name in cats.items():
    items = [i for i in G["images"] if i.get("include_in_gallery") and i.get("category") == key]
    if not items: continue
    ranked = sorted(items, key=lambda i: (i["quality"], i["width"]), reverse=True)
    fresh = [i for i in ranked if f"gal:{i['file']}" not in HOME_USED]
    best = (fresh or ranked)[0]
    HOME_USED.add(f"gal:{best['file']}")
    covers.append({"cat": key, "name": name, "count": len(items), **gal(best["file"])})

towns = [t["name"] for t in REGION.get("towns", []) if t.get("name") != "Eschau"][:12] or [
    "Aschaffenburg", "Miltenberg", "Obernburg am Main", "Elsenfeld", "Erlenbach am Main", "Klingenberg am Main",
    "Wörth am Main", "Großostheim", "Mespelbrunn", "Heimbuchenthal", "Amorbach", "Kleinwallstadt"]

map_file = ROOT / "site/assets/img/map/einzugsgebiet-2400.webp"
region_media = [{"src": "site:map/einzugsgebiet-2400.webp", "focus": [0.55, 0.5], "alt": "Karte des Einzugsgebiets rund um Eschau im Landkreis Miltenberg"}] if map_file.exists() else [gen("hero_A2", "Garten im Spessart")]

media = {
    "home": {
        "hero_video": {"desktop": "assets/video/hero-1920.mp4", "tablet": "assets/video/hero-1280.mp4", "mobile": "assets/video/hero-mobile.mp4", "poster": "assets/video/hero-poster.jpg"},
        "about_left": gal("galerie_bepflanzungen__i40a2c7788ae4896d.jpg"),
        "about_right": gal("galerie_sichtschutz_zaun__i2bdb6a7ffdb4198a.jpg"),
        "services_rows": [["bepflanzungen", "garten-pflege", "rasen"], ["beton-natursteinbelaege", "treppenanlagen", "hangbefestigung-mauerbau"], ["sichtschutz-zaeune", "dachbegruenung-regenwassernutzung", "bagger-erdarbeiten"]],
        "water": ["poolbau", "teichanlagen-wasserelemente"],
        "smart_media": [{"video": "assets/video/smart-portrait.mp4", "poster": "assets/video/smart-portrait-poster.jpg", "alt": "Beleuchteter Garten zur blauen Stunde"}, gen("svc_maehroboter_portrait", "Mähroboter auf gepflegtem Rasen")],
        "smart_video_wide": {"video": "assets/video/smart-1280.mp4", "poster": "assets/video/smart-portrait-poster.jpg"},
        "career_media": [gal("galerie_hangsicherung_mauerbau__i84ca8c988c745380.jpg"), gal("galerie_hangsicherung_mauerbau__i66504980e7052caa.jpg")],
        "region_media": region_media,
        "towns": towns,
        "projects": [gal("unsere_gaerten__i99a1f086519e5b01.jpg"), gal("galerie_bepflanzungen__i8a5079ae951f6f57.jpg"), gal("galerie_belagsarbeiten__i637bbf9020cd919f.jpg")],
        "promise_media": [gal("galerie_bepflanzungen__i1f0405c633a45b1d.jpg"), gal("galerie_bepflanzungen__i59de44877f9e306f.jpg")],
        "footer_image": gal("galerie_bepflanzungen__i42bf4141ecff4e35.jpg"),
        "gallery_cards": covers,
    },
    "services": services,
    "smart": smart,
    "pages": {
        "services_overview": gen("svc_hang_hero", "Terrassierter Hanggarten mit Sandsteinmauern", (0.5, 0.55)),
        "smart_overview": gen("smartgarden_hero", "Garten in der Abenddämmerung mit Beleuchtung und Mähroboter"),
        "gallery": gal("galerie_bepflanzungen__i8a5079ae951f6f57.jpg"),
        "contact": gen("hero_kontakt", "Eingangsweg aus Natursteinplatten zu einem modernen Wohnhaus"),
        "about": gen("owners_composite", "Stefan Opolka und Stefan Weis, Inhaber von Gartengestaltung Geißler, in einem Garten", (0.69, 0.4)),
        "about_mobile": gen("owners_composite_portrait", "Stefan Opolka und Stefan Weis, Inhaber von Gartengestaltung Geißler, in einem Garten"),
        "about_portraits": [gal("kontakt_ansprechpartner__i301500a0b13eef88.jpg", alt="Stefan Weis") if "kontakt_ansprechpartner__i301500a0b13eef88.jpg" in IM else None,
                             gal("kontakt_ansprechpartner__i131dd466bceb1b2e.jpg", alt="Stefan Opolka") if "kontakt_ansprechpartner__i131dd466bceb1b2e.jpg" in IM else None],
        "career": gal("stellenangebote__i16387a75cf17060a.jpg", alt="Team von Gartengestaltung Geißler"),
        "legal": gen("svc_belaege_hero", "Natursteinterrasse"),
        "hero_A1": gen("hero_A1", "Gestalteter Garten im Abendlicht"),
    },
}
(ROOT / "src/media.json").write_text(json.dumps(media, ensure_ascii=False, indent=1), encoding="utf-8")
print("media.json written;", len(services), "services;", len(covers), "gallery covers; region:", region_media[0]["src"])
for k, v in services.items():
    print(f"  {k:36} tile={v['tile']['src'][:48]:48} imgs={[i['src'][4:30] for i in v['images']]} slider={len(v['slider'])}")
