# Estilos de animação Canvas

Três estilos que o Claude executa com qualidade em Canvas 2D, determinísticos (tudo deriva de `t`) e renderizáveis com `scripts/render_canvas.py`. Cada um tem uma cena-demonstração em `assets/estilo-*.html` (4 s, 1080x1920) que serve de **template de partida**: copiar para `scenes/NN.html` e adaptar texto, tempos e cores.

Apresentar os três ao utilizador na etapa 1 e pedir a escolha antes do roteiro. Não misturar estilos no mesmo vídeo, exceto o logo intro/outro, que pode ser neutro.

## Como escolher

| Estilo | Quando encaixa | Evitar quando |
|---|---|---|
| 1. Tipografia cinética | Há narração ou mensagem forte em poucas palavras; reels rápidos; anúncios; frases de impacto. | O conteúdo tem muita informação por cena, ou não há texto. |
| 2. Motion graphics geométrico | Explainers, "o que fazemos", listas, processos, dados simples; tom amigável e claro. | Se quer um ar dramático ou cinematográfico. |
| 3. Tech escuro com brilho | Software, produto digital, números e métricas, lançamentos; tom premium e tecnológico. | Marcas quentes/artesanais; público pouco técnico; texto longo (brilho cansa). |

## 1. Tipografia cinética — `assets/estilo-kinetic.html`

Palavras grandes que entram ao ritmo da fala. Uma ideia por "beat".

- **Paleta**: fundos sólidos que trocam por frase (escuro → amarelo → escuro → branco); texto na cor oposta. Nunca mais de 3 cores.
- **Tipografia**: Inter 900, `fitFont()` para encher 85–90% da largura; letras maiúsculas; uma linha por beat, no máximo três palavras empilhadas.
- **Vocabulário de movimento**: `slam` (escala 1,45→1 com overshoot `backOut`, rotação -0,12 rad a assentar), `wipe` (máscara `clip` da esquerda para a direita com linha de corte), `rise` (letras sobem uma a uma com stagger de 0,06 s e clip na linha de base), `stack` (palavras empilham com stagger 0,22 s, última a cores). Saída por queda com `easeIn`.
- **Tempos**: beats de 0,7–1,0 s; entradas 0,3–0,4 s; corte de fundo "arrastado" por uma barra em 0,18 s. Sincronizar cada beat com o `start` da palavra no JSON do `transcribe.py`.
- **Detalhes que fazem a diferença**: barra de acento amarela a entrar por baixo da palavra; barra de progresso de 10 px no rodapé; cortes secos, sem fades.
- **Erros comuns**: texto a tocar nas margens (deixar 60 px); mais de uma animação por beat; durações iguais em todos os beats (variar dá ritmo).

## 2. Motion graphics geométrico — `assets/estilo-geometrico.html`

Formas planas que se desenham e montam; explainer limpo.

- **Paleta**: fundo claro quente `#f7f5ef`, escuro `#1a1a1a`, amarelo `#ffbf00`, cartões brancos. Grelha de pontos a 8% de opacidade no fundo.
- **Tipografia**: Inter 800 para títulos (96 px), 700 para labels (60 px); minúsculas com inicial maiúscula.
- **Ícones**: Lucide via `Icons.draw` (ver SKILL.md) em tiles amarelos com `progress` a escrever o traço; é o ícone "a desenhar-se" que dá o ar de explainer. Pedir ícones ao `icons.py` em vez de os desenhar.
- **Vocabulário de movimento**: `strokeDraw()` (traço que se escreve com `setLineDash([per*p, per])`), preenchimento com `backOut` pequeno (s=1,2), cartões que deslizam de fora com sombra suave (`shadowBlur` 30), sublinhado que cresce do centro, um elemento em órbita lenta para a cena nunca ficar parada.
- **Tempos**: stagger 0,08–0,12 s entre elementos iguais; entradas 0,4–0,6 s com `easeOut`/`easeInOut`; cena montada em ~2,5 s e depois 1–2 s de repouso para leitura.
- **Motivo geométrico**: cluster de 7 hexágonos (raio 150, espaçamento 1,78·R) com ícone no centro; trocar pela forma que a marca usa (círculos, cartões, etc.).
- **Erros comuns**: `arc()` com raio negativo vindo do overshoot (envolver em `Math.max(0, …)`); demasiadas formas a mexer ao mesmo tempo; sombras fortes (ficam "Powerpoint").

## 3. Tech escuro com brilho — `assets/estilo-tech.html`

Fundo quase preto, grelha em perspetiva, partículas, linhas de luz e contadores.

- **Paleta**: fundo `#0b0e14`, amarelo `#ffbf00` como única cor de luz, branco `#f3f4f6` para números. Vinheta radial a 70%.
- **Tipografia**: Inter 900 para o número (260 px, `shadowBlur` 20–60 para brilho), 700 maiúsculas com tracking para labels (44 px), monoespaçada para "terminal".
- **Vocabulário de movimento**: grelha em perspetiva a deslizar (linhas horizontais em `pow(z, 2.2)`), 120 partículas a subir (posição por `hash(i)`, nunca `Math.random`), linhas luminosas que se desenham do centro (`glowLine`), contador que sobe com `easeOut` em 1,6 s e "assenta" com um pico de brilho, varrimento de luz diagonal em `lighter`, typewriter determinístico (`Math.floor(p * texto.length)`).
- **Tempos**: mais lento que os outros; entradas 0,6–1,0 s; cena a respirar continuamente (grelha e partículas nunca param).
- **Erros comuns**: `shadowBlur` em dezenas de elementos por frame (render lento; usar só em 2–3); brilho em texto pequeno (fica ilegível); fundo puro `#000` (perde profundidade).

## Regras comuns

- Guardar `WIDTH`, `HEIGHT`, `FPS`, `DURATION_S` e uma `renderFrame(t)` pura, como nas demos.
- Helpers de easing: `seg(t, t0, d)`, `easeOut`, `easeInOut`, `easeIn`, `backOut`. Copiar das demos.
- Rever sempre uma folha de contacto de 8 frames antes de aceitar a cena: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/contact_sheet.py scenes/NN.mp4`.
