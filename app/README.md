# Fleur Cupcake — Adaptif Mevzuat Çalışma Uygulaması

6183 sayılı Kanun'dan adaptif sınav soruları sunan, üyelik sistemli web uygulaması.
Telefon, tablet ve bilgisayarla uyumludur (mobil öncelikli duyarlı tasarım).

## Çalıştırma

```bash
cd app
npm install
npm start          # http://localhost:3000
```

Node.js 18+ gerektirir. Farklı port için: `PORT=8080 npm start`

## Özellikler

- **Üyelik**: E-posta + şifre ile kayıt ve giriş. Şifreler scrypt ile hash'lenir,
  oturumlar HttpOnly çerezle 30 gün tutulur.
- **Adaptif motor** (`lib/adaptive.js`): Skill'deki `adaptasyon.md` kurallarının
  uygulamaya taşınmış hali — konu bazlı seviye (1–4), son 5 cevaba göre seviye
  ayarı, üst üste 3 doğru = seviye artışı / 2 yanlış = düşüş, zayıf ve hiç
  görülmemiş konulara ağırlıklı soru seçimi, yanlış yapılan soruların en az
  5 soru sonra tekrar sorulması.
- **Soru bankası** (`data/soru-bankasi.json`): `mevzuat/6183.md` metnine dayalı
  48 soru; her soruda konu etiketi, madde dayanağı, seviye ve açıklama bulunur.
  Doğru cevap ve açıklama istemciye soru cevaplanmadan gönderilmez.
- **Panel**: Toplam/doğru/başarı istatistikleri ve konu bazlı ilerleme çubukları.

## Veri dosyaları

- `data/soru-bankasi.json` — soru bankası (depoya dahil)
- `data/kullanicilar.json` — üyeler ve performans geçmişi (gitignore'da; sunucuda oluşur)
- `data/oturumlar.json` — aktif oturumlar (gitignore'da)

## Soru bankasını genişletme

Yeni soru eklerken `CLAUDE.md` kuralları geçerlidir: madde metni yalnızca
`mevzuat/` klasöründen okunur, konu etiketleri `data/6183/konu-haritasi.md`
kimlikleriyle aynı olmalıdır. `adaptif-soru-uretimi` skill'i ile üretilen
sorular bu bankaya aynı şemayla aktarılabilir.

## Yayına alma notu

Uygulama tek Node.js süreci + JSON dosyası ile çalışır; küçük kullanıcı grupları
için yeterlidir. İnternete açarken HTTPS arkasında çalıştırın (ör. bir reverse
proxy ile) ve `Set-Cookie` satırına `Secure` bayrağını ekleyin.
