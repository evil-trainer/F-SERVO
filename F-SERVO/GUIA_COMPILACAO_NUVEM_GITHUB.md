# Guia: Como Compilar o F-SERVO na Nuvem (Grátis e sem instalar nada!)

Como o Visual Studio ocupa 5GB+ de espaço, vamos usar os servidores do GitHub para compilar o executável para você. Você não gastará nenhum MB de espaço no seu disco rígido.

---

## Passo 1: Criar um Repositório no seu GitHub
1. Acesse seu [GitHub](https://github.com/) e crie um novo repositório (pode ser privado ou público).
2. Dê um nome como `F-SERVO-WiiU`.

---

## Passo 2: Subir o Código
Você pode fazer isso direto pelo site do GitHub (sem instalar nada):
1. No seu novo repositório, clique em **"uploading an existing file"**.
2. Arraste **todos os arquivos e pastas** que estão dentro do `F-SERVO_WIIU_source_v3.2.zip` para a janela do navegador.
3. Clique em **"Commit changes"** no final da página.
   *Certifique-se de que a pasta `.github/workflows` também foi enviada.*

---

## Passo 3: O GitHub Compila para Você
Assim que você subir os arquivos, o "robô" do GitHub vai começar a trabalhar:
1. Clique na aba **"Actions"** no topo da página do seu repositório.
2. Você verá uma tarefa chamada **"Build Windows Release"** rodando (com um ícone amarelo girando).
3. Aguarde cerca de 5 a 10 minutos até que o ícone fique **verde**.

---

## Passo 4: Baixar seu Executável
1. Clique no nome da tarefa que terminou (`Build Windows Release`).
2. Role a página até o final, na seção **"Artifacts"**.
3. Clique em **"F-SERVO-Windows-Release"**.
4. O GitHub vai baixar um arquivo `.zip` contendo o seu `F-SERVO.exe` prontinho para uso!

---

### Vantagens deste método:
- **Espaço em disco usado:** 0 MB.
- **Processamento usado:** 0% do seu PC (quem trabalha é o servidor da Microsoft).
- **Praticidade:** Você terá o executável oficial gerado em um ambiente de compilação limpo.
