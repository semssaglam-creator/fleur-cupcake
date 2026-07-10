# Mevzuat Kaynak Metinleri

`adaptif-soru-uretimi` skill'i soruları bu klasördeki metinlerden üretir.
Kaynak metin olmadan soru üretilmez.

## Dosya kuralı

- Her kanun tek dosya: `<kanun-no>.md` (ör. `6183.md`, `213.md`).
- Metnin **güncel (mükerrer maddeler dâhil) tam halini** kullanın —
  https://www.mevzuat.gov.tr üzerinden güncel metne ulaşabilirsiniz.
- Madde numaraları metinde açıkça yer almalı ("Madde 55 –" gibi); skill soruları
  madde dayanağıyla açıklar.
- Metni güncellediğinizde dosyanın başına güncelleme tarihini not düşün
  (ör. `> Güncelleme: 2026-07-10`).

## Yeni kanun ekleme

1. `mevzuat/<kanun-no>.md` dosyasını oluşturun.
2. `data/<kanun-no>/` klasörü ve konu haritası skill tarafından ilk kullanımda
   otomatik oluşturulur (isterseniz `data/6183/konu-haritasi.md` örnek alınabilir).
