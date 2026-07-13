#!/usr/bin/env python3
"""Çevrimdışı tek dosyalık sürümü üretir: pdf-donusturucu-tam.html

Tüm kütüphaneleri, OCR motorunu ve Türkçe/İngilizce dil verilerini tek
HTML dosyasına gömer. Çıktı dosyası internete hiç bağlanmadan, çift
tıklamayla tarayıcıda çalışır.

Kullanım: python3 cevrimdisi-derle.py
"""
import base64
import gzip
from pathlib import Path

KOK = Path(__file__).parent
LIB = KOK / "web" / "lib"

sablon = (KOK / "web" / "cevrimdisi-sablon.html").read_text(encoding="utf-8")

def oku(yol):
    return yol.read_text(encoding="utf-8")

son = sablon.replace("/*KUTUPHANELER*/", "\n;\n".join(
    oku(LIB / a) for a in ["pdf.min.js", "pdf.worker.min.js", "xlsx.full.min.js",
                           "docx.umd.js", "tesseract.min.js"]))
son = son.replace("/*ISCI*/", oku(LIB / "tesseract-worker.min.js"))
son = son.replace("/*CEKIRDEK_SIMD*/", oku(LIB / "core" / "tesseract-core-simd-lstm.wasm.js"))
son = son.replace("/*CEKIRDEK_DUZ*/", oku(LIB / "core" / "tesseract-core-lstm.wasm.js"))

for kod in ["tur", "eng"]:
    ham = gzip.decompress((KOK / "web" / "tessdata" / f"{kod}.traineddata.gz").read_bytes())
    son = son.replace(f"/*DIL_{kod.upper()}*/", base64.b64encode(ham).decode())

hedef = KOK / "pdf-donusturucu-tam.html"
hedef.write_text(son, encoding="utf-8")
print(f"Oluşturuldu: {hedef} ({len(son.encode())/1e6:.1f} MB)")
