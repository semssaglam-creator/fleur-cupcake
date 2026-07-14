#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mevzuat Asistanı — Çevrimdışı Vergi Mevzuatı Arama ve Uyum Kontrol Aracı
=========================================================================

Gelir uzmanları için: `mevzuat/` klasörüne atılan kanun, yönerge, tebliğ,
sirküler ve özelge dosyalarını (PDF, Word .docx, .txt) madde madde
indeksler; konu araması yapar, kısa özet ve otomatik yorum üretir,
tıklandığında ilgili mevzuat metnini gösterir.

Tamamen çevrimdışı çalışır — hiçbir veri bilgisayar dışına çıkmaz.

Kullanım:
    python3 mevzuat_asistani.py            # sunucuyu başlatır, tarayıcıyı açar
    python3 mevzuat_asistani.py --port 8765
    python3 mevzuat_asistani.py --no-browser

PDF okumak için sırasıyla şunlar denenir:
    1) pypdf Python paketi (varsa)
    2) pdftotext komutu (poppler-utils paketi, çoğu Linux'ta mevcut)
İkisi de yoksa PDF dosyaları atlanır ve arayüzde uyarı gösterilir.
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import unicodedata
import urllib.parse
import webbrowser
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from xml.etree import ElementTree

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEVZUAT_DIR = os.path.join(BASE_DIR, "mevzuat")
SUPPORTED_EXTS = (".pdf", ".docx", ".txt", ".md")

# ---------------------------------------------------------------------------
# Türkçe metin yardımcıları
# ---------------------------------------------------------------------------

_TR_LOWER = str.maketrans({"İ": "i", "I": "ı"})


def tr_lower(text: str) -> str:
    """Türkçe kurallarına göre küçük harfe çevirir (İ→i, I→ı)."""
    return text.translate(_TR_LOWER).lower()


def tr_fold(text: str) -> str:
    """Arama eşleştirmesi için aksansız/katlanmış biçim üretir.

    Hem 'istisna' hem 'İSTİSNA' hem de yanlış yazılmış 'istısna' gibi
    biçimlerin birbirini bulabilmesi için ı/i, ş/s, ğ/g, ü/u, ö/o, ç/c
    tek biçime indirgenir.
    """
    text = tr_lower(text)
    table = str.maketrans({"ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c"})
    text = text.translate(table)
    # kalan aksanları da temizle
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


_WORD_RE = re.compile(r"[a-zA-ZçÇğĞıİöÖşŞüÜâîûÂÎÛ0-9]+")

# Aramada gözardı edilecek yaygın kelimeler
_STOPWORDS = {tr_fold(w) for w in (
    "ve", "veya", "ile", "bir", "bu", "şu", "o", "için", "gibi", "kadar",
    "göre", "olan", "olarak", "her", "daha", "ise", "de", "da", "ki", "mi",
    "ne", "hangi", "nasıl", "olduğu", "üzere", "ait", "dair", "ilişkin",
)}


def tokenize(text: str):
    return [tr_fold(m.group(0)) for m in _WORD_RE.finditer(text)]


def query_terms(query: str):
    """Sorgudan anlamlı arama kökleri çıkarır."""
    terms = []
    for tok in tokenize(query):
        if len(tok) < 2 or tok in _STOPWORDS:
            continue
        # basit gövdeleme: uzun kelimelerin çekim eklerini yaklaşıkla —
        # ilk 5+ karakter kök kabul edilir (ör. "istisnası" → "istis...")
        terms.append(tok)
    return terms


def term_matches(term: str, token: str) -> bool:
    """Bir arama kökü belge kelimesiyle eşleşiyor mu?

    Kısa terimlerde tam eşleşme, 4+ karakterde önek eşleşmesi aranır ki
    'istisna' terimi 'istisnasından' kelimesini de bulsun.
    """
    if token == term:
        return True
    if len(term) >= 4 and token.startswith(term):
        return True
    if len(token) >= 4 and term.startswith(token) and len(term) - len(token) <= 3:
        return True
    return False


# ---------------------------------------------------------------------------
# Metin kalitesi ölçümü (taranmış / bozuk kodlamalı PDF tespiti)
# ---------------------------------------------------------------------------

_VOWELS = set("aeıioöuüAEIİOÖUÜâîûÂÎÛ")
# Düzgün çıkarılmış Türkçe mevzuat metni ~0.92+ puan alır; bozuk OCR/kodlama
# çıktısı ~0.77 ve altında kalır. 0.85 ikisini güvenle ayırır.
QUALITY_THRESHOLD = 0.85
QUALITY_SEVERE = 0.75

OCR_ADVICE = (
    "Bu dosyadan sağlıklı metin çıkarılamadı — taranmış (görüntü) veya bozuk "
    "yazı kodlamalı PDF olabilir. Çözüm: dosyayı OCR'dan geçirin: "
    "sudo apt install ocrmypdf tesseract-ocr-tur ; "
    "ocrmypdf -l tur --force-ocr girdi.pdf cikti.pdf — sonra cikti.pdf'i "
    "mevzuat klasörüne koyun. Mümkünse belgenin metin tabanlı resmî "
    "sürümünü (mevzuat.gov.tr / GİB) tercih edin."
)


_CONSONANT_RUN_RE = re.compile(r"[bcçdfgğhjklmnprsştvyzBCÇDFGĞHJKLMNPRSŞTVYZ]{4,}")
_MIXED_CASE_RE = re.compile(r"[a-zçğıöşü][A-ZÇĞİÖŞÜ]")


def _word_is_suspicious(core: str) -> bool:
    """Bir kelime OCR/kodlama bozulması izi taşıyor mu?

    Türkçe'de q/w/x bulunmaz; 4+ ardışık sessiz harf ('htrP', 'tlrrt'),
    kelime içinde küçük→BÜYÜK geçişi ('I-leeapUzman') ve harf-rakam-simge
    karışımı ('q\"galilu_.r') düzgün metinde görülmez.
    """
    if core.isdigit():
        return False
    if core.isupper() and len(core) <= 6:  # KDV, GVK, TBMM gibi kısaltmalar
        return False
    if not core.isalpha():
        return True
    folded = tr_fold(core)
    if any(c in folded for c in "qwx"):
        return True
    if not any(c in _VOWELS for c in core):
        return True
    if _MIXED_CASE_RE.search(core):
        return True
    if _CONSONANT_RUN_RE.search(core):
        return True
    # sesli harf oranı aşırı düşük kelimeler ('yrllara' değil 'tlgrfsz' gibi)
    vowels = sum(c in _VOWELS for c in core)
    if len(core) >= 5 and vowels / len(core) < 0.2:
        return True
    return False


def text_quality(text: str) -> float:
    """0..1 arası kaba metin kalitesi puanı; düşük puan bozuk çıkarım demektir."""
    sample = text[:30000]
    if not sample.strip():
        return 0.0
    non_space = [c for c in sample if not c.isspace()]
    if not non_space:
        return 0.0
    letter_ratio = sum(c.isalpha() for c in non_space) / len(non_space)
    words = re.findall(r"\S+", sample)[:4000]
    ok = n = 0
    for w in words:
        core = re.sub(r"^[^\wçğıöşüÇĞİÖŞÜ]+|[^\wçğıöşüÇĞİÖŞÜ]+$", "", w)
        if not core:
            continue
        n += 1
        if not _word_is_suspicious(core):
            ok += 1
    word_ratio = ok / max(n, 1)
    return round(0.25 * letter_ratio + 0.75 * word_ratio, 3)


# ---------------------------------------------------------------------------
# Dosya okuma (PDF / DOCX / TXT)
# ---------------------------------------------------------------------------

def _extract_pdf_pypdf(path: str) -> str:
    import pypdf  # type: ignore
    reader = pypdf.PdfReader(path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_pdf_pdftotext(path: str) -> str:
    out = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", path, "-"],
        capture_output=True, timeout=120,
    )
    if out.returncode != 0:
        raise RuntimeError("pdftotext hata verdi: " +
                           out.stderr.decode(errors="replace")[:200])
    return out.stdout.decode("utf-8", errors="replace")


def _read_pdf(path: str) -> str:
    """PDF metnini çıkarır; birden çok yöntem deneyip en kalitelisini seçer."""
    candidates = []
    errors = []
    try:
        candidates.append(_extract_pdf_pypdf(path))
    except ImportError:
        pass
    except Exception as e:
        errors.append("pypdf: " + str(e)[:150])
    # pypdf sonucu yoksa ya da bozuk görünüyorsa pdftotext ile de dene
    if shutil.which("pdftotext") and (
            not candidates or text_quality(candidates[0]) < QUALITY_THRESHOLD):
        try:
            candidates.append(_extract_pdf_pdftotext(path))
        except Exception as e:
            errors.append(str(e)[:150])
    if candidates:
        return max(candidates, key=text_quality)
    if errors:
        raise RuntimeError("PDF okunamadı: " + " | ".join(errors))
    raise RuntimeError(
        "PDF okunamadı: 'pypdf' paketi veya 'pdftotext' komutu bulunamadı. "
        "Kurulum için: pip install pypdf  (veya)  sudo apt install poppler-utils"
    )


_DOCX_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def _read_docx(path: str) -> str:
    """python-docx gerektirmeden .docx metnini çıkarır (docx = zip + XML)."""
    with zipfile.ZipFile(path) as zf:
        with zf.open("word/document.xml") as f:
            tree = ElementTree.parse(f)
    paragraphs = []
    for p in tree.iter("{%s}p" % _DOCX_NS["w"]):
        texts = [t.text or "" for t in p.iter("{%s}t" % _DOCX_NS["w"])]
        paragraphs.append("".join(texts))
    return "\n".join(paragraphs)


def read_document(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return _read_pdf(path)
    if ext == ".docx":
        return _read_docx(path)
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Belge türü ve mevzuat hiyerarşisi
# ---------------------------------------------------------------------------

DOC_TYPES = [
    # (anahtar kelimeler, tür adı, hiyerarşi sırası — küçük olan üstün)
    # Sıralama tespit önceliğidir: 'KDV Genel Uygulama Tebliği' gibi adlarda
    # tür kelimesi (tebliğ) kısaltmadan (kdv) önce yakalanmalıdır.
    (("teblig",), "Tebliğ", 4),
    (("sirkuler",), "Sirküler", 6),
    (("ozelge", "mukteza"), "Özelge", 7),
    (("yonetmelik",), "Yönetmelik", 3),
    (("yonerge",), "Yönerge", 5),
    (("cumhurbaskani karari", "bkk", "karar"), "Karar", 2),
    (("kilavuz", "klavuz", "rehber", "el kitabi"), "Rehber", 8),
    (("kanun", "khk"), "Kanun", 1),
    # Yalnız kısaltmayla adlandırılmış dosyalar ('VUK.pdf') kanun sayılır;
    # tür kelimeleri yukarıda arandığından buraya ancak düşerse gelir.
    (("vuk", "gvk", "kvk", "kdv", "otv", "aatuhk", "dvk", "mtvk", "vivk", "hk"), "Kanun", 1),
]


def detect_doc_type(filename: str, first_chunk: str = ""):
    """Dosya adından (öncelikli) ve içeriğin başından belge türünü tahmin eder.

    Kısa kısaltmalar (kdv, vuk...) yalnızca ayrı kelime olarak eşleşir ki
    içerikte geçen 'KDV' bir sirküleri 'kanun' sanmasın; uzun anahtarlar
    ('teblig', 'sirkuler') kelime öneki olarak eşleşir ('tebliği' gibi).
    """
    def match(hay_tokens, hay_text):
        for keys, name, rank in DOC_TYPES:
            for k in keys:
                if len(k) <= 4 or " " in k:
                    if k in hay_tokens or (" " in k and k in hay_text):
                        return name, rank
                elif any(t.startswith(k) for t in hay_tokens):
                    return name, rank
        return None

    for source in (filename, first_chunk[:400]):
        text = tr_fold(source)
        found = match(set(tokenize(source)), text)
        if found:
            return found
    return "Belge", 8


HIERARCHY_NOTE = {
    "Kanun": "Kanun hükmüdür; normlar hiyerarşisinde alt düzenlemelere (tebliğ, sirküler, özelge) üstündür.",
    "Karar": "Cumhurbaşkanı Kararı/BKK düzeyindedir; kanunun verdiği yetki sınırları içinde hüküm ifade eder.",
    "Yönetmelik": "Yönetmelik hükmüdür; dayanağı olan kanunla çelişirse kanun esas alınır.",
    "Tebliğ": "Tebliğ, idarenin genel düzenleyici işlemidir; kanun hükmüyle çelişirse kanun esas alınır.",
    "Yönerge": "Yönerge iç düzenlemedir; kanun ve üst düzenlemelerle birlikte değerlendirilmelidir.",
    "Sirküler": "Sirküler, idarenin görüşünü yansıtır; bağlayıcılığı kanun ve tebliğden sonra gelir.",
    "Özelge": "Özelge, yalnızca verildiği mükellefin somut olayı için idarenin görüşüdür; emsal olarak dikkatle kullanılmalıdır.",
    "Rehber": "Rehber/kılavuz, idarenin yardımcı kaynağıdır; bağlayıcı mevzuat değildir, dayandığı kanun ve tebliğ hükümleri esas alınır.",
    "Belge": "Belge türü dosya adından tespit edilemedi; hiyerarşideki yerini kontrol ediniz.",
}


# ---------------------------------------------------------------------------
# Çapraz atıf tanıma ("213 sayılı VUK'un 344 üncü maddesi" → bağlantı)
# ---------------------------------------------------------------------------

# Kanun numarası ↔ kısaltma ↔ ad parçası eşlemesi (dosya adlarıyla atıfları
# buluşturmak için). Örn. "213 sayılı Kanunun..." atfı, adında 'vuk' veya
# 'vergi usul' geçen dosyaya bağlanır.
_LAW_ALIASES = {
    "213": ("vuk", "vergi usul"),
    "193": ("gvk", "gelir vergisi"),
    "5520": ("kvk", "kurumlar vergisi"),
    "3065": ("kdv", "katma deger"),
    "4760": ("otv", "ozel tuketim"),
    "6183": ("aatuhk", "amme alacaklar"),
    "488": ("damga", "damga vergisi"),
    "492": ("harc", "harclar"),
    "7338": ("viv", "veraset ve intikal"),
    "197": ("mtv", "motorlu tasitlar"),
    "1319": ("emlak", "emlak vergisi"),
}


def doc_aliases(name: str):
    """Bir dosya adı için atıf eşleştirmede kullanılacak takma adlar."""
    folded = tr_fold(name)
    toks = set(tokenize(name))
    aliases = {folded}
    for num, alts in _LAW_ALIASES.items():
        if num in toks or any(a in folded for a in alts):
            aliases.add(num)
            aliases.update(alts)
    return aliases


# "344 üncü maddesi", "mükerrer 355 inci maddesinde", "geçici 67 nci madde",
# "5/a maddesi" biçimlerini yakalar. Madde başlıklarında sıra eki
# bulunmadığından ("MADDE 344 –") başlıklar yanlışlıkla eşleşmez.
_REF_RE = re.compile(
    r"(?:(mükerrer|geçici|ek)\s+)?"
    r"(\d+)(?:\s*/\s*([A-Za-zçğıöşüÇĞİÖŞÜ]))?"
    r"\s*['’]?\s*(?:üncü|uncu|inci|ıncı|nci|ncı|ncu|ncü)\s+madde\w*",
    re.IGNORECASE,
)

_CTX_LAW_NUM_RE = re.compile(r"(\d{2,5})\s*sayili")

# Atıf bağlamındaki tür kelimesi ("...Kanununun", "...Tebliğinin")
_CTX_TYPE_WORDS = [
    ("kanun", "Kanun"), ("teblig", "Tebliğ"), ("sirkuler", "Sirküler"),
    ("yonetmelik", "Yönetmelik"), ("yonerge", "Yönerge"), ("ozelge", "Özelge"),
]


# ---------------------------------------------------------------------------
# Değişiklik tespiti ("...Tebliğinin (2.1.) bölümü ... değiştirilmiştir")
# ---------------------------------------------------------------------------

# Uzun kalıplar önce gelmeli ("yürürlükten kaldırılmıştır" > "kaldırılmıştır")
_AMEND_VERB_RE = re.compile(
    r"yürürlükten kaldırılmıştır|değiştirilmiştir|eklenmiştir"
    r"|çıkarılmıştır|kaldırılmıştır|mülga"
)

_AMEND_KIND = {
    "yürürlükten kaldırılmıştır": "yürürlükten kaldırıldı",
    "değiştirilmiştir": "değiştirildi",
    "eklenmiştir": "yakınına ekleme yapıldı",
    "çıkarılmıştır": "ibare/bölüm çıkarıldı",
    "kaldırılmıştır": "kaldırıldı",
    "mülga": "mülga edildi",
}

# "(2.1.) numaralı bölümü", "(3.1.2) bölümünün" → hedef bölüm numarası
_AMEND_SECTION_RE = re.compile(
    r"\(\s*(\d+(?:\.\d+){0,4})\.?\s*\)[^()]{0,50}?böl", re.IGNORECASE)
# "3 üncü bölümü" biçimi
_AMEND_SECTION_ORD_RE = re.compile(
    r"(\d+(?:\.\d+){0,4})\s*(?:üncü|uncu|inci|ıncı|nci|ncı|ncu|ncü)\s+böl",
    re.IGNORECASE)

# Belge adında konu tespitinde anlamsız kelimeler (tür/kalıp kelimeleri)
_SUBJECT_NOISE = {tr_fold(w) for w in (
    "teblig", "tebligi", "tebliginde", "sirkuler", "sirkuleri", "ozelge",
    "kanun", "kanunu", "kanununda", "yonetmelik", "yonetmeligi", "yonerge",
    "genel", "uygulama", "degisiklik", "yapilmasina", "dair", "hakkinda",
    "iliskin", "seri", "sira", "no", "ile", "ve", "vergi", "vergisi",
)}


def subject_tokens(name: str):
    """Dosya adından belgenin konusunu ayırt eden kelimeleri çıkarır."""
    return {t for t in tokenize(name)
            if not t.isdigit() and len(t) >= 3 and t not in _SUBJECT_NOISE}


# Resmî Gazete tarihi ve Seri No ayrıştırma (dosya adı + metin başı)
_SERI_RE = re.compile(r"seri\s*no\s*[:.]?\s*\(?\s*(\d+)")
_DATE_RE = re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b")


def extract_doc_meta(filename: str, first_chunk: str):
    hay = tr_fold(filename) + " " + tr_fold(first_chunk[:800])
    seri = _SERI_RE.search(hay)
    date = _DATE_RE.search(hay)
    return (seri.group(1) if seri else None,
            "%s.%s.%s" % date.groups() if date else None)


# ---------------------------------------------------------------------------
# Madde bölümleme
# ---------------------------------------------------------------------------

# "MADDE 5", "Madde 5 -", "GEÇİCİ MADDE 67", "MÜKERRER MADDE 355", "EK MADDE 1"
_ARTICLE_RE = re.compile(
    r"^[ \t]*((?:GEÇİCİ|Geçici|MÜKERRER|Mükerrer|EK|Ek)\s+)?"
    r"(MADDE|Madde)\s+(\d+(?:/[A-Za-zÇĞİÖŞÜçğıöşü])?)\s*[-–—:.]?",
    re.MULTILINE,
)

# Tebliğ/sirküler bölüm başlıkları: "3.1.2. Başlık" gibi numaralı başlıklar
_SECTION_RE = re.compile(r"^[ \t]*(\d+(?:\.\d+){0,3})[.)]\s+(?=[A-ZÇĞİÖŞÜ])", re.MULTILINE)


def _chunk_paragraphs(text: str, prefix: str, size: int = 1500):
    """Yapısız metni ~size karakterlik bloklara ayırır (paragraf sınırında;
    boş satırsız dev paragraflar boşluktan kesilir)."""
    blocks, buf, n = [], [], 0
    for p in re.split(r"\n\s*\n", text):
        while len(p) > size * 2:  # tek dev paragraf: boşluktan böl
            cut = p.rfind(" ", size, size * 2)
            if cut == -1:
                cut = size * 2
            buf.append(p[:cut])
            blocks.append("\n\n".join(buf))
            buf, n = [], 0
            p = p[cut:]
        buf.append(p)
        n += len(p)
        if n >= size:
            blocks.append("\n\n".join(buf))
            buf, n = [], 0
    if buf:
        blocks.append("\n\n".join(buf))
    blocks = [b.strip() for b in blocks if b.strip()]
    if len(blocks) == 1:
        return [(prefix, blocks[0])]
    return [("%s %d" % (prefix, i + 1), b) for i, b in enumerate(blocks)]


def split_articles(text: str):
    """Metni madde/bölüm parçalarına ayırır.

    Önce 'MADDE n' kalıbı denenir (kanunlar); yeterince bölünemezse
    numaralı başlıklar (tebliğ/sirküler) denenir; o da olmazsa metin
    sabit uzunlukta paragraf bloklarına ayrılır (özelgeler genelde
    maddesizdir). Giriş kısmı (içindekiler vb.) tek dev blok olmasın
    diye ayrıca parçalanır.
    Dönüş: [(başlık, gövde), ...]
    """
    matches = list(_ARTICLE_RE.finditer(text))
    if len(matches) >= 3:
        parts = []
        if matches[0].start() > 200:
            parts.extend(_chunk_paragraphs(text[: matches[0].start()].strip(), "Giriş"))
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            prefix = (m.group(1) or "").strip()
            label = ((prefix + " ") if prefix else "") + "Madde " + m.group(3)
            body = text[start:end].strip()
            if body:
                parts.append((label, body))
        return parts

    matches = list(_SECTION_RE.finditer(text))
    if len(matches) >= 4:
        parts = []
        if matches[0].start() > 200:
            parts.extend(_chunk_paragraphs(text[: matches[0].start()].strip(), "Giriş"))
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            if body:
                parts.append(("Bölüm " + m.group(1), body))
        return parts

    # Yapısız belge
    return _chunk_paragraphs(text, "Bölüm")


# ---------------------------------------------------------------------------
# Otomatik yorum (kural tabanlı)
# ---------------------------------------------------------------------------

_TOPIC_RULES = [
    # (aranan kökler, yorum cümlesi)
    (("istisna",), "Bu hüküm bir <b>istisna</b> düzenlemesi içeriyor; istisnanın kapsamı ve şartlarının somut olayda birebir karşılanıp karşılanmadığını kontrol edin."),
    (("muafiyet", "muaf"), "Bu hüküm bir <b>muafiyet</b> düzenlemesi içeriyor; muafiyet şartlarının kaybedilmesi hâlinde vergileme yönünü değerlendirin."),
    (("vergi ziyai", "ziyai", "ziya"), "Hükümde <b>vergi ziyaı</b>na atıf var; ceza uygulamasında VUK 344 ve tekerrür hükümlerini birlikte değerlendirin."),
    (("ceza", "usulsuzluk"), "Hüküm <b>ceza/usulsüzlük</b> yaptırımı içeriyor; fiilin tarihindeki yürürlükteki tutar ve oranları teyit edin."),
    (("oran", "%", "nispet"), "Hükümde <b>oran/nispet</b> belirlemesi var; oranlar sıkça güncellenir, işlemin yapıldığı tarihte geçerli oranı esas alın."),
    (("had", "tutar", "sinir", "esik"), "Hükümde <b>had/tutar</b> belirlemesi var; bu tutarlar genellikle her yıl yeniden değerleme oranında güncellenir, güncel tebliği kontrol edin."),
    (("sure", "gun icinde", "ay icinde", "takvim yili"), "Hükümde <b>süre</b> düzenlemesi var; sürenin başlangıç anını ve hak düşürücü nitelikte olup olmadığını kontrol edin."),
    (("beyanname", "beyan"), "Hüküm <b>beyan yükümlülüğü</b> ile ilgili; beyan dönemi ve verilme/ödeme sürelerini teyit edin."),
    (("tevkifat", "stopaj", "kesinti"), "Hüküm <b>tevkifat/stopaj</b> düzenlemesi içeriyor; sorumlu sıfatıyla beyan gerekip gerekmediğini değerlendirin."),
    (("iade",), "Hüküm <b>iade</b> sürecine ilişkin; iade türüne göre aranan belgeler ve teminat/YMM raporu şartlarını kontrol edin."),
    (("zamanasimi",), "Hükümde <b>zamanaşımı</b> düzenlemesi var; tarh ve tahsil zamanaşımını (VUK 114, 6183 s.K. 102) ayrı ayrı değerlendirin."),
    (("pismanlik",), "Hüküm <b>pişmanlık</b> müessesesine ilişkin; VUK 371 şartlarının tamamının sağlandığını kontrol edin."),
    (("uzlasma",), "Hüküm <b>uzlaşma</b> müessesesine ilişkin; başvuru süresi ve uzlaşma kapsamındaki vergi/ceza türlerini teyit edin."),
    (("tecil", "taksit"), "Hüküm <b>tecil/taksitlendirme</b> düzenlemesi içeriyor; teminat ve faiz şartlarını kontrol edin."),
    (("yururluk", "yururluge"), "Hükümde <b>yürürlük</b> düzenlemesi var; işlem tarihinde hükmün yürürlükte olup olmadığını mutlaka teyit edin."),
    (("mucbir",), "Hüküm <b>mücbir sebep</b> hâllerine ilişkin; sürelerin işlemeyeceği dönemi belgelendirin."),
]


def make_comment(body: str, doc_type: str) -> str:
    """Madde metni için kısa, kural tabanlı otomatik yorum üretir."""
    folded = tr_fold(body)
    notes = []
    for keys, note in _TOPIC_RULES:
        if any(k in folded for k in keys):
            notes.append(note)
        if len(notes) >= 3:
            break
    notes.append(HIERARCHY_NOTE.get(doc_type, ""))
    return " ".join(n for n in notes if n)


_SENT_SPLIT_RE = re.compile(r"(?<=[.;:!?])\s+(?=[A-ZÇĞİÖŞÜ0-9(])")


def summarize(body: str, terms, max_sentences: int = 3) -> str:
    """Kısa özet: ilk cümle + arama terimlerini içeren cümleler."""
    # başlık satırını gövdeden ayır
    text = re.sub(r"\s+", " ", body).strip()
    sentences = _SENT_SPLIT_RE.split(text)
    if not sentences:
        return text[:300]
    picked = []
    seen = set()

    def add(s):
        s = s.strip()
        if s and s not in seen:
            seen.add(s)
            picked.append(s)

    add(sentences[0])
    if terms:
        for s in sentences[1:]:
            toks = tokenize(s)
            if any(any(term_matches(t, tok) for tok in toks) for t in terms):
                add(s)
            if len(picked) >= max_sentences:
                break
    summary = " ".join(picked)
    if len(summary) > 600:
        summary = summary[:600].rsplit(" ", 1)[0] + "…"
    return summary


def highlight(text_html: str, terms) -> str:
    """HTML'e çevrilmiş metinde arama terimlerini <mark> ile işaretler."""
    if not terms:
        return text_html

    def repl(m):
        word = m.group(0)
        folded = tr_fold(word)
        for t in terms:
            if term_matches(t, folded):
                return "<mark>" + word + "</mark>"
        return word

    return _WORD_RE.sub(repl, text_html)


# ---------------------------------------------------------------------------
# İndeks
# ---------------------------------------------------------------------------

class Article:
    __slots__ = ("id", "doc", "doc_type", "rank", "label", "body", "tokens")

    def __init__(self, id_, doc, doc_type, rank, label, body):
        self.id = id_
        self.doc = doc
        self.doc_type = doc_type
        self.rank = rank
        self.label = label
        self.body = body
        self.tokens = tokenize(body)


class Index:
    def __init__(self):
        self.articles = []          # [Article]
        self.docs = []              # [{name, type, articles, error}]
        self.mtimes = {}            # path -> mtime
        self.art_lookup = {}        # (doc_name, katlanmış etiket) -> article id
        self.doc_alias_map = []     # [(doc_name, doc_type, alias kümesi)]
        self.cited_by = {}          # hedef id -> [atıf yapan id'ler]
        self.amend_map = {}         # hedef id -> [{"src": id, "kind": str}]
        self.low_quality = set()    # bozuk metinli belge adları
        self.doc_quality = {}       # belge adı -> kalite puanı
        self.lock = threading.Lock()

    def needs_reindex(self) -> bool:
        current = {}
        if os.path.isdir(MEVZUAT_DIR):
            for fn in os.listdir(MEVZUAT_DIR):
                p = os.path.join(MEVZUAT_DIR, fn)
                if os.path.isfile(p) and fn.lower().endswith(SUPPORTED_EXTS):
                    current[p] = os.path.getmtime(p)
        return current != self.mtimes

    def build(self):
        with self.lock:
            self.articles = []
            self.docs = []
            self.mtimes = {}
            self.art_lookup = {}
            self.doc_alias_map = []
            self.low_quality = set()
            self.doc_quality = {}
            os.makedirs(MEVZUAT_DIR, exist_ok=True)
            for fn in sorted(os.listdir(MEVZUAT_DIR)):
                path = os.path.join(MEVZUAT_DIR, fn)
                if not (os.path.isfile(path) and fn.lower().endswith(SUPPORTED_EXTS)):
                    continue
                self.mtimes[path] = os.path.getmtime(path)
                name = os.path.splitext(fn)[0]
                entry = {"name": name, "file": fn, "type": "?", "articles": 0,
                         "error": None, "seri_no": None, "date": None,
                         "warning": None}
                try:
                    text = read_document(path)
                    text = re.sub(r"\r\n?", "\n", text)
                    quality = text_quality(text)
                    self.doc_quality[name] = quality
                    if quality < QUALITY_THRESHOLD:
                        entry["warning"] = OCR_ADVICE
                        self.low_quality.add(name)
                    doc_type, rank = detect_doc_type(fn, text)
                    entry["type"] = doc_type
                    entry["seri_no"], entry["date"] = extract_doc_meta(fn, text)
                    for label, body in split_articles(text):
                        if len(body.strip()) < 30:
                            continue
                        art = Article(len(self.articles), name, doc_type, rank, label, body)
                        self.articles.append(art)
                        self.art_lookup[(name, tr_fold(label))] = art.id
                        entry["articles"] += 1
                    self.doc_alias_map.append((name, doc_type, doc_aliases(name)))
                except Exception as e:  # dosya bozuksa diğerlerini engelleme
                    entry["error"] = str(e)
                self.docs.append(entry)

            # tüm belgeler yüklendikten sonra: ters atıf dizini + değişiklik taraması
            self.cited_by = {}
            for art in self.articles:
                for _s, _e, tid in self._find_refs(art):
                    if tid is not None and tid != art.id:
                        lst = self.cited_by.setdefault(tid, [])
                        if art.id not in lst:
                            lst.append(art.id)
            self._scan_amendments()

    def search(self, query: str, limit: int = 30):
        terms = query_terms(query)
        if not terms:
            return terms, []
        scored = []
        with self.lock:
            for art in self.articles:
                tf = {}
                for tok in art.tokens:
                    for t in terms:
                        if term_matches(t, tok):
                            tf[t] = tf.get(t, 0) + 1
                if not tf:
                    continue
                matched = len(tf)
                total = sum(tf.values())
                # tüm terimleri içeren maddeler öne; kanunlar alt
                # düzenlemelerden önce gelsin; kısa maddede geçiş daha değerli.
                # Geçiş sayısı 30'da kırpılır ki içindekiler benzeri dev
                # bloklar salt tekrar sayısıyla zirveye çıkmasın; bozuk
                # metinli belgeler geriye itilir.
                score = (
                    matched * 1000
                    + min(total, 30) * 10
                    + max(0, 9 - art.rank)
                    - min(len(art.tokens) // 400, 5)
                    - (500 if self.doc_quality.get(art.doc, 1) < QUALITY_SEVERE
                       else 150 if art.doc in self.low_quality else 0)
                )
                scored.append((score, art, matched, total))
        scored.sort(key=lambda x: -x[0])
        results = []
        for score, art, matched, total in scored[:limit]:
            r = {
                "id": art.id,
                "doc": art.doc,
                "doc_type": art.doc_type,
                "label": art.label,
                "matched_terms": matched,
                "total_terms": len(terms),
                "hits": total,
                "summary": highlight(html.escape(summarize(art.body, terms)), terms),
                "comment": make_comment(art.body, art.doc_type),
            }
            if art.doc in self.low_quality:
                r["low_quality"] = True
            warns = self._amend_info(art.id)
            if warns:
                srcs = []
                for w in warns:
                    s = w["doc"] + " " + w["label"]
                    if s not in srcs:
                        srcs.append(s)
                r["amended"] = True
                r["amend_srcs"] = "; ".join(srcs[:3])
            results.append(r)
        return terms, results

    # -- çapraz atıf çözümleme ---------------------------------------------

    def _resolve_ref_doc(self, context: str, current_doc: str, current_type: str):
        """Atıf bağlamından ('...213 sayılı Kanunun') hedef belgeyi bulur."""
        ctx = tr_fold(context)
        wanted_type = None
        for word, tname in _CTX_TYPE_WORDS:
            if word in ctx:
                wanted_type = tname
                break

        # bağlamda geçen kanun numarası / kısaltma / ad parçası
        hints = set(_CTX_LAW_NUM_RE.findall(ctx))
        ctx_toks = set(ctx.split())
        for num, alts in _LAW_ALIASES.items():
            if num in ctx_toks or any(a in ctx for a in alts):
                hints.add(num)
                hints.update(alts)

        candidates = [
            (name, dtype) for name, dtype, aliases in self.doc_alias_map
            if (not wanted_type or dtype == wanted_type) and hints & aliases
        ]
        if candidates:
            # birden çok aday varsa hiyerarşide üstte olanı (kanunu) seç
            candidates.sort(key=lambda c: next(
                (r for keys, n, r in DOC_TYPES if n == c[1]), 8))
            return candidates[0][0]

        # ipucu yok: "bu Kanunun"/"Kanunun" gibi genel atıflar
        if wanted_type is None or wanted_type == current_type or "bu " in ctx[-30:]:
            if wanted_type in (None, current_type):
                return current_doc
        if wanted_type:
            # mevcut belgeyle aynı konuyu paylaşan hedef türde belge
            # (örn. 'KDV ... Tebliği' içindeki 'Kanunun' → KDV Kanunu)
            cur_aliases = doc_aliases(current_doc)
            same_subject = [
                name for name, dtype, aliases in self.doc_alias_map
                if dtype == wanted_type and (aliases & cur_aliases)
            ]
            if same_subject:
                return same_subject[0]
            typed = [name for name, dtype, _ in self.doc_alias_map if dtype == wanted_type]
            if len(typed) == 1:
                return typed[0]
        return current_doc

    def _find_refs(self, art):
        """Madde gövdesindeki atıfları bulur: [(start, end, hedef_id|None)]."""
        refs = []
        for m in _REF_RE.finditer(art.body):
            context = art.body[max(0, m.start() - 80):m.start()]
            target_doc = self._resolve_ref_doc(context, art.doc, art.doc_type)
            prefix, num, letter = m.group(1), m.group(2), m.group(3)
            keys = []
            base = "madde " + num
            if prefix:
                base = tr_fold(prefix) + " " + base
            if letter:
                keys.append(base + "/" + tr_fold(letter))
            keys.append(base)
            target_id = None
            for key in keys:
                target_id = self.art_lookup.get((target_doc, key))
                if target_id is not None:
                    break
            if target_id == art.id:  # maddenin kendine atfını bağlama
                target_id = None
            refs.append((m.start(), m.end(), target_id))
        return refs

    # -- değişiklik taraması -------------------------------------------------

    def _amend_base_doc(self, context: str, current_doc: str):
        """Değişiklik cümlesindeki hedef (değiştirilen) belgeyi bulur."""
        ctx = tr_fold(context)
        wanted_type = None
        for word, tname in _CTX_TYPE_WORDS:
            if word in ctx:
                wanted_type = tname
                break
        others = [(n, t, a) for n, t, a in self.doc_alias_map if n != current_doc]
        if wanted_type:
            others = [o for o in others if o[1] == wanted_type]
        if not others:
            return None
        # bağlamda açıkça anılan belge (kanun no / kısaltma / ad)
        hints = set(_CTX_LAW_NUM_RE.findall(ctx))
        ctx_toks = set(ctx.split())
        for num, alts in _LAW_ALIASES.items():
            if num in ctx_toks or any(a in ctx for a in alts):
                hints.add(num)
                hints.update(alts)
        explicit = [n for n, _t, a in others if hints & a]
        if explicit:
            return explicit[0]
        # "aynı/adı geçen/mezkûr Tebliğin" → mevcut belgeyle aynı konudaki belge
        cur_subject = subject_tokens(current_doc)
        scored = [(len(cur_subject & subject_tokens(n)), n) for n, _t, _a in others]
        scored.sort(key=lambda x: -x[0])
        if scored and scored[0][0] > 0:
            return scored[0][1]
        if len(others) == 1:
            return others[0][0]
        return None

    def _scan_amendments(self):
        """Tüm maddelerde değişiklik kalıplarını tarar; değiştirilen bölüme
        değiştiren düzenlemeyi bağlayan haritayı kurar."""
        self.amend_map = {}
        for art in self.articles:
            body = art.body
            for m in _AMEND_VERB_RE.finditer(body):
                kind = _AMEND_KIND.get(m.group(0), "değiştirildi")
                context = body[max(0, m.start() - 260):m.start()]
                base = self._amend_base_doc(context, art.doc)
                if not base:
                    continue
                # bağlamdaki en son anılan hedef (bölüm numarası veya madde)
                candidates = []
                for sm in _AMEND_SECTION_RE.finditer(context):
                    candidates.append((sm.start(), "bolum " + sm.group(1)))
                for sm in _AMEND_SECTION_ORD_RE.finditer(context):
                    candidates.append((sm.start(), "bolum " + sm.group(1)))
                for rm in _REF_RE.finditer(context):
                    prefix, num = rm.group(1), rm.group(2)
                    key = ("madde " + num) if not prefix else (
                        tr_fold(prefix) + " madde " + num)
                    candidates.append((rm.start(), key))
                if not candidates:
                    continue
                key = max(candidates, key=lambda c: c[0])[1]
                target = self.art_lookup.get((base, key))
                # bölüm birebir bulunamazsa üst bölüme iliştir (3.1.2 → 3.1)
                while target is None and key.startswith("bolum") and "." in key:
                    key = key.rsplit(".", 1)[0]
                    target = self.art_lookup.get((base, key))
                if target is None or target == art.id:
                    continue
                lst = self.amend_map.setdefault(target, [])
                if not any(w["src"] == art.id and w["kind"] == kind for w in lst):
                    lst.append({"src": art.id, "kind": kind})

    def _amend_info(self, art_id: int):
        """Bir madde için değişiklik uyarılarını okunur biçimde döndürür."""
        out = []
        for w in self.amend_map.get(art_id, [])[:10]:
            src = self.articles[w["src"]]
            out.append({"id": src.id, "doc": src.doc, "label": src.label,
                        "kind": w["kind"]})
        return out

    def _render_body(self, art, terms):
        """Gövdeyi HTML'e çevirir: vurgu + tıklanabilir çapraz atıflar."""
        parts = []
        pos = 0
        for start, end, target_id in self._find_refs(art):
            parts.append(highlight(html.escape(art.body[pos:start]), terms))
            seg = highlight(html.escape(art.body[start:end]), terms)
            if target_id is not None:
                parts.append(
                    '<a class="ref" href="#" data-ref="%d" title="Atıf yapılan maddeye git">%s</a>'
                    % (target_id, seg))
            else:
                parts.append(
                    '<span class="ref-missing" title="Atıf yapılan madde yüklü dosyalarda bulunamadı">%s</span>'
                    % seg)
            pos = end
        parts.append(highlight(html.escape(art.body[pos:]), terms))
        return "".join(parts).replace("\n", "<br>")

    def get_article(self, art_id: int, terms):
        with self.lock:
            if 0 <= art_id < len(self.articles):
                art = self.articles[art_id]
                # ters atıf: bu maddeye atıf yapanlar — önce başka belgeler,
                # sonra hiyerarşi sırası (kanun → tebliğ → ... → özelge)
                cited = []
                for src_id in self.cited_by.get(art.id, [])[:80]:
                    s = self.articles[src_id]
                    cited.append({
                        "id": s.id, "doc": s.doc, "doc_type": s.doc_type,
                        "label": s.label, "rank": s.rank,
                        "same_doc": s.doc == art.doc,
                    })
                cited.sort(key=lambda c: (c["same_doc"], c["rank"], c["doc"]))
                for c in cited:
                    del c["rank"], c["same_doc"]
                return {
                    "id": art.id,
                    "doc": art.doc,
                    "doc_type": art.doc_type,
                    "label": art.label,
                    "body_html": self._render_body(art, terms),
                    "comment": make_comment(art.body, art.doc_type),
                    "warnings": self._amend_info(art.id),
                    "cited_by": cited[:50],
                    "low_quality": art.doc in self.low_quality,
                }
        return None

    def compliance(self, description: str, limit: int = 20):
        """İşlem tarifi için uyum kontrolü: ilgili hükümleri hiyerarşiye
        göre gruplar ve kontrol listesi üretir."""
        terms, results = self.search(description, limit=limit)
        groups = {}
        for r in results:
            groups.setdefault(r["doc_type"], []).append(r)
        ordered = sorted(groups.items(), key=lambda kv: min(
            (rank for keys, name, rank in DOC_TYPES if name == kv[0]), default=8))
        checklist = []
        if results:
            if any(r.get("amended") for r in results):
                checklist.append("⚠ Sonuçlar arasında sonradan DEĞİŞTİRİLMİŞ bölümler var — kırmızı uyarılı maddeleri açıp değiştiren düzenlemeyi mutlaka inceleyin.")
            checklist.append("İşlem tarihinde ilgili hükümlerin yürürlükte olan hâlini teyit edin (aşağıdaki maddeler yüklü dosyaların tarihli sürümüne göredir).")
            if any(g[0] == "Kanun" for g in ordered):
                checklist.append("Önce kanun hükmünü esas alın; tebliğ/sirküler/özelge yalnızca açıklayıcıdır.")
            if any(g[0] == "Özelge" for g in ordered):
                checklist.append("Bulunan özelgeler başka mükelleflerin somut olaylarına ilişkindir; birebir emsal almadan önce olay örgüsünü karşılaştırın.")
            checklist.append("Tutar, had ve oranların işlem yılına ait güncel değerlerini ilgili genel tebliğden doğrulayın.")
        return terms, ordered, checklist


INDEX = Index()

# ---------------------------------------------------------------------------
# Kayıtlı aramalar (uygulamanın yanında JSON dosyasında saklanır)
# ---------------------------------------------------------------------------

SAVED_FILE = os.path.join(BASE_DIR, "kayitli_aramalar.json")
_SAVED_LOCK = threading.Lock()


def load_saved():
    try:
        with open(SAVED_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [d for d in data
                    if isinstance(d, dict) and d.get("text")
                    and d.get("mode") in ("search", "comply")]
    except (OSError, json.JSONDecodeError):
        pass
    return []


def save_saved(items):
    tmp = SAVED_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    os.replace(tmp, SAVED_FILE)


def saved_add(mode: str, text: str):
    text = text.strip()
    if not text or mode not in ("search", "comply"):
        return load_saved()
    with _SAVED_LOCK:
        items = load_saved()
        if not any(i["mode"] == mode and i["text"] == text for i in items):
            items.insert(0, {"mode": mode, "text": text[:500]})
            save_saved(items[:100])  # makul bir üst sınır
        return load_saved()


def saved_delete(mode: str, text: str):
    with _SAVED_LOCK:
        items = [i for i in load_saved()
                 if not (i["mode"] == mode and i["text"] == text)]
        save_saved(items)
        return items

# ---------------------------------------------------------------------------
# Web arayüzü
# ---------------------------------------------------------------------------

PAGE = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mevzuat Asistanı</title>
<style>
:root {
  --bg: #f4f6f8; --card: #ffffff; --ink: #1a2733; --muted: #5b6b7a;
  --accent: #0b5e3b; --accent-ink: #ffffff; --line: #dde4ea;
  --mark: #ffe9a8; --warn-bg: #fff4e5; --warn-ink: #8a5300;
}
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, "Segoe UI", Roboto, "Noto Sans", sans-serif;
       background: var(--bg); color: var(--ink); }
header { background: var(--accent); color: var(--accent-ink); padding: 14px 22px;
         display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; }
header h1 { margin: 0; font-size: 1.25rem; }
header .sub { opacity: .85; font-size: .85rem; }
main { max-width: 1060px; margin: 0 auto; padding: 18px; }
.tabs { display: flex; gap: 8px; margin-bottom: 14px; }
.tabs button { border: 1px solid var(--line); background: var(--card); padding: 8px 16px;
  border-radius: 8px 8px 0 0; cursor: pointer; font-size: .95rem; color: var(--muted); }
.tabs button.active { background: var(--accent); color: var(--accent-ink); border-color: var(--accent); }
.panel { background: var(--card); border: 1px solid var(--line); border-radius: 0 10px 10px 10px;
         padding: 16px; }
.searchrow { display: flex; gap: 8px; }
.searchrow input, .searchrow textarea { flex: 1; padding: 10px 12px; font-size: 1rem;
  border: 1px solid var(--line); border-radius: 8px; font-family: inherit; }
.searchrow button, .btn { background: var(--accent); color: var(--accent-ink); border: 0;
  padding: 10px 18px; border-radius: 8px; font-size: 1rem; cursor: pointer; }
.btn.gray { background: #64748b; }
.hint { color: var(--muted); font-size: .85rem; margin: 8px 2px 0; }
.result { border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; margin-top: 12px;
  cursor: pointer; background: var(--card); transition: box-shadow .15s; }
.result:hover { box-shadow: 0 2px 10px rgba(0,0,0,.10); }
.result .top { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.badge { font-size: .72rem; padding: 2px 8px; border-radius: 999px; background: #e8eef4;
  color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: .03em; }
.badge.kanun { background: #dcefe4; color: var(--accent); }
.result .doc { font-weight: 700; }
.result .label { color: var(--muted); }
.summary { margin: 8px 0 0; line-height: 1.5; }
.comment { margin: 8px 0 0; padding: 8px 10px; background: var(--warn-bg); color: var(--warn-ink);
  border-radius: 8px; font-size: .88rem; line-height: 1.45; }
mark { background: var(--mark); padding: 0 2px; border-radius: 3px; }
.grouphdr { margin: 18px 0 4px; font-size: 1.02rem; font-weight: 700; color: var(--accent); }
.checklist { background: #eef6f1; border: 1px solid #cde5d7; border-radius: 10px;
  padding: 10px 14px 10px 30px; margin-top: 14px; }
.checklist li { margin: 6px 0; line-height: 1.45; }
#docs { font-size: .88rem; color: var(--muted); margin-top: 14px; }
#docs table { border-collapse: collapse; width: 100%; }
#docs td, #docs th { border-bottom: 1px solid var(--line); padding: 6px 8px; text-align: left; }
#docs .err { color: #b00020; }
#docs .warnq { color: #8a5300; }
dialog { border: 0; border-radius: 12px; max-width: 860px; width: 92vw; padding: 0;
  box-shadow: 0 10px 40px rgba(0,0,0,.3); }
dialog::backdrop { background: rgba(15,30,45,.55); }
.dlg-head { position: sticky; top: 0; background: var(--accent); color: var(--accent-ink);
  padding: 12px 18px; display: flex; justify-content: space-between; gap: 10px; align-items: center; }
.dlg-head b { font-size: 1.05rem; }
.dlg-head button { background: rgba(255,255,255,.2); color: #fff; border: 0; border-radius: 6px;
  padding: 6px 12px; cursor: pointer; font-size: .95rem; }
.dlg-body { padding: 16px 20px 22px; line-height: 1.65; max-height: 70vh; overflow-y: auto; }
.empty { color: var(--muted); padding: 18px 4px; }
a.ref { color: var(--accent); font-weight: 600; text-decoration: underline;
  text-decoration-style: dotted; text-underline-offset: 3px; cursor: pointer; }
.ref-missing { border-bottom: 1px dotted var(--muted); cursor: help; }
.amend { margin: 8px 0 0; padding: 8px 10px; background: #fdecea; color: #92211a;
  border: 1px solid #f2b8b5; border-radius: 8px; font-size: .88rem; line-height: 1.45; }
.amend a.ref { color: #92211a; }
.citedhdr { font-weight: 700; color: var(--accent); margin: 16px 0 6px; }
ul.citedby { margin: 0; padding-left: 4px; list-style: none; }
ul.citedby li { margin: 7px 0; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.chip { display: inline-flex; align-items: center; gap: 6px; background: #e8eef4;
  color: var(--ink); border: 1px solid var(--line); border-radius: 999px;
  padding: 4px 10px; font-size: .85rem; cursor: pointer; max-width: 340px; }
.chip .txt { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chip:hover { border-color: var(--accent); }
.chip .del { border: 0; background: none; color: var(--muted); cursor: pointer;
  font-size: .85rem; padding: 0 2px; }
.chip .del:hover { color: #b00020; }
.btn.star { background: #b98a00; }
footer { text-align: center; color: var(--muted); font-size: .8rem; padding: 18px; }
@media (prefers-color-scheme: dark) {
  :root { --bg: #10161c; --card: #1a232c; --ink: #e6edf3; --muted: #9fb0bf;
    --line: #2c3945; --mark: #6b5b12; --warn-bg: #33290f; --warn-ink: #ffd98a; }
  .badge { background: #26313c; }
  .badge.kanun { background: #14382a; color: #7fd0a8; }
  .checklist { background: #142720; border-color: #1f3a2f; }
  .chip { background: #26313c; }
  a.ref { color: #7fd0a8; }
  .amend { background: #3a1512; color: #ffb4a8; border-color: #5c2320; }
  .amend a.ref { color: #ffb4a8; }
}
</style>
</head>
<body>
<header>
  <h1>⚖️ Mevzuat Asistanı</h1>
  <span class="sub">Çevrimdışı vergi mevzuatı arama &amp; işlem uyum kontrolü</span>
</header>
<main>
  <div class="tabs">
    <button id="tab-search" class="active" onclick="showTab('search')">🔍 Konu Ara</button>
    <button id="tab-comply" onclick="showTab('comply')">✅ İşlem Uyum Kontrolü</button>
    <button id="tab-files" onclick="showTab('files'); loadStatus()">📁 Yüklü Mevzuat</button>
  </div>

  <div class="panel" id="panel-search">
    <div class="searchrow">
      <input id="q" placeholder="Aranacak konu… (ör. kira geliri istisnası, KDV tevkifatı, pişmanlık)"
             onkeydown="if(event.key==='Enter')doSearch()">
      <button onclick="doSearch()">Ara</button>
      <button class="btn star" title="Bu aramayı kaydet" onclick="saveCurrent('search')">⭐ Kaydet</button>
    </div>
    <div class="chips" id="chips-search"></div>
    <div class="hint">Sonuçlarda kısa özet ve otomatik yorum gösterilir; maddeye tıklayınca tam metin açılır. Sık kullandığınız konuları ⭐ ile kaydedin.</div>
    <div id="results"></div>
  </div>

  <div class="panel" id="panel-comply" style="display:none">
    <div class="searchrow">
      <textarea id="tx" rows="3" placeholder="Yapacağınız/inceleyeceğiniz işlemi kısaca tarif edin… (ör. Mükellef 2025 yılında konut kira geliri elde etti, beyanname vermedi; pişmanlıkla beyan etmek istiyor.)"></textarea>
    </div>
    <div style="margin-top:8px; display:flex; gap:8px">
      <button class="btn" onclick="doComply()">Uyum Kontrolü Yap</button>
      <button class="btn star" title="Bu işlem tarifini kaydet" onclick="saveCurrent('comply')">⭐ Kaydet</button>
    </div>
    <div class="chips" id="chips-comply"></div>
    <div class="hint">İşlem tarifinizdeki anahtar kavramlar mevzuatla eşleştirilir; ilgili hükümler normlar hiyerarşisine göre gruplanır ve kontrol listesi üretilir.</div>
    <div id="complyout"></div>
  </div>

  <div class="panel" id="panel-files" style="display:none">
    <p>Mevzuat dosyalarınızı (PDF, Word .docx, .txt) şu klasöre koyun ve <b>Yeniden İndeksle</b>'ye basın:</p>
    <p><code id="folder"></code></p>
    <p>Kanun güncellemesi geldiğinde eski dosyayı yenisiyle değiştirmeniz yeterlidir — uygulama açılışta ve yeniden indekslemede değişiklikleri otomatik algılar.</p>
    <button class="btn" onclick="reindex()">🔄 Yeniden İndeksle</button>
    <div id="docs"></div>
  </div>

  <dialog id="dlg">
    <div class="dlg-head">
      <button id="dlg-back" style="display:none" onclick="goBack()">← Geri</button>
      <b id="dlg-title"></b>
      <button onclick="dlg.close()">Kapat ✕</button>
    </div>
    <div class="dlg-body" id="dlg-body"></div>
  </dialog>
</main>
<footer>Bu araç yalnızca yüklediğiniz dosyalar üzerinde çevrimdışı çalışır. Otomatik yorumlar kural tabanlı yardımcı notlardır; hukuki dayanak olarak daima mevzuat metninin kendisini ve güncel resmî kaynakları esas alınız.</footer>
<script>
const dlg = document.getElementById('dlg');
let lastTerms = [];

function showTab(name){
  for (const t of ['search','comply','files']) {
    document.getElementById('panel-'+t).style.display = (t===name)?'':'none';
    document.getElementById('tab-'+t).classList.toggle('active', t===name);
  }
}

function badge(t){
  const cls = (t==='Kanun') ? 'badge kanun' : 'badge';
  return '<span class="'+cls+'">'+t+'</span>';
}

function resultCard(r){
  return '<div class="result" onclick="openArticle('+r.id+')">'
    + '<div class="top">'+badge(r.doc_type)+'<span class="doc">'+esc(r.doc)+'</span>'
    + '<span class="label">— '+esc(r.label)+'</span>'
    + '<span class="label" style="margin-left:auto">'+r.matched_terms+'/'+r.total_terms+' terim, '+r.hits+' geçiş</span></div>'
    + '<div class="summary">'+r.summary+'</div>'
    + (r.low_quality ? '<div class="amend">📷 Bu dosyadan çıkarılan metin bozuk görünüyor (taranmış PDF olabilir) — sonuç güvenilir değil. "Yüklü Mevzuat" sekmesindeki OCR önerisine bakın.</div>' : '')
    + (r.amended ? '<div class="amend">⚠ Bu bölümü değiştiren düzenleme var: <b>'+esc(r.amend_srcs)+'</b> — maddeyi açıp güncel hâli kontrol edin.</div>' : '')
    + (r.comment && !r.low_quality ? '<div class="comment">💡 '+r.comment+'</div>' : '')
    + '</div>';
}

function esc(s){ const d=document.createElement('div'); d.textContent=s; return d.innerHTML; }

async function doSearch(){
  const q = document.getElementById('q').value.trim();
  const out = document.getElementById('results');
  if(!q){ out.innerHTML=''; return; }
  out.innerHTML = '<div class="empty">Aranıyor…</div>';
  const res = await fetch('/api/search?q='+encodeURIComponent(q)).then(r=>r.json());
  lastTerms = res.terms;
  if(!res.results.length){
    out.innerHTML = '<div class="empty">Sonuç bulunamadı. Farklı kelimelerle deneyin veya "Yüklü Mevzuat" sekmesinden dosyaların indekslendiğini kontrol edin.</div>';
    return;
  }
  out.innerHTML = res.results.map(resultCard).join('');
}

async function doComply(){
  const t = document.getElementById('tx').value.trim();
  const out = document.getElementById('complyout');
  if(!t){ out.innerHTML=''; return; }
  out.innerHTML = '<div class="empty">İnceleniyor…</div>';
  const res = await fetch('/api/compliance', {method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify({text:t})}).then(r=>r.json());
  lastTerms = res.terms;
  let h = '';
  if(res.checklist.length){
    h += '<div class="checklist"><b>Kontrol listesi</b><ul>' +
      res.checklist.map(c=>'<li>'+c+'</li>').join('') + '</ul></div>';
  }
  if(!res.groups.length){
    h += '<div class="empty">İşlem tarifinizle eşleşen hüküm bulunamadı. Tarife vergi türü, işlem türü gibi anahtar kavramlar ekleyin.</div>';
  }
  for(const [type, items] of res.groups){
    h += '<div class="grouphdr">'+type+' düzeyi ('+items.length+')</div>';
    h += items.map(resultCard).join('');
  }
  out.innerHTML = h;
}

let dlgStack = [];   // çapraz atıf gezinmesi için geri yığını
let dlgCurrent = null;

// nav: 'new' = sonuç listesinden (yığını sıfırla), 'ref' = atıf bağlantısından
// (mevcut maddeyi yığına koy), 'back' = geri düğmesinden (yığına dokunma)
async function openArticle(id, nav){
  nav = nav || 'new';
  const res = await fetch('/api/article?id='+id+'&terms='+encodeURIComponent(lastTerms.join(' '))).then(r=>r.json());
  if(!res || res.error) return;
  if(nav === 'new') dlgStack = [];
  else if(nav === 'ref' && dlgCurrent !== null) dlgStack.push(dlgCurrent);
  dlgCurrent = id;
  document.getElementById('dlg-back').style.display = dlgStack.length ? '' : 'none';
  document.getElementById('dlg-title').textContent = res.doc + ' — ' + res.label + '  [' + res.doc_type + ']';
  let h = '';
  if(res.low_quality){
    h += '<div class="amend">📷 Bu dosyadan çıkarılan metin bozuk görünüyor (taranmış veya bozuk kodlamalı PDF). Aşağıdaki metne güvenmeyin; "Yüklü Mevzuat" sekmesindeki OCR önerisini uygulayın.</div>';
  }
  for(const w of (res.warnings || [])){
    h += '<div class="amend">⚠ Bu bölüm <a class="ref" href="#" data-ref="'+w.id+'">'+
      esc(w.doc)+' — '+esc(w.label)+'</a> ile <b>'+esc(w.kind)+'</b>. Güncel uygulama için değiştiren düzenlemeyi açın.</div>';
  }
  h += (res.comment ? '<div class="comment">💡 '+res.comment+'</div><br>' : '') + res.body_html;
  if(res.cited_by && res.cited_by.length){
    h += '<div class="citedhdr">📌 Bu maddeye atıf yapan düzenlemeler ('+res.cited_by.length+')</div><ul class="citedby">'
      + res.cited_by.map(c =>
        '<li>'+badge(c.doc_type)+' <a class="ref" href="#" data-ref="'+c.id+'">'+esc(c.doc)+' — '+esc(c.label)+'</a></li>'
      ).join('') + '</ul>';
  }
  document.getElementById('dlg-body').innerHTML = h;
  document.getElementById('dlg-body').scrollTop = 0;
  if(!dlg.open) dlg.showModal();
}

function goBack(){
  if(dlgStack.length) openArticle(dlgStack.pop(), 'back');
}

// atıf bağlantıları (dinamik içerik → event delegation)
document.getElementById('dlg-body').addEventListener('click', e => {
  const a = e.target.closest('a.ref');
  if(a){ e.preventDefault(); openArticle(parseInt(a.dataset.ref), 'ref'); }
});

// --- kayıtlı aramalar ---
async function loadSaved(){
  const res = await fetch('/api/saved').then(r=>r.json());
  renderChips(res.items);
}

function renderChips(items){
  for(const mode of ['search','comply']){
    const el = document.getElementById('chips-'+mode);
    el.innerHTML = '';
    for(const item of items.filter(i=>i.mode===mode)){
      const chip = document.createElement('span');
      chip.className = 'chip';
      chip.onclick = () => useSaved(mode, item.text);
      const txt = document.createElement('span');
      txt.className = 'txt'; txt.title = item.text; txt.textContent = '⭐ ' + item.text;
      const del = document.createElement('button');
      del.className = 'del'; del.title = 'Kaydı sil'; del.textContent = '✕';
      del.onclick = (e) => { e.stopPropagation(); delSaved(mode, item.text); };
      chip.append(txt, del);
      el.append(chip);
    }
  }
}

function useSaved(mode, text){
  if(mode==='search'){ document.getElementById('q').value = text; showTab('search'); doSearch(); }
  else { document.getElementById('tx').value = text; showTab('comply'); doComply(); }
}

async function saveCurrent(mode){
  const text = (mode==='search' ? document.getElementById('q') : document.getElementById('tx')).value.trim();
  if(!text) return;
  const res = await fetch('/api/saved', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({action:'add', mode, text})}).then(r=>r.json());
  renderChips(res.items);
}

async function delSaved(mode, text){
  const res = await fetch('/api/saved', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({action:'del', mode, text})}).then(r=>r.json());
  renderChips(res.items);
}

loadSaved();

async function loadStatus(){
  const s = await fetch('/api/status').then(r=>r.json());
  document.getElementById('folder').textContent = s.folder;
  const el = document.getElementById('docs');
  if(!s.docs.length){ el.innerHTML = '<p class="empty">Henüz dosya yüklenmemiş.</p>'; return; }
  el.innerHTML = '<table><tr><th>Dosya</th><th>Tür</th><th>Tarih</th><th>Seri No</th><th>Madde/Bölüm</th><th>Durum</th></tr>' +
    s.docs.map(d=>'<tr><td>'+esc(d.file)+'</td><td>'+esc(d.type)+'</td><td>'+esc(d.date||'—')+'</td><td>'+esc(d.seri_no||'—')+'</td><td>'+d.articles+'</td><td>'+
      (d.error?'<span class="err">'+esc(d.error)+'</span>':(d.warning?'<span class="warnq">📷 '+esc(d.warning)+'</span>':'✓'))+'</td></tr>').join('') + '</table>';
}

async function reindex(){
  document.getElementById('docs').innerHTML = '<p class="empty">İndeksleniyor…</p>';
  await fetch('/api/reindex', {method:'POST'});
  loadStatus();
}
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # sessiz sunucu
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(url.query)
        if url.path == "/":
            if INDEX.needs_reindex():
                INDEX.build()
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif url.path == "/api/search":
            q = qs.get("q", [""])[0]
            terms, results = INDEX.search(q)
            self._json({"terms": terms, "results": results})
        elif url.path == "/api/article":
            try:
                art_id = int(qs.get("id", ["-1"])[0])
            except ValueError:
                art_id = -1
            terms = query_terms(qs.get("terms", [""])[0])
            art = INDEX.get_article(art_id, terms)
            if art:
                self._json(art)
            else:
                self._json({"error": "bulunamadı"}, 404)
        elif url.path == "/api/status":
            self._json({"folder": MEVZUAT_DIR, "docs": INDEX.docs})
        elif url.path == "/api/saved":
            self._json({"items": load_saved()})
        else:
            self._json({"error": "yok"}, 404)

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        if url.path == "/api/reindex":
            INDEX.build()
            self._json({"ok": True, "docs": INDEX.docs})
        elif url.path == "/api/compliance":
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                payload = {}
            terms, groups, checklist = INDEX.compliance(payload.get("text", ""))
            self._json({"terms": terms, "groups": groups, "checklist": checklist})
        elif url.path == "/api/saved":
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                payload = {}
            action = payload.get("action")
            mode = payload.get("mode", "")
            text = payload.get("text", "")
            if action == "add":
                self._json({"items": saved_add(mode, text)})
            elif action == "del":
                self._json({"items": saved_delete(mode, text)})
            else:
                self._json({"error": "geçersiz istek"}, 400)
        else:
            self._json({"error": "yok"}, 404)


def main():
    parser = argparse.ArgumentParser(description="Mevzuat Asistanı — çevrimdışı mevzuat arama aracı")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    os.makedirs(MEVZUAT_DIR, exist_ok=True)
    print("Mevzuat dosyaları klasörü:", MEVZUAT_DIR)
    print("İndeksleniyor…")
    INDEX.build()
    total = sum(d["articles"] for d in INDEX.docs)
    print("%d dosya, %d madde/bölüm indekslendi." % (len(INDEX.docs), total))
    for d in INDEX.docs:
        if d["error"]:
            print("  UYARI — %s: %s" % (d["file"], d["error"]))

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = "http://127.0.0.1:%d/" % args.port
    print("Sunucu hazır:", url)
    print("Kapatmak için Ctrl+C")
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nKapatılıyor…")
        server.shutdown()


if __name__ == "__main__":
    main()
