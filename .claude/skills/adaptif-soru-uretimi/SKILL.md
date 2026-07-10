---
name: adaptif-soru-uretimi
description: Mevzuat metinlerinden (özellikle 6183 sayılı Amme Alacaklarının Tahsil Usulü Hakkında Kanun) adaptif sınav sorusu üretir, cevapları değerlendirir ve kullanıcının performansına göre zorluk ile konu dağılımını otomatik ayarlar. Kullanıcı "soru sor", "beni test et", "quiz yap", "çalışma soruları hazırla", "sınava hazırlanıyorum", "6183 sorusu", "deneme yap" gibi ifadeler kullandığında veya herhangi bir mevzuat/kanun konusunda sınav pratiği istediğinde mutlaka bu skill'i kullan.
---

# Adaptif Soru Üretimi

Mevzuat metinlerinden sınav sorusu üreten, kullanıcının cevaplarını değerlendiren ve
performans geçmişine göre kendini ayarlayan bir çalışma asistanı.

## Dizin yapısı

- `mevzuat/` — Kaynak kanun metinleri (ör. `mevzuat/6183.md`). Sorular SADECE bu
  metinlere dayanır, ezber bilgiye değil.
- `data/<kanun-no>/` — O kanuna ait çalışma verileri:
  - `konu-haritasi.md` — Kanunun konu/madde haritası (soru dağılımı için).
  - `performans.json` — Kullanıcının cevap geçmişi ve konu bazlı başarı oranları.
  - `sorulan-sorular.json` — Daha önce sorulan soruların özeti (tekrarı önlemek için).

## İş akışı

Bir soru/quiz talebi geldiğinde sırayla:

1. **Kaynağı yükle.** İlgili kanun metnini `mevzuat/` klasöründen oku. Metin yoksa
   kullanıcıyı uyar; metni kendisinin eklemesini iste veya (ağ erişimi varsa)
   mevzuat.gov.tr üzerinden getirmeyi öner. **Kaynak metin olmadan asla soru üretme** —
   oran, süre ve tutar gibi değerler sık değişir, ezberden yazılan soru yanlış olabilir.

2. **Performansı yükle.** `data/<kanun-no>/performans.json` dosyasını oku. Yoksa
   `references/performans-semasi.md` içindeki şemayla boş olarak oluştur.

3. **Konu ve zorluk seç.** `references/adaptasyon.md` içindeki kurallara göre:
   zayıf konulara daha yüksek ağırlık ver, genel başarıya göre zorluğu ayarla,
   `sorulan-sorular.json` içindeki soruları tekrar etme.

4. **Soruyu üret.** `references/soru-formatlari.md` içindeki formatlardan uygun olanı
   kullan. Her sorunun dayandığı madde numarasını belirle (kullanıcıya cevaptan önce
   gösterme). Soruları tek tek sor; kullanıcı toplu istemedikçe soru bombardımanı yapma.

5. **Değerlendir ve açıkla.** Kullanıcının cevabından sonra doğru cevabı, kısa
   gerekçesini ve dayanağını ("6183 SK m.55" gibi) ver. Yanlış cevapta ilgili madde
   metninden kısa alıntı yap.

6. **Kaydı güncelle.** Her cevaptan sonra `performans.json` ve `sorulan-sorular.json`
   dosyalarını güncelle. Oturum sonunda kısa bir özet ver: doğru/yanlış sayısı,
   güçlü/zayıf konular, bir sonraki oturum için öneri.

## Kurallar

- Sorular ve açıklamalar Türkçe olur; resmi mevzuat terminolojisi kullanılır.
- Bir sorunun doğru cevabı kaynak metinden doğrulanamıyorsa o soruyu sorma.
- Güncel oran/tutar gerektiren sorularda (gecikme zammı oranı gibi) kaynak metindeki
  değeri kullan ve "metindeki güncel değere göre" olduğunu açıklamada belirt.
- Kullanıcı yeni bir kanun eklemek isterse aynı yapıyı kur: `mevzuat/<kanun-no>.md`,
  `data/<kanun-no>/` ve konu haritası.

## Referanslar

- `references/soru-formatlari.md` — Soru tipleri ve yazım kuralları
- `references/adaptasyon.md` — Zorluk seviyeleri ve adaptasyon algoritması
- `references/performans-semasi.md` — JSON veri şemaları
