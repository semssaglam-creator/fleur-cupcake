# Veri Şemaları

Tüm dosyalar `data/<kanun-no>/` altında tutulur ve her cevaptan sonra güncellenir.

## performans.json

```json
{
  "kanun": "6183",
  "olusturma": "2026-07-10",
  "oturum_sayisi": 3,
  "genel": {
    "toplam_soru": 42,
    "dogru": 29,
    "yanlis": 13
  },
  "konular": {
    "odeme-emri": {
      "seviye": 3,
      "toplam": 8,
      "dogru": 6,
      "son5": [1, 1, 0, 1, 1],
      "son_oturum": 3
    },
    "tecil": {
      "seviye": 1,
      "toplam": 5,
      "dogru": 1,
      "son5": [0, 0, 1, 0, 0],
      "son_oturum": 2
    }
  }
}
```

- `son5`: son 5 cevabın sonucu (1 = doğru, 0 = yanlış), en yenisi sonda.
- `seviye`: konunun güncel zorluk seviyesi (1–4, bkz. adaptasyon.md).
- Konu anahtarları `konu-haritasi.md` dosyasındaki kebab-case kimliklerdir.

## sorulan-sorular.json

```json
{
  "sorular": [
    {
      "id": 1,
      "oturum": 3,
      "tarih": "2026-07-10",
      "konu": "odeme-emri",
      "madde": "55",
      "format": "coktan-secmeli",
      "seviye": 3,
      "ozet": "Ödeme emrinde bulunması zorunlu unsurlar",
      "sonuc": "dogru"
    }
  ]
}
```

- `ozet`: sorunun neyi hedeflediğinin tek cümlelik özeti — tekrar kontrolü buradan
  yapılır, soru metninin tamamını saklamaya gerek yok.
- `sonuc`: `dogru` | `yanlis` | `bos` (kullanıcı geçtiyse).
