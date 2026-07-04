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
- 📌 **Uygulama zinciri (ters atıf)** — bir kanun maddesini açtığınızda
  altında **"Bu maddeye atıf yapan düzenlemeler"** listesi görünür: o maddenin
  uygulamasını açıklayan tebliğ bölümleri, sirkülerler ve özelgeler tek
  tıkla önünüzdedir. "Kanun maddesini buldum, uygulaması hangi tebliğde?"
  sorusunun doğrudan cevabıdır.
- ⚠ **Değişiklik tespiti** — değiştirici tebliğlerdeki *"…Tebliğinin (2.1.)
  bölümü aşağıdaki şekilde değiştirilmiştir"*, *"yürürlükten kaldırılmıştır"*
  gibi kalıplar tanınır; **değiştirilen eski bölümün üzerine kırmızı uyarı**
  iliştirilir ve değiştiren düzenlemeye bağlantı verilir. Böylece farkında
  olmadan güncelliğini yitirmiş bir tebliğ bölümüne dayanma riski azalır.
  Uyum kontrolünde de sonuçlar arasında değiştirilmiş bölüm varsa kontrol
  listesinin başına uyarı eklenir. Resmî Gazete tarihi ve Seri No
  ayrıştırılıp "Yüklü Mevzuat" tablosunda gösterilir.
- 🔗 **Çapraz atıf takibi** — madde metnindeki "bu Kanunun 3 üncü maddesi",
  "213 sayılı Vergi Usul Kanununun 344 üncü maddesi", "mükerrer 355 inci
  maddesi" gibi atıflar otomatik tanınır ve **tıklanabilir bağlantıya**
  dönüşür; tıklayınca atıf yapılan madde açılır, "← Geri" ile dönersiniz.
  Atıf yapılan kanun yüklü değilse atıf noktalı çizgiyle işaretlenir.
- ⭐ **Kayıtlı aramalar** — sık kullandığınız konu aramalarını ve işlem
  tariflerini ⭐ Kaydet ile saklarsınız; arama kutusunun altında çip olarak
  görünür, tıklayınca yeniden çalışır. Kayıtlar uygulamanın yanındaki
  `kayitli_aramalar.json` dosyasında tutulur (yedeklenebilir).
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
- Çapraz atıflarda hedef belge, atıf bağlamındaki kanun numarası
  ("213 sayılı"), kısaltma (VUK, GVK, KVK, KDV, ÖTV, AATUHK…) veya ad
  parçasından bulunur; "bu Kanunun X inci maddesi" aynı belgeye bağlanır.
  Bir tebliğin içindeki "Kanunun X inci maddesi" atfı, tebliğle aynı konuyu
  paylaşan kanuna (örn. KDV tebliği → KDV Kanunu) yönlendirilir. Bu yüzden
  ilgili kanunları da yüklemeniz atıf takibini güçlendirir.

## Önemli uyarı

Değişiklik tespiti kalıp tabanlıdır: standart dışı ifadeyle yapılan veya
bölüm numarası verilmeden yapılan değişiklikler yakalanamayabilir. En sağlam
yöntem, tebliğlerin mevzuat.gov.tr / GİB'deki **işlenmiş (birleşik) güncel
metinlerini** yüklemek, değiştirici tebliğleri ise tarihçe izlemek
istediğinizde eklemektir — uygulama iki durumda da çalışır.

Bu araç bir **yardımcı bulma/tarama aracıdır**; hukuki görüş vermez.
Otomatik yorumlar kural tabanlı hatırlatmalardır. Resmî işlemlerde daima
mevzuatın güncel resmî metnini (mevzuat.gov.tr, Resmî Gazete) esas alınız.

## Komut satırı seçenekleri

```
python3 mevzuat_asistani.py --port 8765     # farklı port
python3 mevzuat_asistani.py --no-browser    # tarayıcıyı otomatik açma
```
