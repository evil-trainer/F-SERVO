# Guia de Uso: F-SERVO & Platinum Wii U Tools (Windows)

Este guia explica como realizar o fluxo completo de extração e conversão de arquivos do jogo (DAT, WTA/WTP, MCD) no Windows.

## 1. Extração do DAT (O arquivo principal)
O arquivo `ui_title_us.dat` contém todos os outros arquivos. Use o script Python para extrair tudo mantendo o endianess correto (Wii U = Big Endian).

```cmd
python platinum_wiiu_tools.py dat-extract ui_title_us.dat ui_title_us_extracted
```
*Isso criará a pasta `ui_title_us_extracted` com 55 arquivos.*

---

## 2. Extração de Texturas (WTA/WTP -> GTX)
As texturas de Wii U não são DDS, são **GTX**. O script Python extrai o par `.wta` (cabeçalho) e `.wtp` (dados) para arquivos `.gtx`.

```cmd
python platinum_wiiu_tools.py wtx-extract ui_title_us_extracted\title.wta title_textures
```
*O script agora detecta o `.wtp` automaticamente se ele estiver na mesma pasta.*

---

## 3. Conversão de Texturas (GTX -> DDS -> PNG)
Para ver as imagens "lindas" que eu gerei, você precisa de dois passos extras:

### Passo A: GTX para DDS
Use a ferramenta **GTX-Extractor** (não incluída no F-SERVO original, mas essencial para Wii U).
1. Baixe o [GTX-Extractor](https://github.com/AboodXD/GTX-Extractor).
2. Execute:
   ```cmd
   python gtx_extract.py title_textures\title_000_xxxx.gtx
   ```
   *Isso gerará um arquivo `.dds`.*

### Passo B: DDS para PNG
Você pode abrir o `.dds` no Photoshop/GIMP ou usar o script `dds_to_png_preview.py` que eu incluí:
```cmd
python dds_to_png_preview.py title_textures
```

---

## 4. Extração de Textos (MCD -> TXT/JSON)
O F-SERVO agora suporta MCD de Wii U, mas para uma extração limpa em texto puro, use o script Python:

```cmd
python platinum_wiiu_tools.py mcd-export ui_title_us_extracted\messtitle.mcd messtitle.txt
```
*Isso gerará o arquivo `messtitle.txt` com todos os diálogos perfeitamente extraídos.*

---

## 5. Por que o F-SERVO deu erro? (Resolvido)
1. **Erro de DTT:** O F-SERVO original de Nier Automata (PC) exige um arquivo `.dtt` para texturas. Eu modifiquei o código para que ele procure no mesmo diretório do `.dat` se o `.dtt` não existir.
2. **Erro de Magic:** No `platinum_wiiu_tools.py`, você tentou passar o `.wtp` como primeiro argumento. O primeiro argumento **deve ser sempre o .wta** (que contém a tabela de nomes e formatos). Eu atualizei o script para detectar se você inverteu os arquivos e corrigir sozinho.

## Resumo de Comandos Corrigidos
| Tarefa | Comando |
| :--- | :--- |
| **Extrair DAT** | `python platinum_wiiu_tools.py dat-extract ui_title_us.dat out` |
| **Extrair Texturas** | `python platinum_wiiu_tools.py wtx-extract out\title.wta tex_out` |
| **Exportar Textos** | `python platinum_wiiu_tools.py mcd-export out\messtitle.mcd text.txt` |
| **Importar Textos** | `python platinum_wiiu_tools.py mcd-import out\messtitle.mcd text.json` |
