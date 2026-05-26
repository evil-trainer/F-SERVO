# F-SERVO (File and Scripts EditoR Version One)

A tool for modding a variety of files in Nier:Automata.

This fork adds **experimental Platinum Games Wii U / big-endian support** for Bayonetta-style archives and localization assets, based on byte-level analysis of a Wii U `ui_title_us.dat` sample and cross-checking against the public `bayonetta_tools` format templates/scripts.

Supported file types:
- DAT, DTT
- PAK, YAX, XML (xml quest scripts)
- BIN (ruby quest scripts)
- BXM (XML config files)
- WTA, WTP, WTB (texture files)
- BNK, WEM, WAI, WSP (audio files)
- TMD (localized UI text)
- MCD (localized UI text)
- SMD (localized subtitles)
- FTB (fonts)
- CPK extract
- Save files (SlotData_X.dat)
- EST (effects)

## Wii U / big-endian Platinum Games support added in this fork

This fork extends the existing Nier:Automata-oriented code paths so they can also handle the Wii U sample layout used by Platinum Games titles such as Bayonetta 2. The implementation is intentionally conservative: existing PC/little-endian Nier:Automata behavior is preserved, while Wii U files are detected through header plausibility checks, magic values and metadata stored during extraction.

| Area | Added behavior |
|---|---|
| DAT/DTT archives | Autodetects little-endian PC archives and big-endian Wii U archives. Extracted `dat_info.json` now stores `endian` and `platform`, and repacking uses the original endianess instead of assuming little-endian. |
| WTA/WTP textures | Supports Wii U big-endian `\0BTW` WTA headers, 0xC0-byte GX2 texture metadata records, `.wtp` payload offsets/sizes and mipmap offsets/sizes. Wii U texture extraction emits `.gtx` instead of `.dds`. |
| WTA/WTP reinsertion | Wii U `.gtx` imports are parsed back into GX2 metadata, main image data and mipmap data. Rebuilt `.wta/.wtp` preserve Wii U layout/alignment. |
| MCD localization | Adds endianess detection for MCD files so Bayonetta 2 / Wii U message containers can be read and rewritten without byte-order corruption. |
| UI import filter | The WTA/WTP editor accepts `.gtx` when the currently opened texture container is Wii U, while preserving `.dds` for the original PC workflow. |
| Case-sensitive build fix | Corrected the `BatchLocalizationTool.dart` import capitalization so the repository analyzes/builds correctly on Linux as well as Windows. |

The additional command-line utility `tools/platinum_wiiu_tools.py` is included for Windows-friendly extraction/rebuild workflows outside the Flutter UI. It is pure Python 3 and does not require Visual Studio.

## Python utility for Wii U DAT, WTA/WTP and MCD

The file `tools/platinum_wiiu_tools.py` provides standalone commands for localization and texture workflows. It is useful both as a validation tool and as a scriptable Windows workflow.

```bat
py -3 tools\platinum_wiiu_tools.py --help
```

Typical usage:

```bat
REM Extract a Wii U DAT archive and preserve dat_info.json metadata
py -3 tools\platinum_wiiu_tools.py dat-extract ui_title_us.dat extracted_ui_title_us

REM Rebuild a DAT from an extracted folder that contains dat_info.json
py -3 tools\platinum_wiiu_tools.py dat-build extracted_ui_title_us ui_title_us_repacked.dat

REM Extract Wii U WTA/WTP textures as GTX files
py -3 tools\platinum_wiiu_tools.py wtx-extract extracted_ui_title_us\title.wta title_wtx --wtp extracted_ui_title_us\title.wtp

REM Rebuild Wii U WTA/WTP from GTX files plus wtx_info.json
py -3 tools\platinum_wiiu_tools.py wtx-build title_wtx title_rebuilt.wta --wtp title_rebuilt.wtp

REM Export Wii U MCD strings to JSON/TXT
py -3 tools\platinum_wiiu_tools.py mcd-export extracted_ui_title_us\messtitle.mcd messtitle.json --txt messtitle.txt

REM Import edited MCD JSON back into a Wii U MCD
py -3 tools\platinum_wiiu_tools.py mcd-import messtitle.json messtitle_rebuilt.mcd
```

The MCD JSON export stores the original string entry offsets so that unchanged or duplicated strings can be reinserted safely. For translated strings, keep the JSON structure intact and edit only the exported text values unless you also intend to adjust low-level metadata manually.

## Validation performed for the Wii U sample

The Wii U `ui_title_us.dat` sample was analyzed byte by byte and validated end-to-end with fresh output directories after implementation. The sample is a **big-endian DAT** that contains, among other entries, `title.wta/title.wtp`, `messtitle.wta/messtitle.wtp` and `messtitle.mcd`.

| Validation step | Result |
|---|---|
| DAT extraction | The big-endian file table was detected and all internal files were extracted with names, offsets and sizes preserved in `dat_info.json`. |
| WTA/WTP extraction | `title.wta/title.wtp` produced 9 `.gtx` textures; `messtitle.wta/messtitle.wtp` produced 1 `.gtx` texture. |
| Texture visual check | GTX files were converted through an inspected local GTX-to-DDS converter and PNG previews/contact sheet were generated for visual inspection. |
| WTA/WTP round-trip | Rebuilt WTA/WTP pairs were re-extracted and the resulting GTX payload hashes matched the original extracted GTX files. |
| MCD export/import | `messtitle.mcd` strings were exported to JSON/TXT, reimported without text changes, and re-exported for string-level comparison. |
| DAT rebuild | Extracted Wii U DAT contents were repacked using big-endian metadata into `ui_title_us_repacked.dat`. |
| Flutter analysis | `flutter analyze` reports no errors after the changes; remaining diagnostics are warnings/info already present in the project style/assets. |
| Compile validation | A Linux debug build was successfully produced in the sandbox after installing Linux native Flutter dependencies. Windows executables must still be built on Windows because Flutter desktop Windows builds require a Windows host. |

## Installation

Go to the [releases](https://github.com/ArthurHeitmann/F-SERVO/releases) page and download the latest `F-SERVO_x.x.x.7z` file. Extract the archive and run `F-SERVO.exe`.

For this Wii U fork, if a prebuilt Windows executable is not included, build it locally from source using the Windows instructions below. This project is a **Flutter/Dart desktop application**, not a .NET application, so `dotnet build` is not applicable.

## Usage

See the incomplete [wiki](https://github.com/ArthurHeitmann/F-SERVO/wiki/Getting-Started).

For Wii U texture localization workflows, open a Wii U WTA/WTP pair in the normal texture editor. Extracted textures will use the `.gtx` extension. When replacing textures, import `.gtx` files with compatible GX2 texture metadata. The standalone Python utility can also be used for batch workflows and round-trip validation.

## Screenshots

![image](https://user-images.githubusercontent.com/37270165/221270764-b10a7810-f704-47c6-9b1b-fe652d00ee05.png)  
Editing quest scripts

![image](https://user-images.githubusercontent.com/37270165/222829431-4c1f1123-f6a5-48bc-b211-07cd5126658b.png)  
Music replacement & loop point editing

![image](https://github.com/ArthurHeitmann/F-SERVO/assets/37270165/36770284-fb7d-4293-9656-d64e28f3e74f)  
MCD editing

## Support

- Open an issue on this repository
- [Nier Discord modding server](https://discord.gg/ngAK7rT)
- My Discord name: @raiderbv

## Building on Windows

1. Install [Flutter for Windows](https://docs.flutter.dev/get-started/install/windows). During setup, make sure `flutter` is available from `cmd` or PowerShell.

2. Install **Visual Studio Build Tools 2022** with the "Desktop development with C++" workload. Flutter requires the Windows C++ toolchain to build desktop apps.

3. Clone this repository:

   ```bat
   git clone https://github.com/YOUR_USER/F-SERVO.git
   cd F-SERVO
   ```

4. Get all assets:

   ```bat
   git submodule update --init --recursive
   ```

   Download additional assets from [here](https://github.com/ArthurHeitmann/F-SERVO/releases/tag/assetsV0.7.0) and extract the folders inside into the `assets` folder. This keeps the raw git repository smaller than 100 MB.

5. Update dependencies:

   ```bat
   flutter pub get
   ```

6. Build the Windows executable:

   ```bat
   flutter build windows --release
   ```

7. The executable will be generated under:

   ```text
   build\windows\x64\runner\Release\
   ```

## Building (for developers only)

1. [Setup Flutter for Windows](https://docs.flutter.dev/get-started/install/windows)

2. Git clone this repository

3. Get all assets
   1. Update git submodules with
      ```bat
      git submodule update --init
      ```
   2. Download additional assets from [here](https://github.com/ArthurHeitmann/F-SERVO/releases/tag/assetsV0.7.0) and extract the folders inside into the `assets` folder. (This is so that the raw git repo isn't 100+ MB large)

4. Update dependencies with
   ```bat
   flutter pub get
   ```

5. Run with your IDE of choice or for release build:
   ```bat
   flutter build windows --release
   ```
