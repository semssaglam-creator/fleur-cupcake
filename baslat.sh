#!/usr/bin/env bash
# PDF Dönüştürücü başlatıcısı.
# İlk çalıştırmada gerekli Python kütüphanelerini sanal ortama kurar,
# sonraki çalıştırmalarda doğrudan uygulamayı açar.

set -e
cd "$(dirname "$0")"

VENV=".venv"

hata_goster() {
    MESAJ="$1"
    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title="PDF Dönüştürücü" --text="$MESAJ" || true
    elif command -v notify-send >/dev/null 2>&1; then
        notify-send "PDF Dönüştürücü" "$MESAJ" || true
    fi
    echo "HATA: $MESAJ" >&2
    exit 1
}

# Python kontrolü
command -v python3 >/dev/null 2>&1 || hata_goster \
    "python3 bulunamadı. Kurmak için:\nsudo apt install python3 python3-venv python3-tk"

# Tkinter kontrolü
python3 -c "import tkinter" >/dev/null 2>&1 || hata_goster \
    "Tkinter bulunamadı. Kurmak için:\n\nDebian/Ubuntu: sudo apt install python3-tk\nFedora: sudo dnf install python3-tkinter\nArch: sudo pacman -S tk"

# Sanal ortam ve bağımlılıklar
if [ ! -f "$VENV/kurulum_tamam" ]; then
    echo "İlk kurulum yapılıyor, lütfen bekleyin..."
    if command -v zenity >/dev/null 2>&1; then
        (
            python3 -m venv "$VENV"
            "$VENV/bin/pip" install --upgrade pip -q
            "$VENV/bin/pip" install -r requirements.txt -q
        ) | zenity --progress --pulsate --no-cancel --auto-close \
            --title="PDF Dönüştürücü" \
            --text="Gerekli kütüphaneler kuruluyor, lütfen bekleyin..." || true
    else
        python3 -m venv "$VENV"
        "$VENV/bin/pip" install --upgrade pip -q
        "$VENV/bin/pip" install -r requirements.txt -q
    fi

    "$VENV/bin/python" -c "import pdfplumber, docx, openpyxl" \
        || { rm -rf "$VENV"; hata_goster "Kütüphaneler kurulamadı. İnternet bağlantınızı kontrol edip tekrar deneyin."; }
    touch "$VENV/kurulum_tamam"
fi

exec "$VENV/bin/python" pdf_donusturucu.py "$@"
