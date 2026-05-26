from __future__ import annotations
from dataclasses import dataclass
from math import ceil
from PIL import Image, ImageDraw, ImageFilter
from PIL.ImageFont import FreeTypeFont
from fontTools.ttLib import TTFont

from cliOptions import FontOptions, ImgOperationFromFont, ImgOperationFromTexture, CliOptions


def fallbackInvalidFontChars(options: CliOptions):
	for fontId, font in options.fonts.items():
		fontCmap = TTFont(font.fontPath).getBestCmap()
		supportedChars = set(fontCmap.keys())
		for i in range(len(options.operations)):
			op = options.operations[i]
			if not isinstance(op, ImgOperationFromFont):
				continue
			if op.fallback is None:
				continue
			if op.charFontId != fontId:
				continue
			if len(op.drawChar) != 1:
				raise Exception(f"char {op.id} must be a single char")
			if ord(op.drawChar) not in supportedChars:
				options.operations[i] = op.fallback
	for i in range(len(options.operations)):
		op = options.operations[i]
		if not isinstance(op, ImgOperationFromFont):
			continue
		if op.fallback is None:
			continue
		if op.charFontId in options.fonts:
			continue
		options.operations[i] = op.fallback

def adjustFonts(options: CliOptions):
	# for each font:
	# 1. find largest bbox height extents
	# 2. optionally adjust yOffset and scale
	#   2.1. if max height is > fontHeight, scale font to fit
	#   2.2. if top most edge is != 0, adjust yOffset
	# 3. save bottom baseline

	font: FontOptions
	for fontId, font in options.fonts.items():
		# 1.
		testChars = {
			c for c in
			"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789ÄÖÜßÈÉÊËÀÂÄÇÌÍÎÏÒÓÔÖÙÚÛÜÑŸÆŒÆŒ[]"
		}
		testChars = {
			op.drawChar
			for op in options.operations
			if isinstance(op, ImgOperationFromFont) and op.charFontId == fontId
		}.union(testChars)
		minTop = 999999
		maxBottom = 0
		for c in testChars:
			bbox = font.font.getbbox(c)
			minTop = min(minTop, bbox[1])
			maxBottom = max(maxBottom, bbox[3])
		
		# 2.1.
		maxHeight = maxBottom - minTop + font.letYPadding*2
		if maxHeight > font.fontHeight:
			tooBigByFactor = maxHeight / font.fontHeight
			font.font = FreeTypeFont(font.fontPath, int(font.fontHeight / tooBigByFactor))
		# 2.2.
		if minTop != 0:
			font.letYOffset -= minTop
	
		# 3.
		fontMetrics = font.font.getmetrics()
		additionalYOffset = 0
		height = fontMetrics[0] + fontMetrics[1]
		if height < font.fontHeight:
			additionalYOffset = fontMetrics[1] // 2
		font.letYOffset += additionalYOffset

@dataclass
class FontCharSize:
	char: str
	width: int
	height: int
	xOff: int
	yOff: int

def getCustomFontCharSizes(options: CliOptions) -> dict[str, FontCharSize]:
	charSizes: dict[str, FontCharSize] = {}
	for op in options.operations:
		if not isinstance(op, ImgOperationFromFont):
			continue
		fontOpt = options.fonts[op.charFontId]
		charBBox = fontOpt.font.getbbox(op.drawChar)
		charWidth = charBBox[2] - charBBox[0] + fontOpt.letXPadding*2
		charHeight = charBBox[3] - charBBox[1]
		charHeight = max(charHeight, fontOpt.fontHeight)
		xOff = fontOpt.letXOffset
		yOff = fontOpt.letYOffset
		charSizes[op.id] = FontCharSize(op.drawChar, charWidth, charHeight, xOff, yOff)
	return charSizes

def estimateAtlasSize(options: CliOptions, charSizes: dict[str, FontCharSize]) -> int:
	allCharsWidth = 0
	allCharsHeight = 0
	allCharsCount = 0
	if charSizes:
		allCharsWidth = sum(s.width for s in charSizes.values())
		allCharsHeight = max(s.height for s in charSizes.values())
		allCharsCount = len(charSizes)
	texOps = [op for op in options.operations if isinstance(op, ImgOperationFromTexture)]
	if texOps:
		allCharsWidth += sum(op.pasteWidth for op in texOps)
		allCharsHeight += sum(op.pasteHeight for op in texOps)
		allCharsCount += len(texOps)

	avrCharWidth = allCharsWidth / allCharsCount + options.letterSpacing
	avrCharHeight = allCharsHeight / allCharsCount + options.letterSpacing

	estimatedAtlasArea = avrCharWidth * avrCharHeight * allCharsCount

	def safetyFactor(texSize):
		if texSize >= 2048:
			return 1.05
		if texSize >= 1024:
			return 1.1
		return 1.2
	size = options.minTexSize
	while size**2 < estimatedAtlasArea * safetyFactor(size):
		size *= 2
	
	return size

def resize(img: Image.Image, size: tuple[int, int]) -> Image.Image:
	channels = [
		channel.resize(size, Image.Resampling.BOX)
		for channel in img.split()
	]
	return Image.merge(img.mode, channels)
	

def blurRegionRGB(img: Image.Image, region: tuple[int, int, int, int], blurSize: float) -> Image.Image:
	channels = img.split()
	rgb = Image.merge("RGB", channels[:3])
	alpha = channels[3]
	crop = rgb.crop(region)
	blur = crop.filter(ImageFilter.GaussianBlur(blurSize))
	rgb.paste(blur, region)
	return Image.merge("RGBA", [*rgb.split(), alpha])
	

def generateAtlas(options: CliOptions, charSizes: dict[str, FontCharSize], atlasSize: int) -> tuple[Image.Image, dict]:
	atlasMap = {
		"size": atlasSize,
		"fontParams": {
			fontId: {
				"scale": font.font.size / font.fontHeight,
			}
			for fontId, font in options.fonts.items()
		},
		"symbols": {},
	}
	atlas = Image.new("RGBA", (atlasSize, atlasSize), color=(0, 0, 0, 0))
	draw = ImageDraw.Draw(atlas)

	curX = 0
	curY = 0
	curRowHeight = 0
	for op in options.operations:
		if isinstance(op, ImgOperationFromFont):
			charWidth = charSizes[op.id].width
			charHeight = charSizes[op.id].height
		elif isinstance(op, ImgOperationFromTexture):
			charWidth = op.pasteWidth
			charHeight = op.pasteHeight
		else:
			raise Exception("Unknown operation type")
		curRowHeight = max(curRowHeight, charHeight)
		if curX + charWidth + options.letterSpacing > atlasSize:
			curX = options.letterSpacing
			curY += curRowHeight + options.letterSpacing
			curRowHeight = 0
			if curY + charHeight > atlasSize:
				# big oof
				return generateAtlas(options, charSizes, atlasSize * 2)

		if isinstance(op, ImgOperationFromFont):
			font = options.fonts[op.charFontId]
			xOff = charSizes[op.id].xOff
			yOff = charSizes[op.id].yOff
			draw.text((curX + xOff, curY + yOff), op.drawChar, font=font.font, stroke_width=font.strokeWidth)
			if font.rgbBlurSize > 0:
				pad = ceil(options.letterSpacing / 2)
				atlas = blurRegionRGB(atlas, (curX - pad, curY - pad, curX + pad + charWidth, curY + pad + charHeight), font.rgbBlurSize)
				draw = ImageDraw.Draw(atlas)
		elif isinstance(op, ImgOperationFromTexture):
			srcTex = options.srcTextures[op.srcTexId]
			crop = srcTex.crop((op.srcX, op.srcY, op.srcX + op.width, op.srcY + op.height))
			if op.width != charWidth or op.height != charHeight:
				crop = resize(crop, (charWidth, charHeight))
			atlas.paste(crop, (curX, curY))
		
		atlasMap["symbols"][op.id] = {
			"x": curX,
			"y": curY,
			"width": charWidth,
			"height": charHeight,
		}
		curX += charWidth + options.letterSpacing
	
	return atlas, atlasMap

def generateFontAtlas(options: CliOptions) -> dict:
	options.operations.sort(key=lambda op: options.fonts[op.charFontId].fontHeight if isinstance(op, ImgOperationFromFont) else op.height)
	fallbackInvalidFontChars(options)
	adjustFonts(options)
	charSizes = getCustomFontCharSizes(options)
	atlasSize = estimateAtlasSize(options, charSizes)
	atlas, atlasMap = generateAtlas(options, charSizes, atlasSize)
	atlas.save(options.dstTexPath)
	return atlasMap
