# PDF Dönüştürücü 📄→📊📝

PDF dosyalarını **Word (.docx)** veya **Excel (.xlsx)** formatına çeviren,
Linux'ta tıkla-çalıştır şeklinde kullanılabilen basit bir masaüstü uygulaması.

- Türkçe grafik arayüz
- Birden fazla PDF'i tek seferde dönüştürme
- Tablolar Word'de gerçek tablo, Excel'de hücrelere dağıtılmış olarak aktarılır
- Metinler Word'de paragraf, Excel'de satır satır aktarılır
- Her PDF sayfası Excel'de ayrı çalışma sayfası olur
- Türkçe karakterler (ç, ğ, ı, İ, ö, ş, ü) tam desteklenir — hem içerikte hem dosya adlarında

## Kurulum (tek seferlik)

1. Bu depoyu indirin (veya `git clone` yapın).
2. Terminalde proje klasörüne girip şunu çalıştırın:

   ```bash
   ./kur.sh
   ```

Bu komut uygulama menüsüne ve masaüstünüze **"PDF Dönüştürücü"** kısayolu ekler.
Artık kısayola tıklayarak uygulamayı açabilirsiniz.

> İlk açılışta gerekli kütüphaneler otomatik olarak kurulur (internet gerekir),
> bu bir kez yapılır ve 1-2 dakika sürebilir. Sonraki açılışlar anındadır.

### Gereksinimler

Çoğu Linux dağıtımında hazır gelir; eksikse:

```bash
# Debian / Ubuntu / Mint
sudo apt install python3 python3-venv python3-tk

# Fedora
sudo dnf install python3 python3-tkinter

# Arch
sudo pacman -S python tk
```

## Kullanım

1. **➕ PDF Ekle** ile bir veya daha fazla PDF seçin.
2. Çıktı formatını seçin: **Word (.docx)** veya **Excel (.xlsx)**.
3. İsterseniz **📁 Çıktı Klasörü** seçin (boş bırakılırsa dosyalar PDF'in yanına kaydedilir).
4. **🔄 Dönüştür** düğmesine basın.

### Komut satırından kullanım

```bash
./baslat.sh belge.pdf --format word
./baslat.sh rapor.pdf tablo.pdf --format excel --cikti ~/Belgeler
```

## Notlar

- Uygulama, PDF içindeki **metin ve tabloları** çıkarır. Taranmış (resim olarak
  kaydedilmiş) PDF'lerde metin bulunmadığı için çıktı boş olabilir; bu tür
  dosyalar için önce OCR uygulanması gerekir.
- Karmaşık sayfa düzenleri (çok sütunlu dergi sayfaları vb.) birebir aynı
  görünümde aktarılamayabilir; içerik korunur, düzen sadeleştirilir.
