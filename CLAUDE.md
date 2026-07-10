# fleur-cupcake

Mevzuat tabanlı adaptif sınav çalışma deposu. Kaynak metinler `mevzuat/`,
çalışma verileri `data/<kanun-no>/`, soru üretim mantığı
`.claude/skills/adaptif-soru-uretimi/` altındadır.

## Soru Üretim Kuralları

- Soru üretiminde her zaman `adaptif-soru-uretimi` skill'ini kullan.
- Madde metnini YALNIZCA `mevzuat/` klasöründeki dosyalardan oku; dosyada olmayan
  madde için soru üretme, dur ve kullanıcıya sor.
- Her düğüm tamamlandığında dur; kullanıcı denetlemeden sonraki düğüme geçme.
- Mevcut kavram etiketlerini `data/` klasöründen tara (`konu-haritasi.md` ve
  `performans.json` anahtarları); yenisini gerekmedikçe üretme.
- Her oturum sonunda `.claude/skills/adaptif-soru-uretimi/NOTLAR.md` dosyasına
  öğrenilen dersleri işle.
