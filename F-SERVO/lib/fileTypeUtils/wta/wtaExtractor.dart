
import 'dart:io';
import 'dart:typed_data';

import 'package:path/path.dart';

import 'wtaReader.dart';

final _gtxHeader1 = _hexToBytes("4766783200000020000000070000000100000002000000000000000000000000");
final _gtxHeader2 = _hexToBytes("424c4b7b0000002000000001000000000000000b0000009c0000000000000000");
final _gtxDataPrefix = _hexToBytes("424c4b7b0000002000000001000000000000000c");
final _gtxMipPrefix = _hexToBytes("424c4b7b0000002000000001000000000000000d");
final _gtxEnd = _hexToBytes("424c4b7b00000020000000010000000000000001000000000000000000000000");

Uint8List _hexToBytes(String hex) {
  final out = Uint8List(hex.length ~/ 2);
  for (var i = 0; i < out.length; i++)
    out[i] = int.parse(hex.substring(i * 2, i * 2 + 2), radix: 16);
  return out;
}

int _u32be(List<int> data, int off) {
  return (data[off] << 24) | (data[off + 1] << 16) | (data[off + 2] << 8) | data[off + 3];
}

class WiiUGtxPayload {
  final List<int> gx2;
  final List<int> image;
  final List<int> mipmaps;
  final int dataLength;
  final int mipmapLength;

  const WiiUGtxPayload(this.gx2, this.image, this.mipmaps, this.dataLength, this.mipmapLength);
}

WiiUGtxPayload parseWiiUGtx(List<int> gtx) {
  if (gtx.length < 0x40 + 0x9C || String.fromCharCodes(gtx.take(4)) != "Gfx2")
    throw FormatException("Wii U texture replacement must be a GTX file starting with Gfx2");
  final gx2 = gtx.sublist(0x40, 0x40 + 0x9C);
  final dataLength = _u32be(gx2, 0x20);
  final mipmapLength = _u32be(gx2, 0x28);
  final numMipmaps = _u32be(gx2, 0x10);
  final dataStart = 0x20 * 3 + 0x9C;
  final image = gtx.sublist(dataStart, dataStart + dataLength);
  List<int> mipmaps = const [];
  if (numMipmaps > 1 && mipmapLength > 0) {
    final mipStart = 0x20 * 4 + 0x9C + dataLength;
    mipmaps = gtx.sublist(mipStart, mipStart + mipmapLength);
  }
  return WiiUGtxPayload(gx2, image, mipmaps, dataLength, mipmaps.length);
}

Uint8List makeWiiUGtx(WtaFile wta, int i, List<int> wtpData) {
  final gx2 = wta.textureInfo[i].rawData;
  if (gx2 == null)
    throw StateError("Wii U WTA texture info is missing raw GX2 metadata");
  final numMipmaps = _u32be(gx2, 0x10);
  final dataLength = _u32be(gx2, 0x20);
  final mipmapLength = _u32be(gx2, 0x28);
  final dataOffset = wta.textureOffsets[i];
  final mipmapOffset = wta.textureMipmaps?[i] ?? 0;

  final out = BytesBuilder(copy: false);
  out.add(_gtxHeader1);
  out.add(_gtxHeader2);
  out.add(gx2.take(0x9C).toList());
  out.add(_gtxDataPrefix);
  out.add(gx2.sublist(0x20, 0x24));
  out.add(Uint8List(8));
  out.add(wtpData.sublist(dataOffset, dataOffset + dataLength));
  if (numMipmaps > 1 && mipmapLength > 0 && mipmapOffset != 0) {
    out.add(_gtxMipPrefix);
    out.add(gx2.sublist(0x28, 0x2C));
    out.add(Uint8List(8));
    out.add(wtpData.sublist(mipmapOffset, mipmapOffset + mipmapLength));
  }
  out.add(_gtxEnd);
  return out.toBytes();
}

Future<List<String>> extractWta(String wtaPath, String? wtpPath, bool isWtb) async {
  List<String> texturePaths = [];
  var extractDir = join(dirname(wtaPath), "nier2blender_extracted", basename(wtaPath));
  await Directory(extractDir).create(recursive: true);
  var wta = await WtaFile.readFromFile(wtaPath);
  var textureDataPath = isWtb ? wtaPath : wtpPath!;
  var textureDataBytes = await File(textureDataPath).readAsBytes();
  for (int i = 0; i < wta.textureOffsets.length; i++) {
    final ext = wta.isWiiU && !isWtb ? "gtx" : "dds";
    var texturePath = join(extractDir, makeTextureFileName(i, wta.textureIdx?[i], ext: ext));
    texturePaths.add(texturePath);
    final textureBytes = wta.isWiiU && !isWtb
      ? makeWiiUGtx(wta, i, textureDataBytes)
      : textureDataBytes.sublist(wta.textureOffsets[i], wta.textureOffsets[i] + wta.textureSizes[i]);
    await File(texturePath).writeAsBytes(textureBytes);
  }
  return texturePaths;
}

String makeTextureFileName(int i, int? id, {String ext = "dds"}) {
  if (id == null)
    return "$i.$ext";
  return "${i}_${id.toRadixString(16).padLeft(8, "0")}.$ext";
}
