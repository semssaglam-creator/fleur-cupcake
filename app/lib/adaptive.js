// Adaptif soru seçimi — .claude/skills/adaptif-soru-uretimi/references/adaptasyon.md
// içindeki kuralların uygulamaya taşınmış hali. Çok kanunlu: sorular kanun bazında
// ayrı çalışılabilir veya "karisik" modda tüm kanunlardan gelir; performans
// "kanun/konu" anahtarıyla her kanun için ayrı izlenir.

const bank = require('../data/soru-bankasi.json');

const KANUNLAR = bank.kanunlar; // { "6183": "Amme Alacaklarının..." }

function konuAnahtari(soru) {
  return soru.kanun + '/' + soru.konu;
}

function bosKonu() {
  return { seviye: 2, toplam: 0, dogru: 0, son5: [] };
}

// Son 5 cevaba ve serilere göre konu seviyesini ayarla (1-4).
function seviyeGuncelle(k) {
  const son5 = k.son5;
  if (son5.length >= 3 && son5.slice(-3).every(x => x === 1)) {
    k.seviye = Math.min(4, k.seviye + 1);
    return;
  }
  if (son5.length >= 2 && son5.slice(-2).every(x => x === 0)) {
    k.seviye = Math.max(1, k.seviye - 1);
    return;
  }
  if (son5.length >= 5) {
    const oran = son5.reduce((a, b) => a + b, 0) / son5.length;
    if (oran >= 0.8) k.seviye = Math.min(4, k.seviye + 1);
    else if (oran < 0.4) k.seviye = Math.max(1, k.seviye - 1);
  }
}

// Konu ağırlığı: zayıf ve hiç görülmemiş konular öne çıkar.
function konuAgirligi(k) {
  const oran = k.toplam > 0 ? k.dogru / k.toplam : 0;
  const hicSorulmadi = k.toplam === 0 ? 1 : 0;
  return (1 - oran) * 2 + hicSorulmadi;
}

function agirlikliSec(items, weightFn) {
  const toplam = items.reduce((a, it) => a + weightFn(it), 0);
  let r = Math.random() * toplam;
  for (const it of items) {
    r -= weightFn(it);
    if (r <= 0) return it;
  }
  return items[items.length - 1];
}

// Kullanıcı için sıradaki soruyu seç.
// kanun: "6183" gibi bir kanun no veya "karisik" (tüm kanunlar).
// perf: { konular: { "kanun/konu": {seviye,toplam,dogru,son5} },
//         cevaplar: [{soruId,kanun,konu,sonuc,sira}] }
function soruSec(perf, kanun) {
  const kanunSorulari = kanun === 'karisik'
    ? bank.sorular
    : bank.sorular.filter(s => s.kanun === kanun);
  if (kanunSorulari.length === 0) return null;

  const cevaplanan = new Map(perf.cevaplar.map(c => [c.soruId, c]));
  const sira = perf.cevaplar.length;

  // Havuz: önce hiç sorulmamışlar; yanlış yapılıp üzerinden en az 5 soru
  // geçmiş olanlar tekrar sorulabilir. Havuz boşalırsa tümü açılır.
  const uygunSorular = kanunSorulari.filter(s => {
    const c = cevaplanan.get(s.id);
    if (!c) return true;
    if (c.sonuc === 'yanlis' && sira - c.sira >= 5) return true;
    return false;
  });
  const havuz = uygunSorular.length > 0 ? uygunSorular : kanunSorulari;

  const konuDurum = {};
  for (const s of havuz) {
    const anahtar = konuAnahtari(s);
    if (!konuDurum[anahtar]) {
      konuDurum[anahtar] = perf.konular[anahtar] || bosKonu();
    }
  }

  // Aynı konudan üst üste en fazla 3 soru.
  const sonUc = perf.cevaplar.slice(-3).map(c => c.kanun + '/' + c.konu);
  let anahtarlar = Object.keys(konuDurum).filter(a =>
    !(sonUc.length === 3 && sonUc.every(k => k === a))
  );
  if (anahtarlar.length === 0) anahtarlar = Object.keys(konuDurum);

  const secilenAnahtar = agirlikliSec(anahtarlar, a => konuAgirligi(konuDurum[a]));
  const hedefSeviye = konuDurum[secilenAnahtar].seviye;

  // Konu içinde hedef seviyeye en yakın soruyu seç; eşitlikte rastgele.
  const konuSorulari = havuz.filter(s => konuAnahtari(s) === secilenAnahtar);
  const enYakin = Math.min(...konuSorulari.map(s => Math.abs(s.seviye - hedefSeviye)));
  const adaylar = konuSorulari.filter(s => Math.abs(s.seviye - hedefSeviye) === enYakin);
  return adaylar[Math.floor(Math.random() * adaylar.length)];
}

// Cevabı işle: performansı güncelle, sonucu döndür.
function cevapIsle(perf, soru, secilenIndex) {
  const dogruMu = secilenIndex === soru.dogru;
  const anahtar = konuAnahtari(soru);
  const k = perf.konular[anahtar] || (perf.konular[anahtar] = bosKonu());
  k.toplam += 1;
  if (dogruMu) k.dogru += 1;
  k.son5.push(dogruMu ? 1 : 0);
  if (k.son5.length > 5) k.son5.shift();
  seviyeGuncelle(k);
  perf.cevaplar.push({
    soruId: soru.id,
    kanun: soru.kanun,
    konu: soru.konu,
    sonuc: dogruMu ? 'dogru' : 'yanlis',
    sira: perf.cevaplar.length,
    tarih: new Date().toISOString().slice(0, 10)
  });
  return dogruMu;
}

function soruBul(id) {
  return bank.sorular.find(s => s.id === id) || null;
}

module.exports = { soruSec, cevapIsle, soruBul, KANUNLAR };
