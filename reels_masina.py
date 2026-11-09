#!/usr/bin/env python3
"""NEUROSTART Reels kūrimo mašina: kiekvienas hookas + kiekviena podložka = paruoštas 9:16 Reels.
Naudojimas:  python3 reels_masina.py <aplankas_su_video> <hookai.txt> [rezultatų_aplankas]
Reikia: ffmpeg ir Pillow (pip3 install pillow).
Rezultatų aplanke atsiranda galerija.html: hookai, podložkos ir visi paruošti Reels."""
import sys, os, subprocess, shutil, html, json
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
MAX_SEK = 12          # ilgiausias Reels
FOTO_SEK = 7          # kiek sekundžių rodoma nuotrauka
VIDEO = ('.mp4', '.mov', '.m4v', '.webm')
FOTO = ('.jpg', '.jpeg', '.png', '.heic', '.webp')
FONTAI = ['/System/Library/Fonts/Supplemental/Arial Bold.ttf', '/Library/Fonts/Arial Bold.ttf',
          'C:/Windows/Fonts/arialbd.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']
SRIFTO_DYDIS, MIN_DYDIS, MAX_EILUCIU = 64, 36, 5
KAPOJIMO_DYDIS = 48   # žemiau šito šrifto nemažinam vien tam, kad nekapotume per ilgo žodžio


def sriftas(dydis):
    for f in FONTAI:
        if os.path.exists(f):
            return ImageFont.truetype(f, dydis)
    try:
        return ImageFont.load_default(dydis)      # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()


def laužyk(d, tekstas, f, plotis):
    """Skaido tekstą į eilutes; per ilgą žodį kapoja per raides."""
    eil, cur = [], ''
    for z in tekstas.split():
        while d.textlength(z, font=f) > plotis and len(z) > 1:   # žodis netelpa net vienas
            if cur: eil.append(cur); cur = ''
            i = len(z) - 1
            while i > 1 and d.textlength(z[:i] + '-', font=f) > plotis: i -= 1
            eil.append(z[:i] + '-'); z = z[i:]
        t = (cur + ' ' + z).strip()
        if d.textlength(t, font=f) > plotis and cur: eil.append(cur); cur = z
        else: cur = t
    if cur: eil.append(cur)
    return eil


def teksto_png(tekstas, kelias):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    dydis = SRIFTO_DYDIS
    while True:   # mažinam šriftą, kol tilps (žodžiai nekapojami, jei įmanoma)
        f = sriftas(dydis)
        eil = laužyk(d, tekstas, f, W * 0.8)
        kapota = any(e.endswith('-') for e in eil) and not any(z.endswith('-') for z in tekstas.split())
        if dydis <= MIN_DYDIS or (len(eil) <= MAX_EILUCIU and (not kapota or dydis <= KAPOJIMO_DYDIS)): break
        dydis -= 4
    aukstis, tarpas = round(dydis * 1.31), round(dydis * 1.34)
    y = int(H * 0.26) - aukstis // 2
    for e in eil:
        w = d.textlength(e, font=f) + round(dydis * 0.69)
        d.rounded_rectangle([(W - w) / 2, y, (W + w) / 2, y + aukstis], round(dydis * 0.28), fill='white')
        d.text((W / 2, y + aukstis / 2), e, font=f, fill='#1d2733', anchor='mm'); y += tarpas
    img.save(kelias)


def kodekas():
    try:
        enc = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'], capture_output=True, text=True).stdout
        if 'h264_videotoolbox' in enc: return ['-c:v', 'h264_videotoolbox', '-b:v', '8M']  # Mac: greitas aparatinis
    except Exception: pass
    return ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20']
KODEKAS = kodekas()


def kadras_jpg(src, out, plotis, sek=1.0):
    """Vienas kadras miniatiūrai. Jei video trumpesnis už `sek`, imamas pirmas kadras."""
    for ss in ([] if src.lower().endswith(FOTO) else ['-ss', str(sek)]), []:
        r = subprocess.run(['ffmpeg', '-v', 'error', '-y', *ss, '-i', src, '-frames:v', '1',
                            '-vf', f'scale={plotis}:-2', '-q:v', '4', out], capture_output=True)
        if r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0: return True
    return False


def heic_i_jpg(src, out):
    """iPhone HEIC dažnai neatsidaro senesniu ffmpeg – bandom konvertuoti."""
    if shutil.which('sips'):   # macOS
        r = subprocess.run(['sips', '-s', 'format', 'jpeg', src, '--out', out], capture_output=True)
        if r.returncode == 0 and os.path.exists(out): return out
    try:
        import pillow_heif; pillow_heif.register_heif_opener()
        from PIL import ImageOps
        ImageOps.exif_transpose(Image.open(src)).convert('RGB').save(out, quality=95)
        return out
    except Exception:
        return src   # paliekam ffmpeg'ui


def montuok(darbas):
    src, png, out, poster = darbas
    foto = src.lower().endswith(FOTO)
    ivestis = ['-loop', '1', '-t', str(FOTO_SEK), '-i', src] if foto else ['-t', str(MAX_SEK), '-i', src]
    fit = f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=30'
    cmd = ['ffmpeg', '-v', 'error', '-y', *ivestis, '-i', png, '-filter_complex',
           f'[0:v]{fit}[b];[b][1:v]overlay=0:0,format=yuv420p[v]', '-map', '[v]', '-map', '0:a?',
           *KODEKAS, '-c:a', 'aac', '-shortest',
           '-movflags', '+faststart', out]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        return out, False, str(e)
    ok = r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 0
    if ok: kadras_jpg(out, poster, 216, 0.5)
    elif os.path.exists(out): os.remove(out)   # neliekam sugadinto failo
    return out, ok, r.stderr.strip()[-300:]


def lt(n, vns, dgs, kilm):
    """Lietuviška daugiskaita: 1 hookas, 2 hookai, 10 hookų, 21 hookas."""
    if n % 10 == 1 and n % 100 != 11: return vns
    if 2 <= n % 10 <= 9 and not 11 <= n % 100 <= 19: return dgs
    return kilm


def galerija(rez, hookai, podlozkos, irasai, gerai):
    """podlozkos: [(miniatiūra|None, failo vardas)], irasai: [(video, poster, hookas)] tik sėkmingi."""
    e = lambda s: html.escape(s, quote=True)
    rel = lambda p: e(os.path.relpath(p, rez).replace(os.sep, '/'))
    viso_h, viso_k = len(hookai), len(podlozkos)
    hook_li = ''.join(f'<li><span>↗</span>{e(h)}</li>' for h in hookai)
    skraidantys = ''.join(f'<i class="chip c{i}">↗ {e(h)}</i>' for i, h in enumerate(hookai[:5]))
    stulpeliai = [[] for _ in range(5)]
    for i, (m, vardas) in enumerate(podlozkos):
        stulpeliai[i % 5].append(f'<img src="{rel(m)}" alt="{e(vardas)}" title="{e(vardas)}" loading="lazy">' if m
                                 else f'<b title="{e(vardas)}">{e(os.path.splitext(vardas)[1][1:].upper())}</b>')
    podl = ''.join(f'<div class="col">{"".join(s)}</div>' for s in stulpeliai if s)
    plyteles = ''.join(
        f'<a href="{rel(v)}" data-i="{i}" title="{e(h)}"><img src="{rel(p)}" alt="{e(h)}" loading="lazy"></a>'
        if os.path.exists(p) else f'<a href="{rel(v)}" data-i="{i}" title="{e(h)}"><span>{e(h)}</span></a>'
        for i, (v, p, h) in enumerate(irasai))
    sarasas = json.dumps([[os.path.relpath(v, rez).replace(os.sep, '/'), h] for v, _, h in irasai],
                         ensure_ascii=False).replace('<', '\\u003c')[1:-1]   # jokio '<' <script> viduje
    proc = round(100 * gerai / max(1, viso_h * viso_k))
    turinys = GALERIJA.format(
        hook_n=viso_h, hook_z=lt(viso_h, 'hookas', 'hookai', 'hookų'), hook_li=hook_li, skraidantys=skraidantys,
        kad_n=viso_k, kad_z=lt(viso_k, 'podložka', 'podložkos', 'podložkų'), podl=podl,
        sand=viso_h * viso_k, gerai=gerai, proc=proc, plyteles=plyteles or '<p class="tuscia">Dar nėra paruoštų Reels</p>',
        sarasas=sarasas, paruost=lt(gerai, 'paruoštas', 'paruošti', 'paruoštų'))
    kelias = os.path.join(rez, 'galerija.html')
    with open(kelias, 'w', encoding='utf-8') as f: f.write(turinys)
    return kelias


GALERIJA = r'''<!DOCTYPE html>
<html lang="lt"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEUROSTART Reels kūrimo mašina</title>
<style>
:root{{--bg:#eef3f8;--kortele:rgba(255,255,255,.72);--tekstas:#1d2733;--blankus:#8a9bb0;--akcentas:#4f7ea8;
--zenkl:#dfe9f3;--tamsi:#2c3a49;--seselis:0 10px 40px rgba(60,90,130,.10)}}
*{{box-sizing:border-box}}
body{{margin:0;background:radial-gradient(ellipse at 50% 40%,#f7fafd 0,var(--bg) 70%);color:var(--tekstas);
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Arial,sans-serif;min-height:100vh}}
.scena{{max-width:1500px;margin:0 auto;padding:40px 28px 24px;display:grid;
grid-template-columns:minmax(0,1fr) minmax(0,.95fr) minmax(0,1.2fr);gap:32px;align-items:start}}
.kortele{{min-width:0;background:var(--kortele);border:1px solid #fff;border-radius:28px;box-shadow:var(--seselis);padding:26px 26px 22px;
backdrop-filter:blur(8px);position:relative}}
.kortele h2{{margin:0;font-size:21px;font-weight:650;display:flex;justify-content:space-between;align-items:center}}
.zenklas{{background:var(--zenkl);color:var(--akcentas);font-size:16px;font-weight:600;border-radius:999px;padding:4px 13px}}
.pozymis{{margin:8px 0 18px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--blankus)}}
.kaire{{display:grid;gap:30px}}
.hookai ul{{list-style:none;margin:0;padding:0;columns:2;column-gap:14px;max-height:280px;overflow:auto;
mask-image:linear-gradient(#000 75%,transparent)}}
.hookai li{{break-inside:avoid;font-size:13.5px;color:#7d8da0;padding:3px 0 3px 18px;position:relative;line-height:1.35;overflow-wrap:anywhere}}
.hookai li span{{position:absolute;left:0;color:#a9b8c8}}
.chip{{position:absolute;font-style:normal;font-size:12px;background:#fff;border-radius:10px;padding:6px 10px;
box-shadow:0 6px 18px rgba(60,90,130,.15);max-width:170px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
animation:skrenda 6s ease-in-out infinite;pointer-events:none;z-index:2}}
.c0{{top:150px;left:42%;animation-delay:0s}}.c1{{top:210px;left:8%;animation-delay:1.2s}}.c2{{top:250px;left:62%;animation-delay:2.4s}}
.c3{{top:300px;left:30%;animation-delay:3.6s}}.c4{{top:120px;left:70%;animation-delay:4.8s}}
@keyframes skrenda{{0%{{opacity:0;transform:translate(0,6px)}}15%{{opacity:1;transform:translate(0,0)}}
70%{{opacity:1}}100%{{opacity:0;transform:translate(120px,-6px) scale(.85)}}}}
.podl{{display:flex;gap:14px;justify-content:space-around;max-height:310px;overflow:hidden;padding-bottom:6px}}
.col{{flex:0 1 72px;min-width:0;display:flex;flex-direction:column}}.col:nth-child(2n){{margin-top:18px}}.col:nth-child(3n){{margin-top:-4px}}
.col img,.col b{{width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:10px;border:2px solid #fff;
box-shadow:0 4px 12px rgba(30,50,80,.18);margin-bottom:-38%;background:#cfdbe7;display:grid;place-items:center;
font-size:11px;color:#fff;transition:transform .25s}}
.col img:hover{{transform:translateY(-8px) rotate(-2deg);position:relative;z-index:3}}
.centras{{display:flex;flex-direction:column;align-items:center;padding-top:150px}}
.masina{{position:relative;width:min(440px,100%);background:rgba(255,255,255,.8);border:1px solid #fff;border-radius:34px;
padding:20px;box-shadow:0 20px 60px rgba(60,90,130,.16)}}
.masina::before,.masina::after{{content:"";position:absolute;top:50%;width:34px;height:84px;margin-top:-30px;
background:var(--tamsi);border:7px solid #fff;border-radius:16px;box-shadow:var(--seselis)}}
.masina::before{{left:-26px}}.masina::after{{right:-26px}}
.busena{{background:#dfe9f3;border-radius:18px;padding:20px 26px;display:flex;align-items:center;gap:14px;
font-size:15px;font-weight:650;letter-spacing:.06em;color:var(--akcentas)}}
.busena i{{width:10px;height:10px;border-radius:50%;background:var(--akcentas);animation:pulsas 1.4s infinite}}
.busena em{{margin-left:auto;font-style:normal;font-size:22px;animation:sukasi 6s linear infinite}}
@keyframes pulsas{{50%{{opacity:.3}}}}@keyframes sukasi{{to{{transform:rotate(360deg)}}}}
.ekranas{{margin:22px 4px 0;background:var(--tamsi);color:#fff;border-radius:20px;padding:28px 28px 24px;position:relative}}
.ekranas h1{{margin:0;padding-right:64px;font-size:31px;line-height:1.12;font-weight:800;letter-spacing:.01em}}
.ekranas p{{margin:18px 0 0;color:#c7d3df;font-size:16px}}
.eq{{position:absolute;right:28px;bottom:42px;display:flex;align-items:flex-end;gap:5px;height:62px}}
.eq s{{width:5px;background:#fff;border-radius:3px;animation:eq 1.1s ease-in-out infinite alternate}}
@keyframes eq{{from{{height:20%}}to{{height:100%}}}}
.eiga{{display:flex;align-items:center;gap:22px;margin:24px 10px 6px}}
.juosta{{flex:1;height:14px;background:#e4ecf3;border-radius:9px;overflow:hidden}}
.juosta div{{height:100%;width:{proc}%;background:var(--akcentas);border-radius:9px;animation:pildo 2s ease-out}}
@keyframes pildo{{from{{width:0}}}}
.play{{width:40px;height:40px;border-radius:50%;background:#cfdeec;border:0;color:var(--akcentas);font-size:14px;cursor:pointer}}
.srautas{{margin-top:50px;text-align:center}}
.srautas b{{display:block;font-size:20px;font-weight:500;color:var(--akcentas)}}
.srautas span{{display:block;margin-top:14px;font-size:14px;color:var(--blankus)}}
.tinklelis{{display:grid;grid-template-columns:repeat(auto-fill,minmax(48px,1fr));gap:6px;max-height:640px;overflow:auto;padding:4px}}
.tinklelis a{{display:block;aspect-ratio:9/16;border-radius:5px;overflow:hidden;border:1.5px solid #fff;
box-shadow:0 2px 6px rgba(30,50,80,.2);background:#cfdbe7;transition:transform .15s;position:relative}}
.tinklelis a:hover{{transform:scale(1.12);z-index:2}}
.tinklelis img{{width:100%;height:100%;object-fit:cover;display:block}}
.tinklelis span{{font-size:8px;padding:3px;display:block;color:var(--tekstas)}}
.tuscia{{color:var(--blankus)}}
.pastaba{{margin:16px 0 0;font-size:14px;color:var(--blankus)}}
.apacia{{max-width:1500px;margin:0 auto;padding:10px 28px 40px;display:flex;justify-content:space-between;align-items:center;
flex-wrap:wrap;gap:16px;font-size:23px}}
.lygtis{{display:flex;gap:26px;align-items:baseline}}.lygtis .op{{color:var(--akcentas)}}.lygtis .ats{{color:var(--akcentas);font-weight:600}}
.siukis{{color:var(--blankus);font-size:18px}}
.didelis{{text-align:center;display:flex;justify-content:center;align-items:center;gap:14px;padding-bottom:40px}}
.didelis b{{font-size:64px;color:var(--tamsi);font-weight:800;line-height:1}}.didelis span{{text-align:left;color:var(--blankus);font-size:14px}}
dialog{{border:0;border-radius:24px;padding:16px;background:#fff;box-shadow:0 30px 80px rgba(0,0,0,.35);max-width:96vw}}
dialog::backdrop{{background:rgba(29,39,51,.6)}}
dialog video{{display:block;height:min(78vh,720px);aspect-ratio:9/16;border-radius:14px;background:#000}}
.ln{{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:12px;font-size:14px}}
.ln button,.ln a{{border:0;background:var(--zenkl);color:var(--akcentas);border-radius:10px;padding:8px 12px;font:inherit;cursor:pointer;text-decoration:none}}
.ln p{{margin:0;flex:1;max-width:280px;color:var(--tekstas);overflow-wrap:anywhere}}
@media (max-width:1100px){{.scena{{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}}.desine{{grid-column:1/-1}}.centras{{padding-top:40px}}}}
@media (max-width:720px){{.scena{{grid-template-columns:minmax(0,1fr);padding:20px 16px}}.chip{{display:none}}.centras{{padding-top:10px}}
.masina::before,.masina::after{{display:none}}.ekranas h1{{font-size:28px}}.apacia{{font-size:18px;padding:10px 16px 24px}}.lygtis{{gap:12px}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style></head><body>
<main class="scena">
 <div class="kaire">
  <section class="kortele hookai"><h2>Hookai <span class="zenklas">{hook_n}</span></h2>
   <p class="pozymis">Tekstai, kurie kabina</p><ul>{hook_li}</ul>{skraidantys}</section>
  <section class="kortele"><h2>Podložkos <span class="zenklas">{kad_n}</span></h2>
   <p class="pozymis">Trumpi video / kadrai iš gyvenimo</p><div class="podl">{podl}</div></section>
 </div>
 <div class="centras">
  <div class="masina">
   <div class="busena"><i></i>MONTUOJU REELS<em>✳</em></div>
   <div class="ekranas"><h1>NEUROSTART<br>REELS KŪRIMO<br>MAŠINA</h1><p>{gerai} iš {sand} · {proc}%</p>
    <div class="eq"><s style="animation-delay:-.1s"></s><s style="animation-delay:-.5s"></s><s style="animation-delay:-.3s"></s>
    <s style="animation-delay:-.8s"></s><s style="animation-delay:-.2s"></s><s style="animation-delay:-.6s"></s><s style="animation-delay:-.4s"></s></div></div>
   <div class="eiga"><div class="juosta"><div></div></div><button class="play" id="groti" aria-label="Peržiūrėti">▶</button></div>
  </div>
  <div class="srautas"><b>Turinys sraute</b><span>hookas + podložka + tavo pateikimas</span></div>
 </div>
 <section class="kortele desine"><h2>Paruošti Reels <span class="zenklas">{gerai}</span></h2>
  <p class="pozymis">Spausk ant Reels – peržiūra ir atsisiuntimas</p>
  <div class="tinklelis" id="tinklelis">{plyteles}</div>
  <p class="pastaba">Kiekvienas hookas susitinka su kiekviena podložka</p></section>
</main>
<footer class="apacia"><div class="lygtis"><span>{hook_n} {hook_z}</span><span class="op">×</span><span>{kad_n} {kad_z}</span>
 <span class="op">=</span><span class="ats">{sand} reels</span></div><div class="siukis">Mažiau rutinos. Daugiau turinio.</div></footer>
<div class="didelis"><b>{gerai}</b><span>{paruost} reels<br>iš tavo hookų ir podložkų</span></div>
<dialog id="langas"><video id="vid" controls autoplay playsinline></video>
 <div class="ln"><button id="atgal" aria-label="Ankstesnis">←</button><p id="hk"></p>
 <a id="parsisiusti" download>Atsisiųsti</a><button id="pirmyn" aria-label="Kitas">→</button><button id="uzd" aria-label="Uždaryti">✕</button></div></dialog>
<script>
const R=[{sarasas}];let dab=0;const L=document.getElementById('langas'),V=document.getElementById('vid');
function rodyk(i){{if(!R.length)return;dab=(i+R.length)%R.length;V.src=R[dab][0];document.getElementById('hk').textContent=R[dab][1];
document.getElementById('parsisiusti').href=R[dab][0];if(!L.open)L.showModal();}}
document.getElementById('tinklelis').addEventListener('click',e=>{{const a=e.target.closest('a');if(!a)return;e.preventDefault();rodyk(+a.dataset.i);}});
document.getElementById('groti').onclick=()=>rodyk(0);
document.getElementById('atgal').onclick=()=>rodyk(dab-1);document.getElementById('pirmyn').onclick=()=>rodyk(dab+1);
document.getElementById('uzd').onclick=()=>L.close();L.addEventListener('close',()=>{{V.pause();V.removeAttribute('src');V.load();}});
L.addEventListener('click',e=>{{if(e.target===L)L.close();}});
document.addEventListener('keydown',e=>{{if(!L.open)return;if(e.key==='ArrowLeft')rodyk(dab-1);if(e.key==='ArrowRight')rodyk(dab+1);}});
</script></body></html>'''


def main():
    if len(sys.argv) < 3: print(__doc__); sys.exit(1)
    if not shutil.which('ffmpeg'): sys.exit('Nerastas ffmpeg. Mac: brew install ffmpeg')
    aplankas, hook_failas = sys.argv[1], sys.argv[2]
    rez = sys.argv[3] if len(sys.argv) > 3 else 'Paruosti_Reels'
    if not os.path.isdir(aplankas): sys.exit(f'Nerastas aplankas: {aplankas}')
    if not os.path.isfile(hook_failas): sys.exit(f'Nerastas hookų failas: {hook_failas}')
    for d in ('.tekstai', '.miniatiuros', '.kadrai'): os.makedirs(os.path.join(rez, d), exist_ok=True)
    rez_abs = os.path.abspath(rez)
    kadrai = sorted(os.path.join(aplankas, p) for p in os.listdir(aplankas)
                    if not p.startswith('.') and p.lower().endswith(VIDEO + FOTO)
                    and os.path.isfile(os.path.join(aplankas, p))
                    and not os.path.abspath(os.path.join(aplankas, p)).startswith(rez_abs + os.sep))
    with open(hook_failas, encoding='utf-8-sig') as f:    # -sig: nuima Windows/Notepad BOM
        hookai = [' '.join(h.split()) for h in f if h.strip()]
    if not kadrai or not hookai: sys.exit('Nėra kadrų arba hookų.')

    podlozkos, saltiniai = [], []
    for ki, k in enumerate(kadrai):
        if k.lower().endswith('.heic'): k = heic_i_jpg(k, os.path.join(rez, '.kadrai', f'k{ki+1:02d}.jpg'))
        saltiniai.append(k)
        m = os.path.join(rez, '.miniatiuros', f'k{ki+1:02d}.jpg')
        podlozkos.append((m if kadras_jpg(k, m, 160) else None, os.path.basename(kadrai[ki])))

    darbai, irasai = [], []
    for hi, h in enumerate(hookai):
        png = os.path.join(rez, '.tekstai', f'h{hi+1}.png'); teksto_png(h, png)
        for ki, k in enumerate(saltiniai):
            vardas = f'reels_h{hi+1:02d}_k{ki+1:02d}'
            out = os.path.join(rez, vardas + '.mp4')
            poster = os.path.join(rez, '.miniatiuros', vardas + '.jpg')
            darbai.append((k, png, out, poster)); irasai.append((out, poster, h))
    print('NEUROSTART REELS KŪRIMO MAŠINA')
    print(f'{len(hookai)} {lt(len(hookai), "hookas", "hookai", "hookų")} × {len(kadrai)} '
          f'{lt(len(kadrai), "kadras", "kadrai", "kadrų")} = {len(darbai)} Reels')
    gerai, sekmingi = 0, []
    with ThreadPoolExecutor(max(2, (os.cpu_count() or 4) // 2)) as ex:
        for i, ((out, ok, err), irasas) in enumerate(zip(ex.map(montuok, darbai), irasai), 1):
            gerai += ok
            if ok: sekmingi.append(irasas)
            print(f'[{i}/{len(darbai)}] {"✓" if ok else "✗"} {os.path.basename(out)}{"" if ok else "  " + err}')
    kelias = galerija(rez, hookai, podlozkos, sekmingi, gerai)
    print(f'\nPadaryta: {gerai}/{len(darbai)}. Atidaryk {kelias}')
    if gerai < len(darbai): sys.exit(1)


if __name__ == '__main__': main()
