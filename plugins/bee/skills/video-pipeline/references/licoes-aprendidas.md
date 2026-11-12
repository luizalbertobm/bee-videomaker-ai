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
- Três cenas (~450 frames) renderizam em paralelo em cerca de um minuto; lançar com `&` e `wait`. Folhas de contacto (PIL) são a forma mais barata de rever uma animação.

## Logos em SVG
- SVGs exportados sem IDs ainda têm cada peça num grupo de topo: dá para os dividir em camadas com o mesmo viewBox e animar cada uma (escala, rotação com pivô, alpha) sem redesenhar a marca. Classificar letras por serem `<g fill=…>` sem clip-path, não pela cor.

## Montagem
- Canvas renderiza para `scenes/NN.mp4`; `build/` é só intermediário. A montagem lê `scenes/NN.*` e `audio/NN.mp3`.
- `concat -c copy` falha a misturar cenas com e sem áudio: o script dá silêncio às cenas mudas e normaliza para AAC.
- Narração mais curta que a cena cortava o vídeo por `-shortest`; agora `-af apad`.
- Música de fundo: `musica.mp3` na raiz, volume `MUSIC_VOL`, ducking por `sidechaincompress`, mistura em estéreo.
- `LC_ALL=C` no script: com locale em vírgula decimal, `awk` escreve "18,38" e o ffmpeg lê dois filtros.

## Stock e ícones
- Pexels e Pixabay são os únicos bancos de vídeo gratuito com API; o Pexels deixou de emitir chaves novas em set. 2026, por isso o Pixabay é a fonte prática de vídeo. Openverse (imagens CC e sons do Freesound) não precisa de chave mas devolve 502/504 de vez em quando; fotos do Flickr vêm com 1024 px no máximo.
- Licenças CC BY-SA obrigam a publicar o vídeo com a mesma licença; preferir CC0 ou CC BY. Entregar sempre `creditos.md`.
- Ícones: Lucide (ISC) via `icons.py`; `qr-code` serve para Pix. Em ícones pequenos ao lado de texto bold, `lineWidth` 2,2–3.

## Transcrição local
- faster-whisper `large-v3` na GPU transcreve 7 s em ~1,4 s; `small` em CPU em ~3 s. As libs CUDA instaladas por pip não estão no `LD_LIBRARY_PATH`; o script pré-carrega-as com `ctypes` e cai para CPU se a primeira computação falhar.

## Organização
- `scenes/`, `audio/` e `build/` são partilhadas: um segundo vídeo no mesmo repositório sobrescreve o anterior. Usar subpastas por projeto ou arquivar antes de começar.
