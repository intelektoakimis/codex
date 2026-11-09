"""Testai: python3 -m unittest discover -s tests -v"""
import os, sys, pathlib, json, re, shutil, subprocess, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import reels_masina as rm
from PIL import Image

SKRIPTAS = os.path.join(os.path.dirname(__file__), '..', 'reels_masina.py')


class Daugiskaita(unittest.TestCase):
    def test_formos(self):
        f = lambda n: rm.lt(n, 'hookas', 'hookai', 'hookų')
        for n, laukta in [(1, 'hookas'), (21, 'hookas'), (101, 'hookas'), (2, 'hookai'), (9, 'hookai'),
                          (22, 'hookai'), (0, 'hookų'), (10, 'hookų'), (11, 'hookų'),
                          (12, 'hookų'), (19, 'hookų'), (20, 'hookų'), (30, 'hookų'), (111, 'hookų'), (900, 'hookų')]:
            self.assertEqual(f(n), laukta, n)


class TekstoPng(unittest.TestCase):
    def setUp(self): self.d = tempfile.mkdtemp()
    def tearDown(self): shutil.rmtree(self.d)

    def ribos(self, tekstas):
        p = os.path.join(self.d, 'h.png'); rm.teksto_png(tekstas, p)
        im = Image.open(p); self.assertEqual(im.size, (rm.W, rm.H))
        return im.getchannel('A').getbbox()

    def test_trumpas_centruotas(self):
        x0, y0, x1, y1 = self.ribos('Štai kodėl')
        self.assertLess(abs((x0 + x1) / 2 - rm.W / 2), 3)

    def test_ilgas_zodis_neislenda(self):
        x0, _, x1, _ = self.ribos('Nebeprisiminkviskąkąžinaiapieturinįirkitusdalykus ilgas')
        self.assertGreater(x0, 0); self.assertLess(x1, rm.W)

    def test_labai_ilgas_hookas_telpa(self):
        x0, y0, x1, y1 = self.ribos(' '.join(['žodis'] * 80))
        self.assertGreater(x0, 0); self.assertLess(x1, rm.W); self.assertLess(y1, rm.H)

    def test_tuscias_neluzta(self):
        self.assertIsNone(self.ribos('   '))


class Galerija(unittest.TestCase):
    def test_pabegimas_ir_json(self):
        d = tempfile.mkdtemp()
        try:
            blogas = '"Kab" & <b>x</b> <!--<script> </script><script>alert(1)</script>'
            v = os.path.join(d, 'reels_h01_k01.mp4'); pathlib.Path(v).touch()
            kelias = rm.galerija(d, [blogas, 'Antras'], [(None, 'a.mov')], [(v, v + '.jpg', blogas)], 1)
            t = pathlib.Path(kelias).read_text(encoding='utf-8')
            self.assertNotIn('<script>alert', t); self.assertNotIn('<!--', t)
            self.assertEqual(t.count('</script>'), 1)               # tik mūsų pačių
            r = json.loads('[' + re.search(r'const R=\[(.*?)\];let', t, re.S).group(1) + ']')
            self.assertEqual(r, [['reels_h01_k01.mp4', blogas]])
            self.assertIn('2 hookai', t); self.assertIn('1 podložka', t); self.assertIn('2 reels', t)
            self.assertIn('NEUROSTART', t)
        finally: shutil.rmtree(d)

    def test_tuscia(self):
        d = tempfile.mkdtemp()
        try:
            t = pathlib.Path(rm.galerija(d, ['a'], [(None, 'x.mp4')], [], 0)).read_text(encoding='utf-8')
            self.assertIn('const R=[];', t); self.assertIn('Dar nėra paruoštų Reels', t)
        finally: shutil.rmtree(d)


@unittest.skipUnless(shutil.which('ffmpeg'), 'reikia ffmpeg')
class VisasPaleidimas(unittest.TestCase):
    def test_e2e(self):
        d = tempfile.mkdtemp()
        try:
            kad = os.path.join(d, 'kadrai'); os.makedirs(kad)
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=size=640x360:rate=30:duration=14',
                            '-f', 'lavfi', '-i', 'sine=duration=14', '-shortest', '-c:v', 'libx264', '-c:a', 'aac',
                            os.path.join(kad, 'a.mp4')], check=True)
            Image.new('RGB', (400, 300), 'red').save(os.path.join(kad, 'b.jpg'))
            pathlib.Path(kad, '._a.mp4').write_bytes(b'junk')          # macOS šiukšlė – praleisti
            pathlib.Path(kad, 'pastabos.txt').write_text('x')         # ne kadras
            hk = os.path.join(d, 'hookai.txt')
            pathlib.Path(hk).write_text('Pirmas hookas\n\n  Antras   hookas  \n', encoding='utf-8-sig')
            rez = os.path.join(d, 'rez')
            r = subprocess.run([sys.executable, SKRIPTAS, kad, hk, rez], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn('2 hookai × 2 kadrai = 4 Reels', r.stdout)
            for h in (1, 2):
                for k, trukme, garsas in ((1, 12.0, True), (2, 7.0, False)):
                    f = os.path.join(rez, f'reels_h{h:02d}_k{k:02d}.mp4')
                    p = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,width,height'
                                        ':format=duration', '-of', 'json', f], capture_output=True, text=True)
                    info = json.loads(p.stdout); tipai = [s['codec_type'] for s in info['streams']]
                    v = next(s for s in info['streams'] if s['codec_type'] == 'video')
                    self.assertEqual((v['width'], v['height']), (1080, 1920))
                    self.assertAlmostEqual(float(info['format']['duration']), trukme, delta=0.2)
                    self.assertEqual('audio' in tipai, garsas)
                    self.assertTrue(os.path.exists(os.path.join(rez, '.miniatiuros', f'reels_h{h:02d}_k{k:02d}.jpg')))
            t = pathlib.Path(rez, 'galerija.html').read_text(encoding='utf-8')
            self.assertIn('Antras hookas', t); self.assertNotIn('﻿', t)
            # sugadintas failas -> išėjimo kodas 1, sugadintas mp4 nepaliekamas
            pathlib.Path(kad, 'c.mp4').write_text('garbage')
            r = subprocess.run([sys.executable, SKRIPTAS, kad, hk, rez], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1); self.assertIn('Padaryta: 4/6', r.stdout)
            self.assertFalse(os.path.exists(os.path.join(rez, 'reels_h01_k03.mp4')))
        finally: shutil.rmtree(d)

    def test_blogi_argumentai(self):
        r = subprocess.run([sys.executable, SKRIPTAS], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1); self.assertIn('Naudojimas', r.stdout)
        r = subprocess.run([sys.executable, SKRIPTAS, '/nera/tokio', '/nera.txt'], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0); self.assertIn('Nerastas aplankas', r.stderr)


if __name__ == '__main__': unittest.main()
