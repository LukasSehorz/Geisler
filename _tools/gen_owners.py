import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from kie import batch, credits
G = "/Users/jannikvomhofe/Desktop/Webdesign/Galabau Geissler/_research/geissler/img/"
OUT = "/Users/jannikvomhofe/Desktop/Webdesign/Galabau Geissler/_gen/"
P = ("Edit this photograph. The two men must remain EXACTLY identical: same faces, same facial features, same expressions, same hair and beard, same grey knitted fleece jackets with the green logo embroidery, "
     "same pose, same arm position, same lighting on their faces - do not beautify, do not change identity. Only change the background and the framing: "
     "remove the orange wooden fence completely and place the two men in front of a beautiful, softly out-of-focus finished private garden at golden hour "
     "(lush green perennial beds, ornamental grasses, a red sandstone wall, warm evening light, pleasant creamy bokeh). "
     "Extend the scene into a wide horizontal format. Photorealistic, natural colour grading, professional corporate portrait photography, no text, no watermark.")
jobs = [
 dict(dest=OUT+"owners_wide_1.png", refs=[G+"home__i6103d52cd6d40911.jpg"], ar="16:9", res="2K", prompt=P + " Position the two men in the right half of the frame, leaving calm garden background space on the left."),
 dict(dest=OUT+"owners_wide_2.png", refs=[G+"home__i6103d52cd6d40911.jpg"], ar="16:9", res="2K", prompt=P + " Keep the two men centred in the frame, visible from the waist up."),
]
for d, u in batch(jobs, workers=2): print(d, u)
print("credits after", credits())
