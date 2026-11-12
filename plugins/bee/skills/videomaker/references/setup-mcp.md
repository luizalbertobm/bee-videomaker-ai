# Registar Higgsfield e ElevenLabs no Claude Code

**O ElevenLabs já está ligado ao Claude como conector da app** (tools `creative_*`); o registo abaixo só é preciso em instalações novas do Claude Code CLI ou se as tools não aparecerem na sessão. Ambos são servidores remotos HTTP com OAuth — não precisam de API key.

Correr no terminal, fora de uma sessão do Claude Code:

```bash
# Higgsfield (imagens, vídeo, 3D, upscale, reframe)
claude mcp add --transport http --scope user higgsfield https://mcp.higgsfield.ai/mcp

# ElevenLabs (voz, transcrição, flows)
claude mcp add --transport http --scope user elevenlabs https://api.elevenlabs.io/v1/mcp

# Verificar
claude mcp list
```

Depois, dentro de uma sessão interativa do Claude Code, correr `/mcp` e concluir o login no browser para cada servidor.

- `--scope user` disponibiliza os servidores em todos os projetos; omitir para registar só neste projeto.
- O nome dado no `claude mcp add` (`higgsfield`, `elevenlabs`) vira o prefixo das tools: `mcp__higgsfield__generate_video`, `mcp__elevenlabs__creative_generate_speech`. Em conectores ligados pela app Claude o prefixo pode ser um identificador gerado; procurar pelo sufixo da tool.
- Sem os conectores a skill continua a funcionar para roteiro, cenas Canvas (`${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/render_canvas.py`) e montagem (`${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/montagem.ffmpeg.sh`), e pode usar narração já existente em `sources/`.

## Dependências locais

```bash
sudo apt install ffmpeg bc
pip install playwright
# Google Chrome já instalado é suficiente (render usa channel="chrome"); alternativa:
# playwright install chromium

# Transcrição local (scripts/transcribe.py): faster-whisper = Whisper em CTranslate2
pip install faster-whisper
# Opcional, para usar a GPU NVIDIA (sem isto cai automaticamente para CPU int8):
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

O modelo (`large-v3`, ~3 GB) é descarregado do Hugging Face na primeira execução para `~/.cache/huggingface/`. Modelos mais pequenos: `--model medium` (1,5 GB) ou `--model small` (500 MB).

Fontes: [Higgsfield MCP](https://higgsfield.ai/mcp) · [ElevenLabs hosted MCP](https://elevenlabs.io/docs/eleven-agents/operate/hosted-mcp)

## Chaves dos bancos de stock (scripts/stock.py)

Só o Pixabay precisa de chave, gratuita e obtida em segundos com uma conta. O Pexels foi retirado: a emissão de chaves novas está suspensa (confirmado na página oficial a 12/11/2026) e sem chave a API responde 401.

- Pixabay: https://pixabay.com/api/docs/ → a chave aparece na própria página depois do login. Limite 100 pedidos/min; o Pixabay exige cache de 24 h, que o script faz em `~/.cache/videomaker/stock/`.
- Openverse: sem chave. Limite anónimo baixo; para mais, registar em https://api.openverse.org/v1/#tag/auth.

Guardar num ficheiro `.env` na raiz do projeto (não o pôr em git):

```
PIXABAY_API_KEY=xxxxxxxx
```
