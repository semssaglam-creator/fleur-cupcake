# PDF Dönüştürücü 📄→📊📝

PDF dosyalarını **Word (.docx)** veya **Excel (.xlsx)** formatına çeviren,
Linux'ta tıkla-çalıştır şeklinde kullanılabilen basit bir masaüstü uygulaması.

- Türkçe grafik arayüz
- Birden fazla PDF'i tek seferde dönüştürme
- Tablolar Word'de gerçek tablo, Excel'de hücrelere dağıtılmış olarak aktarılır
- Metinler Word'de paragraf, Excel'de satır satır aktarılır
- Her PDF sayfası Excel'de ayrı çalışma sayfası olur
- Türkçe karakterler (ç, ğ, ı, İ, ö, ş, ü) tam desteklenir — hem içerikte hem dosya adlarında
- **Taranmış PDF'ler otomatik OCR ile okunur** (Türkçe + İngilizce) — metin katmanı
  olmayan sayfalar algılanıp görüntüden metne çevrilir

## Seçenek 1: Hazır uygulama (hiçbir kurulum gerekmez) ⭐

Derlenmiş tek dosyalık sürümü indirin: Python, tüm kütüphaneler ve OCR motoru
dosyanın içindedir, bilgisayarınıza hiçbir şey kurmanız gerekmez.

1. `pdf-donusturucu-linux-x86_64.tar.gz` dosyasını indirip çıkarın
   (GitHub'da **Releases** veya **Actions** sekmesindeki derleme çıktılarından).
2. `pdf-donusturucu` dosyasına çift tıklayın. Açılmazsa: sağ tık → Özellikler →
   İzinler → "Program olarak çalıştırılabilir" kutusunu işaretleyin
   (veya terminalde `chmod +x pdf-donusturucu`).

> Yeni bir sürüm derlemek için: depo sayfasında **Actions →
> "Tek dosyalık uygulama derle" → Run workflow**. Kendi bilgisayarınızda
> derlemek isterseniz `./derle.sh` kullanın.

## Seçenek 2: Kaynaktan kurulum (tek seferlik)

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

Kaynaktan çalıştırırken OCR de kullanmak isterseniz tesseract kurun
(hazır uygulamada buna gerek yoktur, motor pakete dahildir):

```bash
sudo apt install tesseract-ocr tesseract-ocr-tur
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
./baslat.sh taranmis.pdf --format word --ocr-kapali   # OCR istemiyorsanız
```

(Hazır uygulamada `./baslat.sh` yerine `./pdf-donusturucu` yazın.)

## Notlar

- Taranmış (resim olarak kaydedilmiş) sayfalar otomatik algılanır ve OCR ile
  okunur. OCR sonucu, taramanın kalitesine bağlı olarak küçük hatalar
  içerebilir. İstenirse arayüzdeki kutucuktan veya `--ocr-kapali` ile
  kapatılabilir.
- Karmaşık sayfa düzenleri (çok sütunlu dergi sayfaları vb.) birebir aynı
  görünümde aktarılamayabilir; içerik korunur, düzen sadeleştirilir.
