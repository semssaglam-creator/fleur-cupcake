#!/usr/bin/env bash
# Hiçbir kurulum gerektirmeyen tek dosyalık uygulamayı derler.
# Python, tüm kütüphaneler ve OCR motoru (tesseract + Türkçe dil paketi)
# tek çalıştırılabilir dosyanın içine gömülür.
#
# Gereksinimler (yalnızca derleme yapan makinede):
#   sudo apt install python3 python3-venv python3-tk tesseract-ocr tesseract-ocr-tur
#
# Kullanım: ./derle.sh [python-yorumlayicisi]

set -e
cd "$(dirname "$0")"

PYTHON="${1:-python3}"

command -v tesseract >/dev/null || {
    echo "HATA: tesseract bulunamadı (sudo apt install tesseract-ocr tesseract-ocr-tur)" >&2
    exit 1
}
"$PYTHON" -c "import tkinter" || {
    echo "HATA: tkinter bulunamadı (sudo apt install python3-tk)" >&2
    exit 1
}

# "List of available languages in "/usr/share/.../tessdata/" satırından yolu al
TESSDATA="$(tesseract --list-langs 2>&1 | head -1 | sed 's/.*"\(.*\)".*/\1/' | sed 's:/$::')"
[ -d "$TESSDATA" ] || TESSDATA="$(ls -d /usr/share/tesseract-ocr/*/tessdata 2>/dev/null | head -1)"
[ -d "$TESSDATA" ] || { echo "HATA: tessdata klasörü bulunamadı" >&2; exit 1; }
echo "tessdata: $TESSDATA"

BUILD_VENV=".derleme-venv"
if [ ! -d "$BUILD_VENV" ]; then
    "$PYTHON" -m venv "$BUILD_VENV"
    "$BUILD_VENV/bin/pip" install --upgrade pip -q
    "$BUILD_VENV/bin/pip" install -q -r requirements.txt pyinstaller
fi

"$BUILD_VENV/bin/pyinstaller" --noconfirm --clean --onefile --windowed \
    --name pdf-donusturucu \
    --add-binary "$(command -v tesseract):tesseract" \
    --add-data "$TESSDATA:tesseract/tessdata" \
    pdf_donusturucu.py

echo ""
echo "✅ Derleme tamamlandı: dist/pdf-donusturucu"
echo "   Bu tek dosyayı herhangi bir Linux bilgisayara kopyalayıp"
echo "   çift tıklayarak çalıştırabilirsiniz — kurulum gerekmez."
