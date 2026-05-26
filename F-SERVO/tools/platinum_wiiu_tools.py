#!/usr/bin/env python3
"""
Platinum Wii U tools for F-SERVO.

This script is a Windows-friendly Python port/adaptation of the Bayonetta DAT/WTA/WTP/MCD
workflows needed for Wii U Platinum Games assets. It intentionally has no third-party
runtime dependencies.

Supported workflows:
  dat-extract   Extract DAT/EVN/EFF/DTT with endian autodetection and JSON metadata.
  dat-repack    Rebuild extracted DAT folders losslessly using metadata.
  wtx-extract   Extract WTA/WTP or WTB textures, including Wii U GTX wrapping.
  wtx-repack    Rebuild WTA/WTP or WTB texture containers from extracted payloads.
  mcd-export    Export Bayonetta 2/Wii U MCD strings to UTF-8 JSON/TXT for localization.
  mcd-import    Import edited JSON text into an MCD by rebuilding string data in-place.

The Wii U WTA/WTP GTX logic follows Kerilk/bayonetta_tools' WTBFile implementation:
GTX files are wrapped as Gfx2 + BLK{ chunks and raw image/mipmap payloads are stored
in the paired WTP. The WTA side stores GX2 surface metadata in 0xC0-byte slots.
"""
from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import math
import os
import shutil
import struct
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import BinaryIO, Iterable, Optional


def align(value: int, boundary: int) -> int:
    if boundary <= 0:
        return value
    return (value + boundary - 1) & ~(boundary - 1)


def read_cstr(raw: bytes) -> str:
    return raw.split(b"\0", 1)[0].decode("utf-8", "replace")


def u16(data: bytes, off: int, endian: str) -> int:
    return struct.unpack_from((">" if endian == "big" else "<") + "H", data, off)[0]


def i16(data: bytes, off: int, endian: str) -> int:
    return struct.unpack_from((">" if endian == "big" else "<") + "h", data, off)[0]


def u32(data: bytes, off: int, endian: str) -> int:
    return struct.unpack_from((">" if endian == "big" else "<") + "I", data, off)[0]


def pack_u16(value: int, endian: str) -> bytes:
    return struct.pack((">" if endian == "big" else "<") + "H", value & 0xFFFF)


def pack_i16(value: int, endian: str) -> bytes:
    return struct.pack((">" if endian == "big" else "<") + "h", value)


def pack_u32(value: int, endian: str) -> bytes:
    return struct.pack((">" if endian == "big" else "<") + "I", value & 0xFFFFFFFF)


def pack_f32(value: float, endian: str) -> bytes:
    return struct.pack((">" if endian == "big" else "<") + "f", value)


def detect_dat_endian(data: bytes) -> str:
    if data[:4] != b"DAT\0":
        raise ValueError("Not a DAT archive: missing DAT\\0 magic")
    best: Optional[str] = None
    for endian in ("little", "big"):
        count = u32(data, 4, endian)
        offs = [u32(data, 8 + i * 4, endian) for i in range(5)]
        plausible = 0 < count < 100000 and all(0 <= x < len(data) for x in offs)
        plausible = plausible and offs[0] >= 0x20 and len(set(offs[:4])) >= 4
        if plausible:
            if best is None or endian == "big":
                best = endian
    if best is None:
        raise ValueError("Could not determine DAT endianess from header/table offsets")
    return best


@dataclass
class DatEntry:
    index: int
    name: str
    extension: str
    offset: int
    size: int
    sha256: str = ""
    first16: str = ""


@dataclass
class DatMetadata:
    format: str
    source: str
    endian: str
    count: int
    name_length: int
    header: dict
    entries: list[DatEntry]

    def to_json(self) -> dict:
        d = asdict(self)
        d["entries"] = [asdict(e) for e in self.entries]
        return d


def dat_read(path: Path) -> tuple[DatMetadata, bytes]:
    data = path.read_bytes()
    endian = detect_dat_endian(data)
    count = u32(data, 4, endian)
    off_offsets = u32(data, 8, endian)
    off_ext = u32(data, 12, endian)
    off_names = u32(data, 16, endian)
    off_sizes = u32(data, 20, endian)
    off_hash = u32(data, 24, endian)
    name_length = u32(data, off_names, endian)
    entries: list[DatEntry] = []
    for i in range(count):
        off = u32(data, off_offsets + i * 4, endian)
        size = u32(data, off_sizes + i * 4, endian)
        ext = read_cstr(data[off_ext + i * 4: off_ext + i * 4 + 4])
        name = read_cstr(data[off_names + 4 + i * name_length: off_names + 4 + (i + 1) * name_length])
        payload = data[off: off + size]
        entries.append(DatEntry(i, name, ext, off, size, hashlib.sha256(payload).hexdigest(), payload[:16].hex(" ")))
    meta = DatMetadata(
        format="platinum-dat",
        source=str(path),
        endian=endian,
        count=count,
        name_length=name_length,
        header={
            "file_offsets_offset": off_offsets,
            "file_extensions_offset": off_ext,
            "file_names_offset": off_names,
            "file_sizes_offset": off_sizes,
            "hash_map_offset": off_hash,
        },
        entries=entries,
    )
    return meta, data


def dat_extract(dat_path: Path, out_dir: Path) -> None:
    meta, data = dat_read(dat_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    for e in meta.entries:
        out_file = out_dir / e.name
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_bytes(data[e.offset:e.offset + e.size])
    (out_dir / "dat_info_wiiu.json").write_text(json.dumps(meta.to_json(), indent=2), encoding="utf-8")
    (out_dir / "dat_info.json").write_text(json.dumps({
        "version": 4,
        "platform": "wiiu" if meta.endian == "big" else "pc",
        "endian": meta.endian,
        "files": [e.name for e in meta.entries],
        "original_order": [e.name for e in meta.entries],
        "basename": dat_path.stem,
        "ext": dat_path.suffix.lstrip("."),
        "name_length": meta.name_length,
    }, indent=2), encoding="utf-8")
    lines = [f"DAT endian={meta.endian} count={meta.count} name_length={meta.name_length}"]
    h = meta.header
    lines.append("tables: " + ", ".join(f"{k}=0x{v:X}" for k, v in h.items()))
    lines.append("")
    for e in meta.entries:
        lines.append(f"{e.index:03d} {e.name:<28} ext={e.extension:<4} off=0x{e.offset:08X} size=0x{e.size:08X} first16={e.first16}")
    (out_dir / "dat_listing.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Extracted {meta.count} files from {dat_path} to {out_dir} ({meta.endian}-endian)")


def dat_repack(extracted_dir: Path, output_path: Path) -> None:
    info_path = extracted_dir / "dat_info.json"
    if not info_path.exists():
        info_path = extracted_dir / "dat_info_wiiu.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    if "entries" in info:
        names = [e["name"] for e in info["entries"]]
        endian = info.get("endian", "little")
        name_length = int(info.get("name_length") or max(len(n) + 1 for n in names))
    else:
        names = list(info.get("original_order") or info["files"])
        endian = info.get("endian", "little")
        name_length = int(info.get("name_length") or max(len(n) + 1 for n in names))
    files = [extracted_dir / n for n in names]
    missing = [str(p) for p in files if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing extracted files: " + ", ".join(missing[:10]))
    sizes = [p.stat().st_size for p in files]
    count = len(files)
    file_offsets_offset = 0x20
    file_extensions_offset = file_offsets_offset + 4 * count
    file_ext_bytes = b"".join((p.suffix.lstrip(".")[:3].encode("ascii", "replace").ljust(3, b"\0") + b"\0") for p in files)
    file_names_offset = file_extensions_offset + len(file_ext_bytes)
    file_sizes_offset = align(file_names_offset + 4 + count * name_length, 4)
    hash_map_offset = file_sizes_offset + 4 * count
    # For lossless compatibility with F-SERVO and Bayonetta tools, this Python repacker writes
    # an empty hash-map header equivalent size only when no original map is being preserved.
    # The game/tooling tested here relies on linear tables, not hash lookup.
    hash_blob = pack_u32(0, endian) * 4
    current = hash_map_offset + len(hash_blob)
    file_offsets = []
    for sz in sizes:
        current = align(current, 0x20)
        file_offsets.append(current)
        current += sz
    total_size = align(current, 0x10)
    out = bytearray(total_size)
    out[0:4] = b"DAT\0"
    pos = 4
    for v in [count, file_offsets_offset, file_extensions_offset, file_names_offset, file_sizes_offset, hash_map_offset]:
        out[pos:pos + 4] = pack_u32(v, endian); pos += 4
    out[file_offsets_offset:file_offsets_offset + 4 * count] = b"".join(pack_u32(v, endian) for v in file_offsets)
    out[file_extensions_offset:file_extensions_offset + len(file_ext_bytes)] = file_ext_bytes
    out[file_names_offset:file_names_offset + 4] = pack_u32(name_length, endian)
    pos = file_names_offset + 4
    for n in names:
        b = n.encode("utf-8")[:name_length - 1]
        out[pos:pos + name_length] = b + b"\0" * (name_length - len(b))
        pos += name_length
    out[file_sizes_offset:file_sizes_offset + 4 * count] = b"".join(pack_u32(v, endian) for v in sizes)
    out[hash_map_offset:hash_map_offset + len(hash_blob)] = hash_blob
    for p, off, sz in zip(files, file_offsets, sizes):
        out[off:off + sz] = p.read_bytes()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(out)
    print(f"Repacked {count} files into {output_path} ({endian}-endian)")


GTX_HEADER_1 = bytes.fromhex("4766783200000020000000070000000100000002000000000000000000000000")
GTX_HEADER_2 = bytes.fromhex("424c4b7b0000002000000001000000000000000b0000009c0000000000000000")
GTX_DATA_PREFIX = bytes.fromhex("424c4b7b0000002000000001000000000000000c")
GTX_MIP_PREFIX = bytes.fromhex("424c4b7b0000002000000001000000000000000d")
GTX_END = bytes.fromhex("424c4b7b00000020000000010000000000000001000000000000000000000000")


@dataclass
class WtxTexture:
    index: int
    extension: str
    offset: int
    size: int
    flag: int
    idx: Optional[int]
    info_offset: int = 0
    data_length: Optional[int] = None
    mipmap_length: Optional[int] = None
    mipmap_offset: Optional[int] = None
    sha256: str = ""


@dataclass
class WtxMetadata:
    format: str
    source: str
    paired_wtp: Optional[str]
    endian: str
    is_wta: bool
    magic: str
    unknown: int
    count: int
    offsets: dict
    textures: list[WtxTexture]

    def to_json(self) -> dict:
        d = asdict(self)
        d["textures"] = [asdict(t) for t in self.textures]
        return d


def wtx_read_header(wta_path: Path) -> tuple[bytes, str, str, bool, dict, bytes]:
    data = wta_path.read_bytes()
    magic = data[:4]
    if magic == b"\0BTW":
        endian = "big"
    elif magic == b"WTB\0":
        endian = "little"
    else:
        raise ValueError(f"Unsupported WTA/WTB magic {magic!r}")
    unknown = u32(data, 4, endian)
    count = u32(data, 8, endian)
    offs = {
        "texture_offsets": u32(data, 12, endian),
        "texture_sizes": u32(data, 16, endian),
        "texture_flags": u32(data, 20, endian),
        "texture_idx": u32(data, 24, endian),
        "texture_info": u32(data, 28, endian),
        "mipmap_offsets": u32(data, 32, endian) if endian == "big" and len(data) >= 36 else 0,
    }
    return magic, endian, "gtx" if endian == "big" else "dds", True, {"unknown": unknown, "count": count, **offs}, data


def make_gtx(gx2: bytes, wtp: bytes, data_off: int, mip_off: int, endian: str) -> tuple[bytes, int, int, int]:
    num_mipmap = u32(gx2, 0x10, endian)
    data_length = u32(gx2, 0x20, endian)
    mipmap_length = u32(gx2, 0x28, endian)
    out = bytearray()
    out += GTX_HEADER_1
    out += GTX_HEADER_2
    out += gx2
    out += GTX_DATA_PREFIX
    out += gx2[0x20:0x24]
    out += b"\0" * 8
    out += wtp[data_off:data_off + data_length]
    if num_mipmap > 1 and mipmap_length > 0 and mip_off:
        out += GTX_MIP_PREFIX
        out += gx2[0x28:0x2C]
        out += b"\0" * 8
        out += wtp[mip_off:mip_off + mipmap_length]
    else:
        mipmap_length = 0
    out += GTX_END
    return bytes(out), data_length, mipmap_length, num_mipmap


def wtx_extract(wta_path: Path, wtp_path: Optional[Path], out_dir: Path) -> None:
    # If the user passed a .wtp as the first argument, try to find the .wta
    if wta_path.suffix.lower() == '.wtp':
        wta_cand = wta_path.with_suffix('.wta')
        if wta_cand.exists():
            wtp_path = wta_path
            wta_path = wta_cand
        else:
            wta_cand = wta_path.with_suffix('.wtb')
            if wta_cand.exists():
                wtp_path = wta_path
                wta_path = wta_cand

    try:
        magic, endian, default_ext, _, hdr, wta_data = wtx_read_header(wta_path)
    except ValueError as e:
        print(f"Error: {e}")
        print(f"Make sure you are providing the .wta (header) file as the first argument.")
        return

    count = hdr["count"]
    # Auto-find WTP if not provided and it's not a standalone WTB
    if wtp_path is None and magic == b"\0BTW":
        wtp_cand = wta_path.with_suffix('.wtp')
        if wtp_cand.exists():
            wtp_path = wtp_cand

    is_wta = wtp_path is not None
    if is_wta:
        wtp_data = wtp_path.read_bytes()
    else:
        wtp_data = wta_data
    tex_offsets = [u32(wta_data, hdr["texture_offsets"] + i * 4, endian) for i in range(count)]
    tex_sizes = [u32(wta_data, hdr["texture_sizes"] + i * 4, endian) for i in range(count)] if hdr["texture_sizes"] else [0] * count
    tex_flags = [u32(wta_data, hdr["texture_flags"] + i * 4, endian) for i in range(count)] if hdr["texture_flags"] else [0] * count
    tex_idx = [u32(wta_data, hdr["texture_idx"] + i * 4, endian) for i in range(count)] if hdr["texture_idx"] else [None] * count
    mip_offsets = [u32(wta_data, hdr["mipmap_offsets"] + i * 4, endian) for i in range(count)] if hdr["mipmap_offsets"] else [0] * count
    out_dir.mkdir(parents=True, exist_ok=True)
    textures: list[WtxTexture] = []
    for i in range(count):
        ext = "gtx" if endian == "big" and is_wta else default_ext
        if endian == "big" and is_wta:
            info_off = hdr["texture_info"] + i * 0xC0
            gx2 = wta_data[info_off:info_off + 0x9C]
            payload, data_len, mip_len, _ = make_gtx(gx2, wtp_data, tex_offsets[i], mip_offsets[i], endian)
        else:
            info_off = 0
            data_len = tex_sizes[i]
            mip_len = 0
            payload = wtp_data[tex_offsets[i]:tex_offsets[i] + tex_sizes[i]]
        idx_part = f"_{tex_idx[i]:08x}" if tex_idx[i] is not None else ""
        out_name = f"{wta_path.stem}_{i:03d}{idx_part}.{ext}"
        (out_dir / out_name).write_bytes(payload)
        textures.append(WtxTexture(i, f".{ext}", tex_offsets[i], tex_sizes[i], tex_flags[i], tex_idx[i], info_off, data_len, mip_len, mip_offsets[i], hashlib.sha256(payload).hexdigest()))
    meta = WtxMetadata(
        format="platinum-wtx",
        source=str(wta_path),
        paired_wtp=str(wtp_path) if wtp_path else None,
        endian=endian,
        is_wta=is_wta,
        magic=magic.hex(),
        unknown=hdr["unknown"],
        count=count,
        offsets={k: v for k, v in hdr.items() if k != "count" and k != "unknown"},
        textures=textures,
    )
    (out_dir / "wtx_info.json").write_text(json.dumps(meta.to_json(), indent=2), encoding="utf-8")
    print(f"Extracted {count} textures from {wta_path} to {out_dir} ({endian}-endian)")


def parse_gtx_for_repack(gtx: bytes, endian: str) -> tuple[bytes, bytes, bytes, int, int]:
    if not gtx.startswith(b"Gfx2"):
        raise ValueError("Wii U texture repack expects extracted .gtx files starting with Gfx2")
    gx2_off = 0x40
    gx2 = gtx[gx2_off:gx2_off + 0x9C]
    data_length = u32(gx2, 0x20, endian)
    mipmap_length = u32(gx2, 0x28, endian)
    num_mipmap = u32(gx2, 0x10, endian)
    data_start = 0x20 * 3 + 0x9C
    image = gtx[data_start:data_start + data_length]
    mipmaps = b""
    if num_mipmap > 1 and mipmap_length > 0:
        mip_start = 0x20 * 4 + 0x9C + data_length
        mipmaps = gtx[mip_start:mip_start + mipmap_length]
    return gx2, image, mipmaps, data_length, len(mipmaps)


def wtx_repack(extracted_dir: Path, output_wta: Path) -> None:
    info = json.loads((extracted_dir / "wtx_info.json").read_text(encoding="utf-8"))
    endian = info["endian"]
    is_wta = bool(info["is_wta"])
    textures = info["textures"]
    count = len(textures)
    magic = bytes.fromhex(info["magic"])
    unknown = int(info.get("unknown", 1))
    files = []
    for t in textures:
        matches = sorted(extracted_dir.glob(f"*_{t['index']:03d}*.{t['extension'].lstrip('.')}"))
        if not matches:
            raise FileNotFoundError(f"Could not find extracted texture index {t['index']} in {extracted_dir}")
        files.append(matches[0])
    if endian == "big" and is_wta:
        offsets_off = 0x40
    else:
        offsets_off = 0x20
    sizes_off = align(offsets_off + 4 * count, 0x20)
    flags_off = align(sizes_off + 4 * count, 0x20)
    has_idx = any(t.get("idx") is not None for t in textures)
    idx_off = align(flags_off + 4 * count, 0x20) if has_idx else 0
    after_idx = align((idx_off + 4 * count) if has_idx else (flags_off + 4 * count), 0x20)
    info_off = 0
    mipmap_offs_off = 0
    gx2_list: list[bytes] = []
    image_list: list[bytes] = []
    mip_list: list[bytes] = []
    data_lengths: list[int] = []
    mip_lengths: list[int] = []
    if endian == "big" and is_wta:
        info_off = after_idx
        mipmap_offs_off = align(info_off + 0xC0 * count, 0x20)
        wta_size = align(mipmap_offs_off + 4 * count, 0x20)
        for p in files:
            gx2, img, mip, data_len, mip_len = parse_gtx_for_repack(p.read_bytes(), endian)
            gx2_list.append(gx2)
            image_list.append(img)
            mip_list.append(mip)
            data_lengths.append(data_len)
            mip_lengths.append(mip_len)
        cur = 0
        tex_offsets = []
        for dl in data_lengths:
            cur = align(cur, 0x2000)
            tex_offsets.append(cur)
            cur = align(cur + dl, 0x2000)
        mip_offsets = []
        for ml in mip_lengths:
            if ml:
                cur = align(cur, 0x2000)
                mip_offsets.append(cur)
                cur = align(cur + ml, 0x2000)
            else:
                mip_offsets.append(0)
        wtp_size = cur
        wtp = bytearray(wtp_size)
        for off, img in zip(tex_offsets, image_list):
            wtp[off:off + len(img)] = img
        for off, mip in zip(mip_offsets, mip_list):
            if off and mip:
                wtp[off:off + len(mip)] = mip
        tex_sizes = data_lengths[:]  # Bayonetta tools stores image data length in the size table.
    else:
        payloads = [p.read_bytes() for p in files]
        info_off = 0
        wta_size = after_idx if is_wta else 0
        cur = 0 if is_wta else after_idx
        tex_offsets = []
        tex_sizes = []
        for payload in payloads:
            cur = align(cur, 0x1000)
            tex_offsets.append(cur)
            tex_sizes.append(len(payload))
            cur = align(cur + len(payload), 0x1000)
        if is_wta:
            wtp = bytearray(cur)
            for off, payload in zip(tex_offsets, payloads):
                wtp[off:off + len(payload)] = payload
            wta_size = after_idx
        else:
            wta_size = cur
    wta = bytearray(wta_size)
    wta[0:4] = magic
    pos = 4
    header_values = [unknown, count, offsets_off, sizes_off, flags_off, idx_off, info_off]
    for v in header_values:
        wta[pos:pos + 4] = pack_u32(v, endian); pos += 4
    if endian == "big" and is_wta:
        wta[pos:pos + 4] = pack_u32(mipmap_offs_off, endian)
    wta[offsets_off:offsets_off + 4 * count] = b"".join(pack_u32(v, endian) for v in tex_offsets)
    wta[sizes_off:sizes_off + 4 * count] = b"".join(pack_u32(v, endian) for v in tex_sizes)
    wta[flags_off:flags_off + 4 * count] = b"".join(pack_u32(int(t.get("flag", 0)), endian) for t in textures)
    if has_idx:
        wta[idx_off:idx_off + 4 * count] = b"".join(pack_u32(int(t.get("idx") or 0), endian) for t in textures)
    if endian == "big" and is_wta:
        for i, gx2 in enumerate(gx2_list):
            wta[info_off + i * 0xC0:info_off + i * 0xC0 + 0x9C] = gx2
        wta[mipmap_offs_off:mipmap_offs_off + 4 * count] = b"".join(pack_u32(v, endian) for v in mip_offsets)
    elif not is_wta:
        for off, p in zip(tex_offsets, files):
            payload = p.read_bytes()
            wta[off:off + len(payload)] = payload
    output_wta.parent.mkdir(parents=True, exist_ok=True)
    output_wta.write_bytes(wta)
    if is_wta:
        output_wtp = output_wta.with_suffix(".wtp")
        output_wtp.write_bytes(wtp)
        print(f"Repacked WTA/WTP to {output_wta} + {output_wtp}")
    else:
        print(f"Repacked WTB to {output_wta}")


def detect_mcd_endian(data: bytes) -> str:
    # Bayonetta 2/Wii U MCD has five offset/count pairs. Choose the endian whose offsets are plausible.
    for endian in ("big", "little"):
        pairs = [(u32(data, i * 8, endian), u32(data, i * 8 + 4, endian)) for i in range(5)]
        if all(0 <= off < len(data) and count < 100000 for off, count in pairs) and pairs[0][0] >= 0x28:
            return endian
    return "little"


BUTTON_NAMES = {
    0: "+", 1: "-", 2: "B", 3: "A", 4: "Y", 5: "X", 6: "R", 8: "L",
    11: "DPadUpDown", 12: "DPadLeftRight", 17: "RightStick", 18: "RightStickPress",
    19: "LeftStick", 20: "LeftStickPress", 24: "RightStickRotate", 25: "LeftStickUpDown",
    113: "SwapWeapons", 114: "Evade", 115: "UmbranClimax", 116: "LockOn",
}


def decode_mcd_letter(code: int, pos: int, chars: list[str]) -> str:
    if code < 0x8000:
        return chars[code] if code < len(chars) else f"<BadChar_{code}>"
    if code == 0x8001:
        return " "
    if code == 0x8003:
        return "<" + BUTTON_NAMES.get(pos, str(pos)) + ">"
    return f"<Special0x{code & 0xff:x}_{pos}>"


def mcd_export(mcd_path: Path, out_json: Path, out_txt: Optional[Path]) -> None:
    data = mcd_path.read_bytes()
    endian = detect_mcd_endian(data)
    header = {
        "offset_events": u32(data, 0, endian), "event_count": u32(data, 4, endian),
        "offset_charset": u32(data, 8, endian), "char_count": u32(data, 12, endian),
        "offset_chargraphs": u32(data, 16, endian), "chargraphs_count": u32(data, 20, endian),
        "offset_specialgraphs": u32(data, 24, endian), "specialgraphs_count": u32(data, 28, endian),
        "offset_usedevents": u32(data, 32, endian), "usedevent_count": u32(data, 36, endian),
    }
    chars: list[str] = []
    for i in range(header["char_count"]):
        off = header["offset_charset"] + i * 8
        # lang flags: int16/uint16, UTF-16 code unit, uint32 glyph index
        c = u16(data, off + 2, endian)
        chars.append(chr(c))
    events = []
    for ei in range(header["event_count"]):
        eoff = header["offset_events"] + ei * 16
        paragraphs_off = u32(data, eoff, endian)
        paragraph_count = u32(data, eoff + 4, endian)
        sequence = u32(data, eoff + 8, endian)
        event_id = u32(data, eoff + 12, endian)
        paragraphs = []
        for pi in range(paragraph_count):
            poff = paragraphs_off + pi * 20
            strings_off = u32(data, poff, endian)
            string_count = struct.unpack_from((">" if endian == "big" else "<") + "i", data, poff + 4)[0]
            strings = []
            for si in range(string_count):
                soff = strings_off + si * 24
                letters_off = u32(data, soff, endian)
                length = u32(data, soff + 8, endian)
                nletters = max(0, (length - 1) // 2)
                text_parts = []
                letters = []
                for li in range(nletters):
                    loff = letters_off + li * 4
                    code = u16(data, loff, endian)
                    pos = i16(data, loff + 2, endian)
                    letters.append({"code": code, "pos": pos})
                    text_parts.append(decode_mcd_letter(code, pos, chars))
                strings.append({"index": si, "offset_table_entry": soff, "offset": letters_off, "length": length, "text": "".join(text_parts), "letters": letters})
            paragraphs.append({"index": pi, "strings_offset": strings_off, "string_count": string_count, "strings": strings})
        events.append({"index": ei, "event_id": event_id, "sequence": sequence, "paragraph_count": paragraph_count, "paragraphs": paragraphs})
    used_events = []
    for i in range(header["usedevent_count"]):
        off = header["offset_usedevents"] + i * 40
        used_events.append({"event_id": u32(data, off, endian), "event_index": u32(data, off + 4, endian), "name": read_cstr(data[off + 8:off + 40])})
    doc = {"format": "bayonetta2-wiiu-mcd", "source": str(mcd_path), "endian": endian, "header": header, "chars": chars, "used_events": used_events, "events": events}
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    if out_txt:
        lines = []
        used_by_idx = {u["event_index"]: u for u in used_events}
        for ev in events:
            name = used_by_idx.get(ev["index"], {}).get("name", "")
            lines.append(f"# Event {ev['index']} id=0x{ev['event_id']:08X} {name}")
            for par in ev["paragraphs"]:
                for s in par["strings"]:
                    lines.append(s["text"])
                lines.append("")
        out_txt.write_text("\n".join(lines), encoding="utf-8")
    print(f"Exported {len(events)} MCD events from {mcd_path} to {out_json} ({endian}-endian)")


def mcd_import(original_mcd: Path, edited_json: Path, output_mcd: Path) -> None:
    """Simple safe importer for same-character-set edits.

    This importer rewrites MCD letter streams and string table lengths using the existing
    charset. It supports literal characters present in the original charset, spaces, and
    preserved tags such as <A>/<B>/<Special0x.._..>. It appends rebuilt letter streams at
    the end of the file and updates string offsets/lengths, preserving all graph tables.
    """
    original = bytearray(original_mcd.read_bytes())
    doc = json.loads(edited_json.read_text(encoding="utf-8"))
    endian = doc.get("endian") or detect_mcd_endian(original)
    chars = doc["chars"]
    char_to_idx = {c: i for i, c in enumerate(chars)}
    tag_to_letter = {f"<{name}>": (0x8003, pos) for pos, name in BUTTON_NAMES.items()}

    def encode_text(text: str) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        i = 0
        while i < len(text):
            if text[i] == "<":
                j = text.find(">", i)
                if j != -1:
                    tag = text[i:j + 1]
                    if tag in tag_to_letter:
                        out.append(tag_to_letter[tag]); i = j + 1; continue
                    if tag.startswith("<Special0x") and "_" in tag:
                        try:
                            a, b = tag[9:-1].split("_", 1)
                            out.append((0x8000 | int(a, 16), int(b)))
                            i = j + 1; continue
                        except Exception:
                            pass
            c = text[i]
            if c == " ":
                out.append((0x8001, 0))
            elif c in char_to_idx:
                out.append((char_to_idx[c], 0))
            else:
                raise ValueError(f"Character {c!r} is not present in the original MCD charset")
            i += 1
        return out

    cursor = align(len(original), 4)
    if cursor > len(original):
        original.extend(b"\0" * (cursor - len(original)))
    for ev in doc["events"]:
        for par in ev["paragraphs"]:
            for s in par["strings"]:
                letters = encode_text(s["text"])
                new_off = cursor
                blob = b"".join(pack_u16(code, endian) + pack_i16(pos, endian) for code, pos in letters) + pack_u16(0x8000, endian)
                original.extend(blob)
                cursor += len(blob)
                length = len(letters) * 2 + 1
                soff = int(s["offset_table_entry"]) if "offset_table_entry" in s else None
                # Fall back by finding the string table entry that originally pointed to old offset.
                if soff is None:
                    old_off = int(s["offset"])
                    found = original.find(pack_u32(old_off, endian), 0, min(len(original), doc["header"]["offset_charset"]))
                    if found < 0:
                        raise ValueError(f"Could not locate string-table entry for old offset 0x{old_off:X}")
                    soff = found
                original[soff:soff + 4] = pack_u32(new_off, endian)
                original[soff + 8:soff + 12] = pack_u32(length, endian)
                original[soff + 12:soff + 16] = pack_u32(length, endian)
    output_mcd.write_bytes(original)
    print(f"Imported edited text into {output_mcd}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Platinum Wii U DAT/WTA/WTP/MCD tools")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("dat-extract"); p.add_argument("dat"); p.add_argument("out")
    p = sub.add_parser("dat-repack"); p.add_argument("folder"); p.add_argument("out")
    p = sub.add_parser("wtx-extract"); p.add_argument("wta_or_wtb"); p.add_argument("out"); p.add_argument("--wtp")
    p = sub.add_parser("wtx-repack"); p.add_argument("folder"); p.add_argument("out_wta")
    p = sub.add_parser("mcd-export"); p.add_argument("mcd"); p.add_argument("out_json"); p.add_argument("--txt")
    p = sub.add_parser("mcd-import"); p.add_argument("original_mcd"); p.add_argument("edited_json"); p.add_argument("out_mcd")
    args = parser.parse_args(argv)
    if args.cmd == "dat-extract":
        dat_extract(Path(args.dat), Path(args.out))
    elif args.cmd == "dat-repack":
        dat_repack(Path(args.folder), Path(args.out))
    elif args.cmd == "wtx-extract":
        wtx_extract(Path(args.wta_or_wtb), Path(args.wtp) if args.wtp else None, Path(args.out))
    elif args.cmd == "wtx-repack":
        wtx_repack(Path(args.folder), Path(args.out_wta))
    elif args.cmd == "mcd-export":
        mcd_export(Path(args.mcd), Path(args.out_json), Path(args.txt) if args.txt else None)
    elif args.cmd == "mcd-import":
        mcd_import(Path(args.original_mcd), Path(args.edited_json), Path(args.out_mcd))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
