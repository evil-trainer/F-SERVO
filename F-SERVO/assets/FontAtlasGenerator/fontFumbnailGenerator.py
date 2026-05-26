from PIL import Image
import json
import os


fontsDir = "D:\\Cloud\\Documents\\Programming\\dart\\nier_scripts_editor\\assets\\mcdFonts"

thumbnailChars = "AaBb123"

fontDirs = os.listdir(fontsDir)

for fontDir in fontDirs:
	infoJsonPath = os.path.join(fontsDir, fontDir, "_atlas.json")
	with open(infoJsonPath, "r") as infoJsonFile:
		infoJson = json.load(infoJsonFile)
	
	thumbnailSymbols = []
	for thumbChar in thumbnailChars:
		sym = list(filter(lambda x: x["char"] == thumbChar, infoJson["symbols"]))
		if len(sym) > 0:
			thumbnailSymbols.append(sym[0])
		else:
			print("No symbol for char: " + thumbChar)
	thumbnailWidth = sum([sym["width"] for sym in thumbnailSymbols])
	thumbnailHeight = max([sym["height"] for sym in thumbnailSymbols])

	srcImg = Image.open(os.path.join(fontsDir, fontDir, "_atlas.png"))
	thumbnailImage = Image.new("RGBA", (thumbnailWidth, thumbnailHeight), (0, 0, 0, 0))
	x = 0
	for sym in thumbnailSymbols:
		thumbnailImage.paste(srcImg.crop((sym["x"], sym["y"], sym["x"] + sym["width"], sym["y"] + sym["height"])), (x, 0))
		x += sym["width"]
	thumbnailImage.save(os.path.join(fontsDir, fontDir, "_thumbnail.png"))
	print(f"Saved thumbnail for {fontDir}")


