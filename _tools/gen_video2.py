import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from kie import upload, run, credits
OUT = "/Users/jannikvomhofe/Desktop/Webdesign/Galabau Geissler/_gen/"
print("credits before", credits(), flush=True)
first = upload(OUT + "svc_licht_hero.png", max_side=2048)
prompt = ("Slow, smooth cinematic dolly-in at blue hour through the illuminated garden: warm garden spotlights gently glow on the multi-stem tree and the ornamental grasses, "
          "the grasses sway softly in a light evening breeze, water pours calmly from the corten steel sheet waterfall into the basin with gentle ripples and reflections, "
          "the fire bowl flickers softly, the deep blue sky darkens very slowly. Photorealistic, calm, luxurious, perfectly stable camera, one continuous shot, no cuts, no people, no text.")
run("kling-3.0/video", {"prompt": prompt, "image_urls": [first], "sound": False, "duration": "6", "aspect_ratio": "16:9", "mode": "pro", "multi_shots": False}, OUT + "smart_video_v1.mp4")
print("credits after", credits(), flush=True)
