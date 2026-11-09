#!/usr/bin/env python3
"""Reels mašina: kiekvienas hookas + kiekviena podložka = paruoštas 9:16 Reels.
Naudojimas:  python3 reels_masina.py <aplankas_su_video> <hookai.txt> [rezultatų_aplankas]
Reikia: ffmpeg ir Pillow (pip3 install pillow)."""
import sys, os, subprocess, shutil, html, glob
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
MAX_SEK = 12          # ilgiausias Reels
VIDEO = ('.mp4', '.mov', '.m4v', '.webm')
FOTO = ('.jpg', '.jpeg', '.png', '.heic', '.webp')
FONTAI = ['/System/Library/Fonts/Supplemental/Arial Bold.ttf', '/Library/Fonts/Arial Bold.ttf',
          'C:/Windows/Fonts/arialbd.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']

def sriftas(dydis):
    for f in FONTAI:
        if os.path.exists(f):
            return ImageFont.truetype(f, dydis)
    return ImageFont.load_default()

def teksto_png(tekstas, kelias):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img); f = sriftas(64)
    eil, cur = [], ''
    for z in tekstas.split():
        t = (cur + ' ' + z).strip()
        if d.textlength(t, font=f) > W * 0.8 and cur: eil.append(cur); cur = z
        else: cur = t
    if cur: eil.append(cur)
    y = int(H * 0.26) - 43
    for e in eil:
        w = d.textlength(e, font=f) + 44
        d.rounded_rectangle([(W - w) / 2, y, (W + w) / 2, y + 84], 18, fill='white')
        d.text((W / 2, y + 42), e, font=f, fill='#1d2733', anchor='mm'); y += 86
    img.save(kelias)

def kodekas():
    try:
        enc = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'], capture_output=True, text=True).stdout
        if 'h264_videotoolbox' in enc: return ['-c:v', 'h264_videotoolbox', '-b:v', '8M']  # Mac: greitas aparatinis
    except Exception: pass
    return ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20']
KODEKAS = kodekas()

def montuok(darbas):
    src, png, out = darbas
    foto = src.lower().endswith(FOTO)
    ivestis = ['-loop', '1', '-t', '7', '-i', src] if foto else ['-t', str(MAX_SEK), '-i', src]
    fit = f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=30'
    cmd = ['ffmpeg', '-v', 'error', '-y', *ivestis, '-i', png, '-filter_complex',
           f'[0:v]{fit}[b];[b][1:v]overlay=0:0,format=yuv420p[v]', '-map', '[v]', '-map', '0:a?',
           *KODEKAS, '-c:a', 'aac', '-shortest',
           '-movflags', '+faststart', out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return out, r.returncode == 0, r.stderr[-300:]

def main():
    if len(sys.argv) < 3: print(__doc__); sys.exit(1)
    if not shutil.which('ffmpeg'): sys.exit('Nerastas ffmpeg. Mac: brew install ffmpeg')
    aplankas, hook_failas = sys.argv[1], sys.argv[2]
    rez = sys.argv[3] if len(sys.argv) > 3 else 'Paruosti_Reels'
    os.makedirs(os.path.join(rez, '.tekstai'), exist_ok=True)
    kadrai = sorted(p for p in glob.glob(os.path.join(aplankas, '*')) if p.lower().endswith(VIDEO + FOTO))
    hookai = [h.strip() for h in open(hook_failas, encoding='utf-8') if h.strip()]
    if not kadrai or not hookai: sys.exit('Nėra kadrų arba hookų.')
    darbai, irasai = [], []
    for hi, h in enumerate(hookai):
        png = os.path.join(rez, '.tekstai', f'h{hi+1}.png'); teksto_png(h, png)
        for ki, k in enumerate(kadrai):
            out = os.path.join(rez, f'reels_h{hi+1:02d}_k{ki+1:02d}.mp4')
            darbai.append((k, png, out)); irasai.append((out, h))
    print(f'{len(hookai)} hookai × {len(kadrai)} kadrai = {len(darbai)} Reels')
    gerai = 0
    with ThreadPoolExecutor(max(2, (os.cpu_count() or 4) // 2)) as ex:
        for i, (out, ok, err) in enumerate(ex.map(montuok, darbai), 1):
            gerai += ok
            print(f'[{i}/{len(darbai)}] {"✓" if ok else "✗ " + err} {os.path.basename(out)}')
    plyteles = ''.join(f'<a href="{html.escape(os.path.basename(o))}" title="{html.escape(h)}"><video src="{html.escape(os.path.basename(o))}" muted loop autoplay playsinline preload="metadata"></video></a>' for o, h in irasai if os.path.exists(o))
    open(os.path.join(rez, 'galerija.html'), 'w', encoding='utf-8').write(
        f'<!DOCTYPE html><meta charset="utf-8"><title>Paruošti Reels</title><style>body{{font-family:sans-serif;background:#eef2f7;margin:24px}}'
        f'div{{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:10px}}video{{width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:12px;border:2px solid #fff;box-shadow:0 3px 10px #0002}}</style>'
        f'<h1>Paruošti Reels: {gerai}</h1><div>{plyteles}</div>')
    print(f'\nPadaryta: {gerai}/{len(darbai)}. Atidaryk {os.path.join(rez, "galerija.html")}')

if __name__ == '__main__': main()
