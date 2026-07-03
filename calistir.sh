#!/usr/bin/env bash
# Mevzuat Asistanı — tıkla çalıştır betiği
# Çift tıklayınca (veya terminalden ./calistir.sh ile) uygulamayı başlatır.
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "HATA: python3 bulunamadı. Kurulum: sudo apt install python3"
    read -r -p "Kapatmak için Enter'a basın..."
    exit 1
fi

# PDF desteği için pypdf veya pdftotext aranır; ikisi de yoksa ve internet
# varsa pypdf yerel bir sanal ortama bir defalık kurulur. Sonrası tamamen
# çevrimdışıdır. (.docx ve .txt dosyaları için hiçbir kurulum gerekmez.)
PY=python3
if ! $PY -c "import pypdf" >/dev/null 2>&1 && ! command -v pdftotext >/dev/null 2>&1; then
    if [ -x ".venv/bin/python" ] && .venv/bin/python -c "import pypdf" >/dev/null 2>&1; then
        PY=.venv/bin/python
    else
        echo "PDF desteği için pypdf kuruluyor (yalnızca ilk çalıştırmada, internet gerekir)..."
        if $PY -m venv .venv 2>/dev/null && .venv/bin/pip -q install pypdf 2>/dev/null; then
            PY=.venv/bin/python
        else
            echo "UYARI: pypdf kurulamadı. PDF'ler okunamayacak (Word/.txt çalışır)."
            echo "Elle kurulum: sudo apt install poppler-utils   (pdftotext için)"
        fi
    fi
fi

exec $PY mevzuat_asistani.py "$@"
