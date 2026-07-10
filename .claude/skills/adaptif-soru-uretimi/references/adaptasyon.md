# Zorluk Seviyeleri ve Adaptasyon

## Zorluk seviyeleri

| Seviye | Ad | Tanım |
|---|---|---|
| 1 | Hatırlama | Tek hükmün doğrudan sorulması (süre, oran, tanım) |
| 2 | Kavrama | Hükmün farklı ifadeyle sorulması, doğru/yanlış ayrımı |
| 3 | Uygulama | Tek maddelik basit vaka; hükmün olaya uygulanması |
| 4 | Analiz | Birden fazla maddeyi birleştiren vaka; istisnalar, karşılaştırmalar |

## Başlangıç

- Yeni kullanıcı (performans dosyası boş): seviye 2'den başla, ilk 5 soruyu farklı
  konulardan sorarak seviye tespiti yap.
- Mevcut kullanıcı: konu bazlı son durumdan devam et.

## Zorluk ayarlama (konu bazında)

Her konu için son 5 cevabın doğruluk oranına bak:

- **%80 ve üzeri** → o konuda seviyeyi 1 artır (en fazla 4).
- **%40–79** → seviyede kal.
- **%40 altı** → seviyeyi 1 düşür (en az 1) ve o konunun ağırlığını artır.

Üst üste 3 doğru = anlık seviye artışı; üst üste 2 yanlış = anlık seviye düşüşü.
Bu ayarlar sorudan soruya uygulanır, oturum sonunu bekleme.

## Konu seçimi (ağırlıklı)

Her konuya bir ağırlık puanı hesapla:

```
ağırlık = (1 - başarı_oranı) * 2 + hiç_sorulmadıysa_bonus(1) + eskime_bonusu
eskime_bonusu = son sorulmasından bu yana geçen oturum sayısı * 0.2 (en fazla 1)
```

- Soruların ~%60'ı en yüksek ağırlıklı 3 konudan, kalanı diğerlerinden gelsin —
  zayıf konulara yüklen ama güçlü konuları da unutturma (aralıklı tekrar).
- Aynı konudan üst üste en fazla 3 soru sor, sonra konu değiştir.

## Tekrar önleme

- Yeni soruyu üretmeden önce `sorulan-sorular.json` içindeki aynı konu/madde
  kayıtlarına bak; aynı hükmü aynı formatta tekrar sorma.
- Aynı hüküm ancak farklı format + en az 2 oturum arayla tekrar sorulabilir
  (aralıklı tekrar için bu istenen bir davranıştır).
- Kullanıcının yanlış cevapladığı sorular 1-2 oturum sonra farklı ifadeyle
  yeniden sorulmalıdır.

## Oturum özeti

Oturum sonunda raporla:

- Doğru/yanlış sayısı ve oranı (bu oturum + genel)
- Konu bazında durum: yükselen, sabit, düşen
- En zayıf 3 konu ve çalışma önerisi (ilgili madde aralıklarıyla)
