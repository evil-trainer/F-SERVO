# F-SERVO Wii U Support Validation Report

This report summarizes the Wii U / big-endian work performed on the attached `ui_title_us.dat` sample and the modified F-SERVO repository.

## Scope

The implementation adds support for a Platinum Games Wii U DAT sample and its localization-related contents. The work focused on **DAT/DTT archive endianess**, **WTA/WTP texture extraction and reinsertion**, and **MCD message export/import**. The code changes were made directly in the Flutter/Dart F-SERVO project, and a standalone Python 3 utility was added at `tools/platinum_wiiu_tools.py` for Windows-friendly command-line workflows.

## Binary findings

The sample `ui_title_us.dat` is a **big-endian Wii U DAT**. Its archive metadata decodes correctly when interpreted as big-endian and produces 55 internal entries. The extracted entries include two Wii U WTA/WTP texture pairs and one MCD localization file relevant to title/menu localization workflows.

| Finding | Value |
|---|---|
| Archive endianess | Big-endian |
| Platform metadata written by tools | `wiiu` |
| Extracted DAT entries | 55 |
| Repacked DAT size | 24,746,752 bytes |
| Repacked DAT SHA-256 | `9ce166e39d2e765c6561d09a77cb17509f95752fe5229bd719de5b461e543d67` |

## Texture validation

The Wii U WTA parser recognizes the `\0BTW` header and the larger GX2 metadata records used by the Wii U layout. Texture extraction emits `.gtx` files rather than `.dds` files, because Wii U texture payloads retain GX2/GTX metadata rather than PC DDS headers.

| Pair | Extracted GTX files | Round-trip result |
|---|---:|---|
| `title.wta` / `title.wtp` | 9 | Rebuilt pair re-extracted to GTX files with matching payload hashes. |
| `messtitle.wta` / `messtitle.wtp` | 1 | Rebuilt pair re-extracted to GTX files with matching payload hash. |

The extracted GTX files were also converted through an inspected local GTX-to-DDS converter and then to PNG previews for visual inspection. A contact sheet is included separately as `ui_title_us_texture_contact_sheet.png`.

## MCD validation

The MCD parser/exporter detects Wii U big-endian files and writes metadata sufficient for safe reinsertion. The standalone Python utility exported `messtitle.mcd` to JSON/TXT, reimported it without text changes, and re-exported it for string-level comparison.

| File | Size | SHA-256 |
|---|---:|---|
| `messtitle_rebuilt.mcd` | 76,142 bytes | `765e49766260e3c1e7904e2776a0a203074977b6425ddd78acd83cab0d233969` |

## F-SERVO code validation

The modified Flutter/Dart project was validated with `flutter analyze` and a Linux debug build in the sandbox. `flutter analyze` reports no Dart errors after the modifications; it still reports existing warnings/informational diagnostics from the upstream project style and missing optional asset folders. A Linux debug build completed successfully after installing native Linux Flutter dependencies.

| Check | Result |
|---|---|
| Python utility syntax and command validation | Passed |
| DAT extract/build validation | Passed |
| WTA/WTP extract/build/re-extract hash validation | Passed |
| MCD export/import validation | Passed |
| `flutter analyze` | No errors; warnings/info remain |
| `flutter build linux --debug` | Passed |

## Windows build note

A Windows `.exe` was not generated in the Linux sandbox because Flutter desktop Windows compilation requires a Windows host and the Visual Studio C++ build tools. The repository includes `build_windows_release.bat`; on Windows, after installing Flutter and Visual Studio Build Tools, run:

```bat
build_windows_release.bat
```

The expected output folder is:

```text
build\windows\x64\runner\Release\
```

## Main files changed

| Path | Purpose |
|---|---|
| `lib/fileTypeUtils/dat/datExtractor.dart` | DAT endianess autodetection and Wii U metadata output. |
| `lib/fileTypeUtils/dat/datRepacker.dart` | DAT repacking with preserved endianess. |
| `lib/fileTypeUtils/wta/wtaReader.dart` | Wii U WTA `\0BTW` parsing/writing and GX2 metadata preservation. |
| `lib/fileTypeUtils/wta/wtaExtractor.dart` | GTX extraction/import helpers for Wii U WTA/WTP. |
| `lib/stateManagement/openFiles/types/WtaWtpData.dart` | UI data-flow changes for `.gtx` extraction/reinsertion. |
| `lib/widgets/filesView/types/wtaWtpEditor.dart` | Import filter accepts `.gtx` for Wii U containers. |
| `lib/fileTypeUtils/mcd/mcdIO.dart` | Big-endian MCD detection/read/write support. |
| `lib/utils/utils.dart` | DAT metadata object now carries endian/platform information. |
| `lib/widgets/tools/toolsOverview.dart` | Case-sensitive import fix. |
| `tools/platinum_wiiu_tools.py` | Standalone Python 3 DAT/WTA/WTP/MCD utility for Windows-friendly workflows. |
| `README.md` | Updated with Wii U support, utility usage, validation and Windows build instructions. |
| `build_windows_release.bat` | Convenience Windows build script. |
