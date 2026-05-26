
import 'dart:io';
import 'dart:typed_data';

import '../../stateManagement/events/statusInfo.dart';
import '../../utils/utils.dart';
import '../utils/ByteDataWrapper.dart';

class WtaFileHeader {
  String id;
  int unknown;
  int numTex;
  int offsetTextureOffsets;
  int offsetTextureSizes;
  int offsetTextureFlags;
  int offsetTextureIdx;
  int offsetTextureInfo;
  int offsetTextureMipmaps;

  bool get isBigEndian => id == "\u0000BTW";
  int get headerSize => isBigEndian ? 0x24 : 0x20;

  WtaFileHeader.read(ByteDataWrapper bytes) :
    id = bytes.readString(4),
    unknown = bytes.readInt32(),
    numTex = bytes.readInt32(),
    offsetTextureOffsets = bytes.readUint32(),
    offsetTextureSizes = bytes.readUint32(),
    offsetTextureFlags = bytes.readUint32(),
    offsetTextureIdx = bytes.readUint32(),
    offsetTextureInfo = bytes.readUint32(),
    offsetTextureMipmaps = 0 {
      if (isBigEndian)
        offsetTextureMipmaps = bytes.readUint32();
    }

  void write(ByteDataWrapper bytes) {
    bytes.writeString(id);
    bytes.writeInt32(unknown);
    bytes.writeInt32(numTex);
    bytes.writeUint32(offsetTextureOffsets);
    bytes.writeUint32(offsetTextureSizes);
    bytes.writeUint32(offsetTextureFlags);
    bytes.writeUint32(offsetTextureIdx);
    bytes.writeUint32(offsetTextureInfo);
    if (isBigEndian)
      bytes.writeUint32(offsetTextureMipmaps);
  }
}

class WtaFileTextureInfo {
  late int format;
  late List<int> data;
  late List<int>? rawData;

  bool get isRaw => rawData != null;

  WtaFileTextureInfo(this.format, this.data) : rawData = null;
  WtaFileTextureInfo.raw(this.rawData) : format = 0, data = const [];

  WtaFileTextureInfo.read(ByteDataWrapper bytes, {int recordSize = 0x14}) {
    if (recordSize == 0x14) {
      format = bytes.readUint32();
      data = bytes.readUint32List(4);
      rawData = null;
    } else {
      rawData = bytes.readUint8List(recordSize);
      format = 0;
      data = const [];
    }
  }

  static Future<WtaFileTextureInfo> fromDds(String ddsPath) async {
    var dds = await ByteDataWrapper.fromFile(ddsPath);
    dds.position = 84;
    var dxt = dds.readString(4);
    dds.position = 112;
    var cube = dds.readUint32();
    if (!const ["DXT1", "DXT3", "DXT5"].contains(dxt))
      messageLog.add("Warning: $ddsPath uses unknown DDS format $dxt. This may not work.");
    var isCube = cube == 0xFE00;

    int format = 0;
    List<int> data = [3, isCube ? 4 : 0, 1, 0];
    switch (dxt) {
      case "DXT1":
        format = 71;
        break;
      case "DXT3":
        format = 74;
        break;
      case "DXT5":
        format = 77;
        break;
      default:
        format = 87;
        break;
    }

    return WtaFileTextureInfo(format, data);
  }

  static Future<WtaFileTextureInfo> fromGtx(String gtxPath) async {
    var gtx = await File(gtxPath).readAsBytes();
    if (gtx.length < 0x40 + 0x9C || String.fromCharCodes(gtx.take(4)) != "Gfx2")
      throw FormatException("Wii U texture replacement must be a GTX file starting with Gfx2: $gtxPath");
    var gx2 = Uint8List(0xC0);
    gx2.setRange(0, 0x9C, gtx, 0x40);
    return WtaFileTextureInfo.raw(gx2);
  }

  void write(ByteDataWrapper bytes) {
    if (rawData != null) {
      bytes.writeBytes(rawData!);
      return;
    }
    bytes.writeUint32(format);
    for (var d in data)
      bytes.writeUint32(d);
  }
}

class WtaFile {
  late WtaFileHeader header;
  late List<int> textureOffsets;
  late List<int> textureSizes;
  late List<int> textureFlags;
  List<int>? textureIdx;
  List<int>? textureMipmaps;
  late List<WtaFileTextureInfo> textureInfo;
  late Endian endian;

  bool get isBigEndian => endian == Endian.big;
  bool get isWiiU => isBigEndian;
  int get textureInfoRecordSize => isWiiU ? 0xC0 : 0x14;

  static const int albedoFlag = 0x26000020;
  static const int noAlbedoFlag = 0x22000020;

  WtaFile.read(ByteDataWrapper bytes) {
    bytes.position = 0;
    var magic = bytes.readString(4);
    if (magic == "\u0000BTW") {
      endian = Endian.big;
    } else if (magic == "WTB\u0000") {
      endian = Endian.little;
    } else {
      throw FormatException("Unsupported WTA/WTB magic: $magic");
    }
    bytes.endian = endian;
    bytes.position = 0;
    header = WtaFileHeader.read(bytes);
    bytes.position = header.offsetTextureOffsets;
    textureOffsets = bytes.readUint32List(header.numTex);
    bytes.position = header.offsetTextureSizes;
    textureSizes = bytes.readUint32List(header.numTex);
    bytes.position = header.offsetTextureFlags;
    textureFlags = bytes.readUint32List(header.numTex);
    if (header.offsetTextureIdx != 0) {
      bytes.position = header.offsetTextureIdx;
      textureIdx = bytes.readUint32List(header.numTex);
    }
    if (header.offsetTextureMipmaps != 0) {
      bytes.position = header.offsetTextureMipmaps;
      textureMipmaps = bytes.readUint32List(header.numTex);
    }
    bytes.position = header.offsetTextureInfo;
    textureInfo = List.generate(
      header.numTex,
      (i) => WtaFileTextureInfo.read(bytes, recordSize: textureInfoRecordSize)
    );
  }

  static Future<WtaFile> readFromFile(String path) async {
    var bytes = await ByteDataWrapper.fromFile(path);
    return WtaFile.read(bytes);
  }

  Future<void> writeToFile(String path) async {
    var fileSize = header.offsetTextureInfo + textureInfo.length * textureInfoRecordSize;
    var bytes = ByteDataWrapper.allocate(fileSize, endian: endian);
    header.write(bytes);

    bytes.position = header.offsetTextureOffsets;
    for (var i = 0; i < textureOffsets.length; i++)
      bytes.writeUint32(textureOffsets[i]);

    bytes.position = header.offsetTextureSizes;
    for (var i = 0; i < textureSizes.length; i++)
      bytes.writeUint32(textureSizes[i]);

    bytes.position = header.offsetTextureFlags;
    for (var i = 0; i < textureFlags.length; i++)
      bytes.writeUint32(textureFlags[i]);

    if (header.offsetTextureIdx != 0) {
      bytes.position = header.offsetTextureIdx;
      for (var i = 0; i < textureIdx!.length; i++)
        bytes.writeUint32(textureIdx![i]);
    }

    if (header.offsetTextureMipmaps != 0) {
      bytes.position = header.offsetTextureMipmaps;
      for (var i = 0; i < textureMipmaps!.length; i++)
        bytes.writeUint32(textureMipmaps![i]);
    }

    bytes.position = header.offsetTextureInfo;
    for (var i = 0; i < textureInfo.length; i++)
      textureInfo[i].write(bytes);

    await bytes.save(path);
  }

  void updateHeader() {
    header.numTex = textureOffsets.length;
    header.offsetTextureOffsets = header.headerSize;
    header.offsetTextureSizes = alignTo(header.offsetTextureOffsets + textureOffsets.length * 4, 32);
    header.offsetTextureFlags = alignTo(header.offsetTextureSizes + textureSizes.length * 4, 32);
    header.offsetTextureIdx = textureIdx != null ? alignTo(header.offsetTextureFlags + textureFlags.length * 4, 32) : 0;
    final afterIdx = textureIdx != null ? alignTo(header.offsetTextureIdx + textureIdx!.length * 4, 32) : alignTo(header.offsetTextureFlags + textureFlags.length * 4, 32);
    if (isWiiU) {
      textureMipmaps ??= List.filled(textureOffsets.length, 0);
      header.offsetTextureMipmaps = alignTo(afterIdx, 32);
      header.offsetTextureInfo = alignTo(header.offsetTextureMipmaps + textureMipmaps!.length * 4, 32);
    } else {
      header.offsetTextureMipmaps = 0;
      header.offsetTextureInfo = afterIdx;
    }
  }
}
