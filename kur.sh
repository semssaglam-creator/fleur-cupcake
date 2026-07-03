#!/usr/bin/env bash
# Uygulama menüsüne ve masaüstüne "PDF Dönüştürücü" kısayolu ekler.
# Bir kez çalıştırmanız yeterlidir: ./kur.sh

set -e
cd "$(dirname "$0")"

UYGULAMA_DIZINI="$(pwd)"
KISAYOL_ADI="pdf-donusturucu.desktop"

chmod +x baslat.sh

KISAYOL_ICERIK="[Desktop Entry]
Type=Application
Name=PDF Dönüştürücü
Comment=PDF dosyalarını Word veya Excel formatına çevirir
Exec=$UYGULAMA_DIZINI/baslat.sh
Path=$UYGULAMA_DIZINI
Icon=application-pdf
Terminal=false
Categories=Office;Utility;
Keywords=pdf;word;excel;dönüştür;convert;
"

# Uygulama menüsüne ekle
mkdir -p "$HOME/.local/share/applications"
echo "$KISAYOL_ICERIK" > "$HOME/.local/share/applications/$KISAYOL_ADI"
chmod +x "$HOME/.local/share/applications/$KISAYOL_ADI"

# Masaüstüne ekle (masaüstü klasörü varsa)
MASAUSTU="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
if [ -d "$MASAUSTU" ]; then
    echo "$KISAYOL_ICERIK" > "$MASAUSTU/$KISAYOL_ADI"
    chmod +x "$MASAUSTU/$KISAYOL_ADI"
    # GNOME'da kısayola çift tıklayınca "güvenilir" olarak işaretle
    command -v gio >/dev/null 2>&1 && \
        gio set "$MASAUSTU/$KISAYOL_ADI" metadata::trusted true 2>/dev/null || true
fi

echo ""
echo "✅ Kurulum tamamlandı!"
echo "   Uygulama menüsünde 'PDF Dönüştürücü' olarak görünecek."
[ -d "$MASAUSTU" ] && echo "   Masaüstünüze de kısayol eklendi."
echo "   Dilerseniz doğrudan ./baslat.sh ile de açabilirsiniz."
