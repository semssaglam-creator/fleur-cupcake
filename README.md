# ⚖️ Mevzuat Asistanı

Gelir uzmanları için **tamamen çevrimdışı** çalışan vergi mevzuatı arama ve
işlem uyum kontrol aracı. Kanun, yönetmelik, tebliğ, sirküler, yönerge ve
özelge dosyalarınızı (PDF, Word `.docx`, `.txt`) bir klasöre atarsınız;
uygulama bunları **madde madde** indeksler ve tarayıcınızda şunları sunar:

- 🔍 **Konu arama** — aradığınız konuyla ilgili maddeleri bulur, **kısa özet**
  ve **otomatik yorum** (istisna/muafiyet/ceza/oran/süre uyarıları + normlar
  hiyerarşisi notu) gösterir.
- ✅ **İşlem uyum kontrolü** — yapacağınız işlemi kendi cümlelerinizle tarif
  edersiniz; ilgili hükümler **Kanun → Tebliğ → Sirküler → Özelge**
  hiyerarşisine göre gruplanır ve bir kontrol listesi üretilir.
- 📄 **Tam metin görüntüleme** — herhangi bir sonuca tıklayınca ilgili madde
  metni, arama terimleri işaretlenmiş hâlde açılır.
- 🔄 **Güncellenebilir mevzuat** — kanun değiştiğinde eski dosyayı yenisiyle
  değiştirmeniz yeterli; uygulama değişikliği otomatik algılar
  ("Yeniden İndeksle" düğmesi de vardır).

Hiçbir veri internete gönderilmez; her şey bilgisayarınızda çalışır.

## Kurulum ve çalıştırma (Linux)

1. Bu klasörü bilgisayarınıza kopyalayın.
2. `calistir.sh` dosyasına çift tıklayın (ya da terminalde `./calistir.sh`).
   Gerekirse önce çalıştırma izni verin: `chmod +x calistir.sh`
3. Tarayıcı otomatik açılır: <http://127.0.0.1:8765/>

> **PDF desteği:** Word ve `.txt` dosyaları için hiçbir kurulum gerekmez.
> PDF okumak için `pypdf` paketi veya `pdftotext` komutu kullanılır;
> `calistir.sh` ikisi de yoksa ilk çalıştırmada `pypdf`'i yerel bir sanal
> ortama kurmayı dener (yalnızca bu adım internet ister). Alternatif:
> `sudo apt install poppler-utils`

Masaüstü kısayolu isterseniz `Mevzuat-Asistani.desktop` dosyasını
masaüstünüze kopyalayıp "çalıştırılabilir" olarak işaretleyin.

## Mevzuat dosyalarını yükleme

Dosyaları uygulamanın yanındaki **`mevzuat/`** klasörüne koyun. Belge türü
dosya adından tespit edilir; bu yüzden adlandırmada türü belirtin:

```
mevzuat/
├── 193 Gelir Vergisi Kanunu.pdf
├── 213 Vergi Usul Kanunu.docx
├── KDV Genel Uygulama Tebligi.pdf
├── GVK Sirkuleri 2025-1.docx
└── Ozelge - Kira geliri istisnasi 2024.pdf
```

Tanınan tür anahtar kelimeleri: `kanun`, `yönetmelik`, `tebliğ`, `sirküler`,
`yönerge`, `özelge` (Türkçe karakterli/karaktersiz yazım fark etmez).

**Güncelleme:** Bir kanunda değişiklik olduğunda güncel metni indirip aynı
adla eski dosyanın üzerine yazın. Uygulama açılışta ve her "Yeniden
İndeksle"de dosya değişikliklerini algılar.

## Nasıl çalışır?

- Metinler `MADDE n` / `GEÇİCİ MADDE n` / `MÜKERRER MADDE n` kalıplarına göre
  maddelere ayrılır; tebliğ/sirkülerlerde numaralı bölüm başlıkları,
  özelgelerde paragraf blokları kullanılır.
- Arama Türkçe karakter katlamalı ve önek eşleşmelidir: `istisna` araması
  `istisnasından`, `İSTİSNA` gibi biçimleri de bulur.
- Sıralamada tüm terimleri içeren maddeler ve normlar hiyerarşisinde üstte
  olan belgeler (kanunlar) öne alınır.
- "Otomatik yorum" **kural tabanlıdır**: madde metninde istisna, muafiyet,
  ceza, oran, had/tutar, süre, tevkifat, zamanaşımı, pişmanlık, uzlaşma gibi
  kavramlar tespit edilirse ilgili kontrol uyarısı ve belgenin hiyerarşideki
  yerine dair not eklenir.

## Önemli uyarı

Bu araç bir **yardımcı bulma/tarama aracıdır**; hukuki görüş vermez.
Otomatik yorumlar kural tabanlı hatırlatmalardır. Resmî işlemlerde daima
mevzuatın güncel resmî metnini (mevzuat.gov.tr, Resmî Gazete) esas alınız.

## Komut satırı seçenekleri

```
python3 mevzuat_asistani.py --port 8765     # farklı port
python3 mevzuat_asistani.py --no-browser    # tarayıcıyı otomatik açma
```
