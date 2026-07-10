// Adaptif soru seçimi — .claude/skills/adaptif-soru-uretimi/references/adaptasyon.md
// içindeki kuralların uygulamaya taşınmış hali.

const bank = require('../data/soru-bankasi.json');

const KONULAR = [...new Set(bank.sorular.map(s => s.konu))];

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
// perf: { konular: { konuId: {seviye,toplam,dogru,son5} }, cevaplar: [{soruId,sonuc,sira}] }
function soruSec(perf) {
  const cevaplanan = new Map(perf.cevaplar.map(c => [c.soruId, c]));
  const sira = perf.cevaplar.length;

  // Havuzda sorusu kalan konular: önce hiç sorulmamış, sonra yanlış yapılıp
  // üzerinden en az 5 soru geçmiş olanlar tekrar sorulabilir.
  const uygunSorular = bank.sorular.filter(s => {
    const c = cevaplanan.get(s.id);
    if (!c) return true;
    if (c.sonuc === 'yanlis' && sira - c.sira >= 5) return true;
    return false;
  });
  const havuz = uygunSorular.length > 0 ? uygunSorular : bank.sorular;

  const konuDurum = {};
  for (const konu of KONULAR) {
    if (havuz.some(s => s.konu === konu)) {
      konuDurum[konu] = perf.konular[konu] || bosKonu();
    }
  }

  // Aynı konudan üst üste en fazla 3 soru.
  const sonUc = perf.cevaplar.slice(-3).map(c => c.konu);
  const konular = Object.keys(konuDurum).filter(konu =>
    !(sonUc.length === 3 && sonUc.every(k => k === konu))
  );

  const secilenKonu = agirlikliSec(konular, k => konuAgirligi(konuDurum[k]));
  const hedefSeviye = konuDurum[secilenKonu].seviye;

  // Konu içinde hedef seviyeye en yakın soruyu seç; eşitlikte rastgele.
  const konuSorulari = havuz.filter(s => s.konu === secilenKonu);
  const enYakin = Math.min(...konuSorulari.map(s => Math.abs(s.seviye - hedefSeviye)));
  const adaylar = konuSorulari.filter(s => Math.abs(s.seviye - hedefSeviye) === enYakin);
  return adaylar[Math.floor(Math.random() * adaylar.length)];
}

// Cevabı işle: performansı güncelle, sonucu döndür.
function cevapIsle(perf, soru, secilenIndex) {
  const dogruMu = secilenIndex === soru.dogru;
  const k = perf.konular[soru.konu] || (perf.konular[soru.konu] = bosKonu());
  k.toplam += 1;
  if (dogruMu) k.dogru += 1;
  k.son5.push(dogruMu ? 1 : 0);
  if (k.son5.length > 5) k.son5.shift();
  seviyeGuncelle(k);
  perf.cevaplar.push({
    soruId: soru.id,
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

module.exports = { soruSec, cevapIsle, soruBul, KONULAR };
