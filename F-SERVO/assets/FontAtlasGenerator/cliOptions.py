from __future__ import annotations
from PIL import Image, ImageFont
from PIL.ImageFont import FreeTypeFont

class OperationType:
	FROM_TEXTURE = 0
	FROM_FONT = 1

class ImgOperation:
	type: int
	id: str

	def __init__(self, d: dict):
		self.type = d["type"]
		self.id = d["id"]
	
	@staticmethod
	def fromDict(d: dict):
		if d["type"] == OperationType.FROM_FONT:
			return ImgOperationFromFont(d)
		elif d["type"] == OperationType.FROM_TEXTURE:
			return ImgOperationFromTexture(d)
		else:
			raise Exception(f"Unknown operation type {d['type']}")

class ImgOperationFromFont(ImgOperation):
	drawChar: str
	charFontId: str
	fallback: ImgOperation|None

	def __init__(self, d: dict):
		super().__init__(d)
		self.drawChar = d["drawChar"]
		self.charFontId = d["charFontId"]

		fallback = d.get("fallback", None)
		if fallback is not None:
			self.fallback = ImgOperation.fromDict(fallback)
		else:
			self.fallback = None

class ImgOperationFromTexture(ImgOperation):
	srcTexId: int
	srcX: int
	srcY: int
	width: int
	height: int
	resolutionScale: float
	pasteWidth: int
	pasteHeight: int

	def __init__(self, d: dict):
		super().__init__(d)
		self.srcTexId = d["srcTexId"]
		self.srcX = d["srcX"]
		self.srcY = d["srcY"]
		self.width = d["width"]
		self.height = d["height"]
		self.resolutionScale = d.get("resolutionScale", 1.0)
		self.pasteWidth = int(self.width * self.resolutionScale)
		self.pasteHeight = int(self.height * self.resolutionScale)

class FontOptions:
	fontPath: str
	font: FreeTypeFont
	fontHeight: int
	letXPadding: int
	letYPadding: int
	letXOffset: int
	letYOffset: int
	resolutionScale: float
	strokeWidth: int
	rgbBlurSize: float

	def __init__(self, d: dict):
		self.fontPath = d["path"]
		self.fontHeight = d["height"]
		self.letXPadding = d.get("letXPadding", 0)
		self.letYPadding = d.get("letYPadding", 0)
		self.letXOffset = d.get("letXOffset", 0) + self.letXPadding
		self.letYOffset = d.get("letYOffset", 0) + self.letYPadding
		self.resolutionScale = d.get("resolutionScale", 1.0)
		self.strokeWidth = d.get("strokeWidth", 0)
		self.rgbBlurSize = d.get("rgbBlurSize", 0.0)
		self.fontHeight = int(self.fontHeight * self.resolutionScale)
		self.font = ImageFont.truetype(self.fontPath, size=self.fontHeight)

class CliOptions:
	srcTexPaths: list[str]
	srcTextures: dict[int, Image.Image]
	fonts: dict[str, FontOptions]
	dstTexPath: str
	letterSpacing: int
	minTexSize: int
	operations: list[ImgOperation]

	def __init__(self, argsJson: dict):
		self.srcTexPaths = argsJson.get("srcTexPaths", [])
		self.dstTexPath = argsJson.get("dstTexPath", None)
		self.letterSpacing = argsJson.get("letterSpacing", 0)
		self.minTexSize = argsJson.get("minTexSize", 256)
		self.operations = [ImgOperation.fromDict(d) for d in argsJson.get("operations", [])]

		self.srcTextures = {}
		for srcTexId, srcTexPath in enumerate(self.srcTexPaths):
			self.srcTextures[srcTexId] = Image.open(srcTexPath)

		self.fonts = {}
		for fontId, fontOptions in argsJson.get("fonts", {}).items():
			self.fonts[fontId] = FontOptions(fontOptions)
