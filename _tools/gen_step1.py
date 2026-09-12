import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from kie import batch, credits
G = "/Users/jannikvomhofe/Desktop/Webdesign/Galabau Geissler/_research/geissler/img/"
OUT = "/Users/jannikvomhofe/Desktop/Webdesign/Galabau Geissler/_gen/"
refs = [G+"galerie_bepflanzungen__i42bf4141ecff4e35.jpg", G+"galerie_teichanlagen_wasserelemente__ib6a700d535657f12.jpg", G+"galerie_hangsicherung_mauerbau__i355a5428db175524.jpg", G+"galerie_bepflanzungen__i6f670683356b5ac1.jpg"]
STYLE = ("The reference photos show real gardens built by a German landscaping company (Garten- und Landschaftsbau) in the Spessart / Lower Main valley region. "
         "Use them ONLY as a style and material reference - create a completely new, more beautiful, finished dream garden with the same design language and materials: "
         "rough red Main sandstone block walls and raised beds, large-format light grey concrete and natural stone paving, corten steel elements (water basin with a thin sheet waterfall, fire bowl, planters), "
         "gabion walls, lush perennial beds with ornamental grasses (Pennisetum, Miscanthus), lavender, white hydrangeas, alliums, catmint, boxwood balls, a multi-stem ornamental tree, a perfectly manicured bright green lawn. ")
PHOTO = ("Ultra photorealistic high-end cinematic photograph, shot on a full-frame cinema camera with a 24mm lens, deep depth of field, high dynamic range, natural colour grading with rich but realistic greens, "
         "warm late-afternoon golden-hour sunlight with soft long shadows. Absolutely no people, no animals, no text, no logos, no watermark, no signage.")
jobs = [
 dict(dest=OUT+"hero_A1.png", refs=refs, ar="16:9", res="2K", prompt=STYLE +
   "Composition: wide 16:9 view at a height of about 1.5 metres, camera standing on the lawn and looking along a gently curving path of large light grey stepping stones set into the lawn, leading "
   "deep into the garden towards a sunny sandstone-walled terrace with a corten steel water basin and modern lounge furniture. Perennial and grass borders frame the path on both sides. "
   "In the background a modern white family house with anthracite windows and softly forested rolling hills under a clear evening sky. Lots of depth, a clear leading line into the image, calm and inviting. " + PHOTO),
 dict(dest=OUT+"hero_A2.png", refs=refs, ar="16:9", res="2K", prompt=STYLE +
   "Composition: wide 16:9 view, camera about 1.2 metres high at the edge of a lush perennial bed with backlit ornamental grasses in the soft foreground, looking across a perfectly striped lawn "
   "towards a terraced hillside garden with curved red sandstone retaining walls, broad natural stone steps, a corten steel fire bowl on a light grey paved seating area and a slender multi-stem tree. "
   "Background: a modern house and forested Spessart hills glowing in golden-hour light. Strong depth and a natural leading line into the garden. " + PHOTO),
]
print("credits before", credits())
for d, u in batch(jobs, workers=4): print(d, u)
print("credits after", credits())
