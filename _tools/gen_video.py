import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from kie import upload, run, credits
OUT = "/Users/jannikvomhofe/Desktop/Webdesign/Galabau Geissler/_gen/"
c0 = credits(); print("credits before", c0, flush=True)
first = upload(OUT + "hero_A1.png", max_side=2048)
print("first frame", first, flush=True)
prompt = ("Smooth cinematic gimbal shot slowly gliding forward along the curved light grey stepping-stone path across the lush lawn, deeper into the garden towards the sunny terrace "
          "with the corten steel water basin and the sandstone wall. The camera moves steadily forward and rises very gently while drifting slightly to the right, revealing the flowing sheet waterfall, "
          "the lounge furniture and the forested rolling hills behind. Ornamental grasses, lavender and hydrangeas sway softly in a light evening breeze, leaves of the multi-stem tree flutter gently, "
          "the fire bowl flickers. Warm golden-hour sunlight with long soft shadows. Photorealistic, natural and calm motion, perfectly stable, one continuous shot, no cuts, no people, no text.")
run("kling-3.0/video", {"prompt": prompt, "image_urls": [first], "sound": False, "duration": "8", "aspect_ratio": "16:9", "mode": "pro", "multi_shots": False}, OUT + "hero_video_v1.mp4")
print("credits after", credits(), flush=True)
