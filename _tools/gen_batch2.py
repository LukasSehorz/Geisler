import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from kie import batch, credits
G = "/Users/jannikvomhofe/Desktop/Webdesign/Galabau Geissler/_research/geissler/img/"
O = "/Users/jannikvomhofe/Desktop/Webdesign/Galabau Geissler/_gen/"
def g(n): return G + n
REG = ("Setting: a private garden of a family home in a village in the Spessart / Lower Main valley region of Bavaria, Germany, built by a premium master landscaping company. "
       "Design language as in the reference photos (use them only as style and material reference, create a new, finished, more beautiful scene): red Main sandstone, light grey large-format stone paving, corten steel accents, gabions, lush perennials and ornamental grasses, manicured lawn. ")
PH = (" Ultra photorealistic high-end architectural garden photography, full-frame camera, natural realistic colour grading with rich but believable greens, beautiful soft light, crisp detail, "
      "calm premium editorial look. No text, no letters, no logos, no brand names, no watermark.")
NOP = " No people."
R_POOL = [g("galerie_bepflanzungen__i6f670683356b5ac1.jpg"), g("galerie_teichanlagen_wasserelemente__ib6a700d535657f12.jpg"), g("galerie_belagsarbeiten__i165b62483b5aa3b0.jpg")]
R_PLANT = [g("galerie_bepflanzungen__i1f0405c633a45b1d.jpg"), g("galerie_bepflanzungen__i59de44877f9e306f.jpg"), g("dienstleistungen__i0b4edef148c1fb8d.jpg")]
R_WALL = [g("galerie_hangsicherung_mauerbau__i832e7703525c139d.jpg"), g("galerie_hangsicherung_mauerbau__i355a5428db175524.jpg"), g("galerie_treppenanlagen__i9ecbaa7f8102f178.jpg")]
R_PAVE = [g("galerie_belagsarbeiten__i0e81325bc915eda8.jpg"), g("galerie_belagsarbeiten__ic06a0c5588cbb73d.jpg"), g("galerie_bepflanzungen__i8a5079ae951f6f57.jpg")]
R_SCREEN = [g("galerie_sichtschutz_zaun__i18d39194c32be562.jpg"), g("galerie_sichtschutz_zaun__i50fbc725907fc8c6.jpg"), g("galerie_teichanlagen_wasserelemente__i2c9b859df9696986.jpg")]
R_WATER = [g("galerie_teichanlagen_wasserelemente__ib6a700d535657f12.jpg"), g("galerie_teichanlagen_wasserelemente__ie6f8f1aededff682.jpg"), g("galerie_teichanlagen_wasserelemente__i2c9b859df9696986.jpg")]
R_ROOF = [g("galerie_dachbegruenung_wasserspeicher__i7a6c9bb8e5a9b951.jpg"), g("dienstleistungen__iec261e977009dd4a.jpg")]
R_EARTH = [g("dienstleistungen__i97caee3182645afb.jpg"), g("stellenangebote__i16387a75cf17060a.jpg")]
R_SMART = [g("smartgarden__iffc487272e591a22.jpg"), g("smartgarden__i9dc49b35b656350e.jpg"), g("smartgarden__i456b0624763ab737.jpg")]
J = []
def add(name, refs, ar, prompt, people=False):
    J.append(dict(dest=O + name + ".png", refs=refs, ar=ar, res="2K", prompt=REG + prompt + ("" if people else NOP) + PH))
# Poolbau
add("svc_pool_hero", R_POOL, "16:9", "A newly built elegant rectangular swimming pool with a slim light natural-stone coping and a light grey large-format stone deck, clear turquoise water, integrated into a lush garden with ornamental grasses, lavender and a red sandstone retaining wall, two modern sun loungers, a modern house in the background and forested hills. Wide composition with calm space in the upper half, warm late afternoon sun.")
add("svc_pool_portrait", R_POOL, "3:4", "Vertical composition: close view along the edge of an elegant swimming pool with light natural stone coping, crystal clear water with sunlight caustics, soft ornamental grasses and a corten steel planter beside the pool deck, golden hour.")
add("svc_pool_detail", R_POOL, "3:4", "Vertical composition: a natural stone stepping path leading to a modern pool with a sandstone wall and a slim sheet waterfall pouring into the pool, lush green planting, bright summer afternoon.")
# Pflege
add("svc_pflege_hero", R_PLANT, "16:9", "An immaculately maintained mature garden in early summer morning light: freshly and precisely trimmed hedges and topiary balls, crisp clean lawn edges, weed-free mulched perennial beds in full bloom, pruned roses and hydrangeas, a light grey stone path; a pair of professional pruning shears and a woven harvest basket with clippings rest on a sandstone wall in the foreground.")
add("svc_pflege_portrait", R_PLANT, "3:4", "Vertical composition: close-up of perfectly clipped boxwood balls and flowering perennials (catmint, salvia, white hydrangea) along a freshly edged lawn and a sandstone border, soft morning light, dew drops.")
# Rasen
add("svc_rasen_hero", R_PLANT, "16:9", "A brand-new, perfectly even, lush emerald green lawn in a freshly landscaped private garden, a few rolls of fresh roll-out turf still lying at the edge with the last strips being laid, clean curved lawn edge against a light grey stone path and a young perennial bed, soft morning backlight.")
add("svc_rasen_portrait", R_PLANT, "3:4", "Vertical composition: low camera angle just above an extremely dense, lush, freshly mown striped lawn with dew in the early morning backlight, blurred garden with trees and a house in the background.")
# Erdarbeiten
add("svc_erdarbeiten_hero", R_EARTH, "16:9", "A clean, well organised garden construction site: a modern compact tracked mini excavator in neutral grey and dark green without any logo is precisely levelling fresh brown soil for a new garden next to a new family house; string lines, wooden stakes and a laser level mark the future terrace; piles of gravel and red sandstone blocks wait on the side; forested Spessart hills in the background, bright sunny day with clouds.")
add("svc_erdarbeiten_portrait", R_EARTH, "3:4", "Vertical composition: close view of the bucket of a compact mini excavator (no logos) carefully shaping fresh soil in a garden construction site, sandstone blocks and gravel in the background, bright sunlight.")
# Dachbegruenung
add("svc_dach_hero", R_ROOF, "16:9", "An extensive green roof on a modern flat-roofed garage and bungalow extension, densely planted with flowering sedum in green, red and pink tones, low grasses and wild thyme, a neat gravel edge strip and a slim anthracite roof edge, bees on the flowers; view from a slightly elevated garden position, a lush garden below and forested hills behind, soft summer afternoon light.")
add("svc_dach_portrait", R_ROOF, "3:4", "Vertical composition: close-up of a flowering sedum green roof (red, pink, yellow blossoms) with a gravel strip and a rain gutter leading into a corten steel rain barrel in a garden below, soft light.")
# Lichtdesign
add("svc_licht_hero", R_WATER, "16:9", "The same kind of premium garden at blue hour just after sunset: warm white LED uplights illuminate a multi-stem tree and ornamental grasses, subtle bollard lights line a light grey stone path, the corten steel water basin and sheet waterfall glow from below, a warmly lit terrace with lounge furniture and a gently flickering fire bowl, deep blue evening sky, the house windows softly lit. Magical but realistic, long exposure feel.")
add("svc_licht_portrait", R_WATER, "3:4", "Vertical composition: at night, a slender multi-stem tree dramatically uplit by a warm garden spotlight, backlit ornamental grasses and a sandstone wall with integrated warm LED step lights, dark blue sky.")
add("svc_licht_detail", R_WATER, "3:4", "Vertical composition: blue hour, natural sandstone garden steps with integrated warm LED step lights leading up to an illuminated terrace, lavender and grasses along the steps glowing softly.")
# Bewaesserung
add("svc_bewaesserung_hero", R_SMART, "16:9", "Early morning in a beautiful private garden: several pop-up lawn sprinklers spray fine arcs of water across a lush green lawn, the water droplets sparkle in golden backlight, perennial borders and a sandstone wall frame the lawn, a large tree casts soft shadows.")
add("svc_bewaesserung_portrait", R_SMART, "3:4", "Vertical composition: macro-like close-up of a modern pop-up sprinkler head spraying a fine fan of water over dense green grass, glittering droplets in warm backlight.")
# Maehroboter
add("svc_maehroboter_hero", R_SMART, "16:9", "A sleek modern robotic lawn mower in anthracite with a small green accent and absolutely no logo or brand name, working on a perfectly even green lawn in a premium private garden with perennial borders, a sandstone wall and a light grey terrace, soft late afternoon light, calm and tidy.")
add("svc_maehroboter_portrait", R_SMART, "3:4", "Vertical composition: low angle close view of an anthracite robotic lawn mower (no logo, no brand) on a lush lawn next to a flowering perennial border, shallow depth of field, warm evening light.")
# Smart Garden overview
add("smartgarden_hero", R_SMART, "16:9", "A premium garden at dusk combining smart garden technology: warm garden lighting just switched on along paths and in trees, a robotic lawn mower (no logo) resting in its discreet charging station under a small wooden roof, fine sprinkler mist over the lawn in the last golden light, modern house with large glass windows glowing warmly.")
# Real service categories: premium heroes
add("svc_bepflanzung_hero", R_PLANT, "16:9", "Lush, richly layered perennial borders in full bloom in early summer: alliums, catmint, salvia, white hydrangeas, ornamental grasses and boxwood balls along a curved lawn, a multi-stem tree and a sandstone wall, soft golden light.")
add("svc_teich_hero", R_WATER, "16:9", "A natural garden pond with crystal clear water, water lilies, rushes and marsh plants, large red sandstone boulders along the shore and a small stream with a gentle cascade, a wooden deck at the water edge, lush garden around, soft evening light.")
add("svc_belaege_hero", R_PAVE, "16:9", "A freshly finished elegant terrace and driveway of light grey large-format concrete and natural stone slabs with perfectly straight joints and a darker granite edging band, framed by clipped hedges, grasses and a sandstone wall, modern family house, bright soft afternoon light.")
add("svc_sichtschutz_hero", R_SCREEN, "16:9", "A modern privacy screen combination in a private garden: gabion walls filled with warm sandstone, vertical larch wood slat elements and a corten steel screen panel, lush planting of grasses and perennials in front, a cosy terrace with lounge furniture, soft afternoon light.")
add("svc_hang_hero", R_WALL, "16:9", "A beautifully terraced hillside garden with curved retaining walls made of large rough red Main sandstone blocks, planted terraces with lavender, grasses and perennials, broad natural stone steps connecting the levels, a modern house at the top, forested hills behind, golden-hour light.")
add("svc_treppen_hero", R_WALL, "16:9", "Wide elegant garden steps made of solid light natural stone block steps, flanked by ornamental grasses, lavender and boxwood, leading up a gentle slope to a terrace and a modern house entrance, soft late afternoon light and long shadows.")
add("hero_kontakt", R_PLANT, "16:9", "A welcoming garden entrance path of light grey stone slabs leading through lush perennial planting and past a corten steel planter to the front door of a modern family house, a sandstone wall with a discreet house number plate without numbers, warm morning light.")
print("credits before", credits(), flush=True)
for d, u in batch(J, workers=6): print(("OK  " if u else "FAIL") , os.path.basename(d), flush=True)
print("credits after", credits(), flush=True)
