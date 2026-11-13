# Lições aprendidas

Ler antes de estimar custos, gerar áudio/vídeo ou montar. Acrescentar uma linha no fim de cada produção.

## Formato e duração
- O modelo de vídeo **ignora** "9:16" escrito no prompt. Passar o aspect ratio como parâmetro e confirmar `width`/`height` no resultado; se vier errado, `reframe` ou `pad`/`crop` no ffmpeg, nunca regenerar só por isso.
- Gerar a narração **antes** do vídeo e ler a duração real; ~2 palavras por segundo no eleven_v4 (15 palavras deram 7 s). Cena = áudio + 0,4–0,8 s de respiro.
- Transcrever qualquer narração já existente antes de desenhar as cenas, para o texto no ecrã acompanhar o que se ouve.

## Custos observados (ElevenLabs, nov. 2026)
- Fala eleven_v4: 26–50 créditos por frase curta (5 frases, ~15 s de voz: ~200 créditos). `estimate_only` devolve o custo exato.
- Música eleven_music_v2_5: ~900 créditos por faixa de 22 s (estimativa dizia 1500), 1–2 min a gerar.
- Vídeo 5 s (flow ElevenLabs): Seedance 2.5 ≈ 14.000; Seedance v2 mini ≈ 4.600; LTX v2 fast ≈ 1.450. Higgsfield Seedance 2.5 5 s = 35 créditos. Mini/fast para testes, modelo grande só para a entrega.
- Os links de download expiram em ~2,5 h: descarregar logo para `audio/` e `scenes/`.

## Canvas e render
- `render_canvas.py` substitui `requestAnimationFrame` por uma função vazia e chama `renderFrame(t)` por frame: tudo deve derivar de `t`; nada de estado acumulado ou `performance.now()`.
- Imagens por `file://` deixam o canvas "tainted" e `toDataURL` falha; o render lança o Chrome com `--allow-file-access-from-files`. Não remover a flag.
- Só expor `renderFrame` depois de imagens e fontes carregarem (o render espera por ela).
- SVG copiado de HTML inline (`<svg viewBox=…>` sem `xmlns`) não carrega como `<img>`: acrescentar `xmlns`, `width`/`height` e trocar `fill="currentColor"` por uma cor.
- `arc()` com raio negativo vindo do overshoot do `backOut`: proteger com `Math.max(0, …)`.
- Varrimento de luz em `lighter` mancha fundos escuros; redesenhar o texto com um gradiente como `fillStyle`.
- Caixas de texto: nunca fixar a largura; medir com `measureText` e somar padding. Rever os frames finais de cada cena em meia resolução antes de aceitar.
- Ao gerar vários ficheiros a partir de um cabeçalho com `sed`, usar marcadores únicos (`__DUR__`), não substrings de identificadores.
- Três cenas (~450 frames) renderizam em paralelo em cerca de um minuto; lançar com `&` e `wait`. Folhas de contacto (`scripts/contact_sheet.py`, só ffmpeg) são a forma mais barata de rever uma animação.

## Logos em SVG
- SVGs exportados sem IDs ainda têm cada peça num grupo de topo: dá para os dividir em camadas com o mesmo viewBox e animar cada uma (escala, rotação com pivô, alpha) sem redesenhar a marca. Classificar letras por serem `<g fill=…>` sem clip-path, não pela cor.

## Montagem
- Canvas renderiza para `scenes/NN.mp4`; `build/` é só intermediário. A montagem lê `scenes/NN.*` e `audio/NN.mp3`.
- `concat -c copy` falha a misturar cenas com e sem áudio: o script dá silêncio às cenas mudas e normaliza para AAC.
- Narração mais curta que a cena cortava o vídeo por `-shortest`; agora `-af apad`.
- Música de fundo: `musica.mp3` na raiz, volume `MUSIC_VOL`, ducking por `sidechaincompress`, mistura em estéreo.
- `LC_ALL=C` no script: com locale em vírgula decimal, `awk` escreve "18,38" e o ffmpeg lê dois filtros.
- Volume final normalizado a `LUFS=-14` (alvo de Instagram/TikTok/YouTube) e pico verdadeiro ≤ `TP=-1.5` dBTP, em duas passagens de `loudnorm` (a 1.ª mede, a 2.ª aplica um ganho linear com os valores medidos, sem compressão dinâmica); `LUFS=0` desliga. O `loudnorm` alonga o áudio ~0,1 s, o que com `-shortest` e `-c:v copy` cortava 3 s do fim do vídeo: a faixa tem de se cortar com `atrim` pela duração do vídeo, não pelo `-shortest`.

## Stock e ícones
- O Pixabay é a única fonte de vídeo gratuito com API utilizável: o Pexels suspendeu a emissão de chaves novas e foi retirado da skill. A API de vídeo do Pixabay ignora `orientation` (o script filtra localmente) e as imagens chegam com no máximo 1280 px no lado maior. Openverse (imagens CC e sons do Freesound) não precisa de chave mas devolve 502/504 de vez em quando; fotos do Flickr vêm com 1024 px no máximo.
- Licenças CC BY-SA obrigam a publicar o vídeo com a mesma licença; preferir CC0 ou CC BY. Entregar sempre `creditos.md`.
- Ícones: Lucide (ISC) via `icons.py`; `qr-code` serve para Pix. Em ícones pequenos ao lado de texto bold, `lineWidth` 2,2–3.

## Transcrição local
- faster-whisper `large-v3` na GPU transcreve 7 s em ~1,4 s; `small` em CPU em ~3 s. As libs CUDA instaladas por pip não estão no `LD_LIBRARY_PATH`; o script pré-carrega-as com `ctypes` e cai para CPU se a primeira computação falhar.

## Organização
- `scenes/`, `audio/` e `build/` são partilhadas: um segundo vídeo no mesmo repositório sobrescreve o anterior. Usar subpastas por projeto ou arquivar antes de começar.

## Reel com vídeo real
- Escolher stock a olhar, não pelo título: pedir ~24 resultados por termo, descarregar só as miniaturas, montar uma folha de contacto com `contact_sheet.py` e só então descarregar os eleitos.
- Recorte 9:16 por plano: cada fonte horizontal precisa do seu centro de recorte, escolhido em frames reais. 4K horizontal recorta sem perda; 1080p fica ampliado 1,78× e aguenta com `lanczos` + `unsharp=5:5:0.5`.
- `render_canvas.py --background video.mp4 --dim 0.55` compõe a cena (canvas transparente) sobre o vídeo; preparar à parte um MP4 de fundo por cena (planos cortados, recortados, mesma correção de cor) numa subpasta, para a montagem não o ler como cena.
- Zona segura de reel: título e etiquetas entre y≈1130 e y≈1480; nada importante acima de y=120 nem nos ~400 px de baixo, que a interface do Instagram tapa.
- Bandeiras, matrículas e letreiros denunciam o país da filmagem: escolher janelas de tempo sem eles ou tapá-los com um cartão de UI.
- Qualidade: `--crf 18` no render e `CRF=18` na montagem; com 23 as duas codificações seguidas notam-se em folhagem e multidões.
- Música mais curta que o vídeo: `atempo` (ex. 0,88) estica sem mudar o tom e mantém o final limpo.
- Versões lado a lado: `SCENES=scenes/v2 AUDIO=audio/v2` na montagem; `adelay` numa cópia da narração dá respiro antes da voz sem mexer no original.

## Efeitos sonoros
- Folha de deixas + `sfx_track.py`: cada som é normalizado ao pico pedido, o silêncio inicial é cortado (o ataque cai no tempo da deixa) e tudo é somado numa faixa WAV com a duração do vídeo; `SFX=` na montagem mistura-a por cima da voz e da música.
- Biblioteca local CC0 em `assets/sfx/` (sons base + Kenney Interface Sounds): produções novas não precisam de rede para os efeitos. Sons novos só via `stock.py --type audio`, preferindo CC0.
- Níveis de partida com a voz a −3 dB de pico: toque −14, whoosh −16, pops −20, ticks −25. Começar baixo; efeitos altos cansam.
- Séries (ícones a entrar, barras de gráfico) soam melhor com o mesmo som a subir de altura (`pitch` 1 → 1,12 → 1,26) ou alternando variações numeradas do pacote Kenney.
- O que leva som: entradas e saídas do objeto principal (whoosh, maximize/minimize), trocas de bloco (swish), toque em botão (click), confirmações (confirmation, glock), elementos em série (pops), texto a ser escrito (ticks), brilhos (shimmer ou glass, baixo). Texto que só aparece com fade não precisa de som.

## Mockups de dispositivos (devices.js, capture_site.py)
- Portátil e telemóvel são um modelo 3D mínimo projetado à mão (yaw/pitch/tilt/roll) e um ecrã deformado por uma malha de triângulos afins a partir de um canvas auxiliar com a página capturada; o Canvas 2D só faz transformações afins, mas com células pequenas (16×10 no portátil, 10×20 no telemóvel) o conjunto lê-se como perspetiva contínua.
- Cada triângulo tem de se sobrepor ~1 px ao vizinho e o ecrã tem de ser pintado antes com a cor de fundo da página, senão ficam costuras diagonais nas arestas da malha.
- `capture_site.py` tira a foto da página inteira (não só o que cabe na janela): recusa o aviso de cookies por um botão "Recusar"/"Rejeitar", rola a página devagar para as imagens lazy carregarem, volta ao topo e desliga animações antes da captura. 1280 px a 1,5× dá uma imagem de ~1920 px de largura para o portátil; 390 px a 2× com user agent de telemóvel dá ~780 px para o telemóvel.
- A captura mostra tudo o que o site tem, incluindo secções que o roteiro não deva exibir: escolher o intervalo de scroll (ou `--hide "seletor"`) em função disso, e só capturar sites com autorização.
- `Devices.placeholderPage()` desenha uma loja genérica para ensaiar e aprovar a animação antes de haver site ou autorização para o mostrar.

