#!/usr/bin/env python3
"""Captura uma página web inteira para usar no ecrã dos mockups de assets/devices.js (portátil ou telemóvel).
Abre o site no Chrome (Playwright), recusa o aviso de cookies, percorre a página para carregar as imagens lazy,
para as animações e grava um PNG alto com a largura que o ecrã do mockup espera.

Uso (a partir da raiz do projeto):
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/capture_site.py https://exemplo.com sources/site-desktop.png
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/capture_site.py https://exemplo.com sources/site-mobile.png --device mobile
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/videomaker/scripts/capture_site.py https://exemplo.com/produtos out.png --hide ".chat-widget,#popup" --max-height 5000

desktop: janela de 1280 px a 1,5x -> imagem com 1920 px de largura (Devices.laptop).
mobile:  janela de 390 px a 2x, com user agent e toque de telemóvel -> 780 px de largura (Devices.phone).
No fim imprime o tamanho da imagem e o scroll máximo a usar na cena. Capturar só sites do cliente ou com autorização:
a página aparece legível no vídeo.
"""
import argparse, pathlib, re, struct, sys
from playwright.sync_api import sync_playwright

MOBILE_UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) '
             'Version/17.5 Mobile/15E148 Safari/604.1')
# Botões de recusa de cookies (a opção que preserva a privacidade); só se nenhum existir é que o aviso se esconde por CSS
REJECT = re.compile(r'^\s*(recusar( tudo| todos)?|rejeitar( tudo| todos)?|negar|não aceito|nao aceito|apenas (os )?(necessários|essenciais)'
                    r'|só (os )?(necessários|essenciais)|continuar sem aceitar|reject( all)?|decline( all)?|deny( all)?'
                    r'|only (necessary|essential)( cookies)?|necessary only|rechazar( todo| todas)?)\s*$', re.I)
BANNERS = ('#onetrust-banner-sdk,#onetrust-consent-sdk,#CybotCookiebotDialog,.cc-window,.cookie-banner,.cookie-consent,'
           '.cookies-banner,[id*="cookie-banner" i],[class*="cookie-banner" i],[id*="cookieconsent" i],[class*="cookieconsent" i],'
           '[aria-label*="cookie" i][role="dialog"]')
SCREEN = {'desktop': (1520, 950, 74), 'mobile': (780, 1650, 124)}   # ecrã do mockup: largura, altura, barra (igual a devices.js)

ap = argparse.ArgumentParser(description='Captura de página inteira para os mockups de dispositivos.')
ap.add_argument('url'); ap.add_argument('out', help='ficheiro .png (ou .jpg)')
ap.add_argument('--device', choices=['desktop', 'mobile'], default='desktop')
ap.add_argument('--width', type=int, help='largura da janela em px CSS (1280 desktop, 390 mobile)')
ap.add_argument('--height', type=int, help='altura da janela em px CSS (800 desktop, 844 mobile)')
ap.add_argument('--scale', type=float, help='fator de resolução (1.5 desktop, 2 mobile)')
ap.add_argument('--max-height', type=int, default=6000, help='altura máxima a capturar, em px CSS (6000); 0 = página toda')
ap.add_argument('--locale', default='pt-BR')
ap.add_argument('--wait', type=float, default=1.0, help='segundos de espera extra depois de carregar (1.0)')
ap.add_argument('--hide', default='', help='seletores CSS a esconder, separados por vírgulas (chat, pop-ups)')
ap.add_argument('--click', action='append', default=[], help='seletor a clicar antes da captura (repetível), ex. fechar um modal')
ap.add_argument('--keep-cookie-banner', action='store_true', help='não mexer no aviso de cookies')
ap.add_argument('--timeout', type=float, default=45, help='segundos até desistir de carregar a página (45)')
a = ap.parse_args()

mobile = a.device == 'mobile'
vw, vh, scale = a.width or (390 if mobile else 1280), a.height or (844 if mobile else 800), a.scale or (2 if mobile else 1.5)
out = pathlib.Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
url = a.url if re.match(r'^[a-z]+://', a.url) else 'https://' + a.url

with sync_playwright() as p:
    try: browser = p.chromium.launch(channel='chrome')
    except Exception: browser = p.chromium.launch()      # sem Google Chrome: o Chromium do Playwright
    ctx = browser.new_context(viewport={'width': vw, 'height': vh}, device_scale_factor=scale, locale=a.locale,
                              is_mobile=mobile, has_touch=mobile, **({'user_agent': MOBILE_UA} if mobile else {}))
    page = ctx.new_page(); page.set_default_timeout(a.timeout * 1000)
    try: page.goto(url, wait_until='networkidle')
    except Exception as e:                                 # sites com pedidos em fundo nunca ficam "idle": seguir com o que carregou
        print(f'[aviso] a página não ficou em repouso ({type(e).__name__}); a continuar', file=sys.stderr)
        if page.url in ('about:blank', ''): sys.exit(f'[erro] não foi possível abrir {url}')
    page.wait_for_timeout(a.wait * 1000)

    cookies = 'sem aviso'
    if not a.keep_cookie_banner:
        for role in ('button', 'link'):
            loc = page.get_by_role(role, name=REJECT)
            if loc.count():
                try: loc.first.click(timeout=3000); cookies = 'recusado'; page.wait_for_timeout(600); break
                except Exception: pass
        if cookies == 'sem aviso' and page.locator(BANNERS).count(): cookies = 'escondido por CSS'
    for sel in a.click:
        try: page.locator(sel).first.click(timeout=3000); page.wait_for_timeout(500)
        except Exception as e: print(f'[aviso] --click {sel}: {type(e).__name__}', file=sys.stderr)

    # percorrer a página para as imagens lazy carregarem, voltar ao topo e parar animações
    total = page.evaluate('document.documentElement.scrollHeight')
    limit = min(total, a.max_height) if a.max_height else total
    y = 0
    while y < limit:
        page.evaluate('y => window.scrollTo(0, y)', y); page.wait_for_timeout(250); y += int(vh * 0.8)
    page.evaluate('window.scrollTo(0, 0)'); page.wait_for_timeout(400)
    hide = ','.join(s for s in ([] if a.keep_cookie_banner else [BANNERS]) + [a.hide] if s)
    page.add_style_tag(content='*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}'
                               'html::-webkit-scrollbar{display:none}' + (f'{hide}{{display:none!important}}' if hide else ''))
    try: page.wait_for_load_state('networkidle', timeout=8000)
    except Exception: pass
    total = page.evaluate('document.documentElement.scrollHeight'); h = min(total, a.max_height) if a.max_height else total
    kind = 'jpeg' if out.suffix.lower() in ('.jpg', '.jpeg') else 'png'
    page.screenshot(path=str(out), full_page=True, type=kind, clip={'x': 0, 'y': 0, 'width': vw, 'height': h},
                    **({'quality': 92} if kind == 'jpeg' else {}))
    browser.close()

pw, ph = round(vw * scale), round(h * scale)
if kind == 'png':                                          # tamanho real, lido do cabeçalho do PNG
    with open(out, 'rb') as f: pw, ph = struct.unpack('>II', f.read(24)[16:24])
sw, sh, bar = SCREEN[a.device]
maxs = max(0, round(ph - (sh - bar) * pw / sw))
print(f'{out}: {pw}x{ph} px ({a.device}, janela {vw}x{vh} a {scale:g}x), cookies: {cookies}'
      + (f', cortada aos {a.max_height} px de {total}' if h < total else ''))
print(f"cena: Devices.{'phone' if mobile else 'laptop'}(ctx, img, pose, {{ scroll }}) com scroll de 0 a {maxs} px"
      + (' (a página cabe inteira no ecrã)' if maxs == 0 else ''))
