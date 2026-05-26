# Guia: Como Instalar o Flutter e Compilar o F-SERVO no Windows

Este guia foi criado para que você possa gerar o executável `.exe` do F-SERVO diretamente no seu computador. Siga estes 4 passos simples:

---

## 1. Instalar as Ferramentas de Compilação (C++)
O Flutter para Windows precisa do compilador da Microsoft para funcionar.
1. Baixe o **[Visual Studio Build Tools 2022](https://visualstudio.microsoft.com/visual-cpp-build-tools/)**.
2. Ao abrir o instalador, selecione a carga de trabalho: **"Desenvolvimento para desktop com C++"** (Desktop development with C++).
3. Certifique-se de que, no painel à direita, os seguintes itens estão marcados:
   - MSVC v143 - VS 2022 C++ x64/x86 build tools
   - Windows 10 SDK (ou 11)
4. Clique em **Instalar** e aguarde (isso pode demorar um pouco).

---

## 2. Instalar o Git
O Flutter usa o Git para gerenciar suas versões.
1. Baixe e instale o **[Git para Windows](https://git-scm.com/download/win)**.
2. Durante a instalação, pode manter todas as opções padrão (basta clicar em "Next").

---

## 3. Instalar o SDK do Flutter
1. Baixe o pacote estável mais recente do Flutter: **[Download Flutter SDK](https://docs.flutter.dev/get-started/install/windows)**.
2. Extraia o arquivo zip em uma pasta simples (ex: `C:\src\flutter`). **Não instale em pastas protegidas como `C:\Program Files`**.
3. **Adicionar ao PATH:**
   - No menu Iniciar, digite "Variáveis de ambiente" e selecione "Editar as variáveis de ambiente do sistema".
   - Clique no botão **Variáveis de Ambiente**.
   - Em "Variáveis do usuário", selecione **Path** e clique em **Editar**.
   - Clique em **Novo** e cole o caminho da pasta `bin` do flutter (ex: `C:\src\flutter\bin`).
   - Clique em OK em todas as janelas.

---

## 4. Validar e Compilar o F-SERVO
1. Abra o **Prompt de Comando (CMD)** ou **PowerShell**.
2. Digite o comando abaixo para verificar se tudo está certo:
   ```cmd
   flutter doctor
   ```
   *(Se ele pedir para aceitar licenças, rode `flutter doctor --android-licenses`, mas para Windows o importante é o item "Visual Studio" estar com um check verde).*
3. Navegue até a pasta onde você extraiu o **F-SERVO_WIIU_source_v3.zip**.
4. Execute o script que eu preparei:
   ```cmd
   build_windows_release.bat
   ```
5. **Pronto!** Quando o processo terminar, o seu executável estará aqui:
   `build\windows\x64\runner\Release\F-SERVO.exe`

---

## Dicas de Solução de Problemas
- **Erro "flutter não é reconhecido":** Você esqueceu de configurar o PATH no Passo 3 ou precisa reiniciar o CMD.
- **Erro de C++ ou SDK:** O Passo 1 não foi concluído corretamente. Reabra o instalador do Visual Studio e verifique se o "Desktop development with C++" está instalado.
- **Lentidão:** A primeira compilação é sempre mais lenta pois o Flutter baixa as dependências. As próximas serão instantâneas.
