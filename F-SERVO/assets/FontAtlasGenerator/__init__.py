import base64
import json

from cliOptions import CliOptions
from fontAtlasGenerator import generateFontAtlas

# debugArgs = {
# 	"dstTexPath": "atlasTest.png",
# 	"fonts": {
# 		"0": {
# 			"path": "C:\\Windows\\Fonts\\comic.ttf",
# 			"height": 76,
# 			"scale": 1,
# 			"letXPadding": 10,
# 		},
# 		"1": {
# 			"path": "C:\\Windows\\Fonts\\comic.ttf",
# 			"height": 12,
# 			"scale": 1.5
# 		},
# 		"2": {
# 			"path": "C:\\Windows\\Fonts\\comic.ttf",
# 			"height": 26,
# 			"scale": 1
# 		}
# 	},
# 	"srcTexPaths": [
# 	],
# 	"operations": [
# 		{
# 			"type": 1,
# 			"id": 0,
# 			"drawChar": "e",
# 			"charFontId": "0"
# 		},
# 		# {
# 		# 	"type": 1,
# 		# 	"id": 1,
# 		# 	"drawChar": "S",
# 		# 	"charFontId": "0"
# 		# },
# 		# {
# 		# 	"type": 1,
# 		# 	"id": 2,
# 		# 	"drawChar": "e",
# 		# 	"charFontId": "0"
# 		# },
# 		# {
# 		# 	"type": 1,
# 		# 	"id": 3,
# 		# 	"drawChar": "c",
# 		# 	"charFontId": "0"
# 		# },
# 		# {
# 		# 	"type": 1,
# 		# 	"id": 4,
# 		# 	"drawChar": "t",
# 		# 	"charFontId": "0"
# 		# },
# 		# {
# 		# 	"type": 1,
# 		# 	"id": 5,
# 		# 	"drawChar": "A",
# 		# 	"charFontId": "0"
# 		# },
# 		# {
# 		# 	"type": 1,
# 		# 	"id": 6,
# 		# 	"drawChar": "C",
# 		# 	"charFontId": "0"
# 		# },
# 		# {
# 		# 	"type": 1,
# 		# 	"id": 7,
# 		# 	"drawChar": "B",
# 		# 	"charFontId": "1"
# 		# },
# 		# {
# 		# 	"type": 1,
# 		# 	"id": 8,
# 		# 	"drawChar": "B",
# 		# 	"charFontId": "1"
# 		# },
# 		# {
# 		# 	"type": 1,
# 		# 	"id": 9,
# 		# 	"drawChar": "C",
# 		# 	"charFontId": "2"
# 		# },
# 		# {
# 		# 	"type": 1,
# 		# 	"id": 10,
# 		# 	"drawChar": "B",
# 		# 	"charFontId": "2"
# 		# },
# 		# {
# 		# 	"type": 1,
# 		# 	"id": 11,
# 		# 	"drawChar": "B",
# 		# 	"charFontId": "2"
# 		# },
# 	]
# }

if __name__ == "__main__":
	b64Json = input() # read json in base64 format
	jsonIn = base64.b64decode(b64Json).decode("utf-8")
	options = json.loads(jsonIn)
	# options = debugArgs
	atlasMap = generateFontAtlas(CliOptions(options))
	print(json.dumps(atlasMap))
