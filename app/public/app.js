// Basit SPA durum yönetimi
const $ = id => document.getElementById(id);

const KONU_ADLARI = {
  'kapsam-tanimlar': 'Kapsam ve Tanımlar',
  'teminat': 'Teminat',
  'ihtiyati-haciz': 'İhtiyati Haciz',
  'ihtiyati-tahakkuk': 'İhtiyati Tahakkuk',
  'korunma-hukumleri': 'Korunma Hükümleri',
  'odeme': 'Ödeme',
  'tecil-gecikme-zammi': 'Tecil ve Gecikme Zammı',
  'cebren-tahsil': 'Cebren Tahsil',
  'odeme-emri': 'Ödeme Emri',
  'mal-bildirimi': 'Mal Bildirimi',
  'haciz': 'Haciz',
  'zamanasimi': 'Zamanaşımı',
  'terkin': 'Terkin'
};

let aktifSoru = null;

async function api(yol, govde) {
  const secenek = govde
    ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(govde) }
    : {};
  const r = await fetch(yol, secenek);
  const veri = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(veri.hata || 'Bir hata oluştu.');
  return veri;
}

function ekranGoster(ad) {
  for (const e of ['ekran-auth', 'ekran-panel', 'ekran-soru']) {
    $(e).classList.toggle('gizli', e !== ad);
  }
}

// --- auth ---

$('sekme-giris').onclick = () => sekme(true);
$('sekme-kayit').onclick = () => sekme(false);
function sekme(giris) {
  $('sekme-giris').classList.toggle('aktif', giris);
  $('sekme-kayit').classList.toggle('aktif', !giris);
  $('form-giris').classList.toggle('gizli', !giris);
  $('form-kayit').classList.toggle('gizli', giris);
  mesaj('');
}

function mesaj(metin, tip) {
  const m = $('auth-mesaj');
  m.textContent = metin;
  m.className = 'mesaj' + (tip ? ' ' + tip : '');
}

$('form-kayit').onsubmit = async e => {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    await api('/api/kayit', { ad: f.get('ad'), email: f.get('email'), sifre: f.get('sifre') });
    mesaj('Üyelik oluşturuldu, giriş yapabilirsiniz.', 'tamam');
    sekme(true);
  } catch (err) { mesaj(err.message, 'hata'); }
};

$('form-giris').onsubmit = async e => {
  e.preventDefault();
  const f = new FormData(e.target);
  try {
    await api('/api/giris', { email: f.get('email'), sifre: f.get('sifre') });
    await panelYukle();
  } catch (err) { mesaj(err.message, 'hata'); }
};

$('btn-cikis').onclick = async () => {
  try { await api('/api/cikis', {}); } catch {}
  $('kullanici-alani').classList.add('gizli');
  ekranGoster('ekran-auth');
};

// --- panel ---

async function panelYukle() {
  const ben = await api('/api/ben');
  $('kullanici-ad').textContent = ben.ad;
  $('kullanici-alani').classList.remove('gizli');
  $('panel-selam').textContent = `Merhaba, ${ben.ad}`;
  $('istat-toplam').textContent = ben.toplam;
  $('istat-dogru').textContent = ben.dogru;
  $('istat-oran').textContent = ben.toplam ? Math.round(100 * ben.dogru / ben.toplam) + '%' : '–';

  const liste = $('konu-listesi');
  liste.innerHTML = '';
  const konular = Object.entries(ben.konular);
  if (konular.length === 0) {
    liste.innerHTML = '<p class="ipucu">Henüz soru çözülmedi. İlk sorularla seviye tespiti yapılır.</p>';
  }
  for (const [konu, d] of konular.sort((a, b) => (a[1].dogru / a[1].toplam) - (b[1].dogru / b[1].toplam))) {
    const oran = d.toplam ? Math.round(100 * d.dogru / d.toplam) : 0;
    const satir = document.createElement('div');
    satir.className = 'konu-satir';
    satir.innerHTML = `
      <span class="ad">${KONU_ADLARI[konu] || konu}</span>
      <span class="cubuk"><i style="width:${oran}%"></i></span>
      <span class="sev">%${oran} · sev. ${d.seviye}</span>`;
    liste.appendChild(satir);
  }
  ekranGoster('ekran-panel');
}

// --- soru ---

$('btn-basla').onclick = soruYukle;
$('btn-sonraki').onclick = soruYukle;
$('btn-panel').onclick = panelYukle;

async function soruYukle() {
  aktifSoru = await api('/api/soru');
  $('soru-konu').textContent = KONU_ADLARI[aktifSoru.konu] || aktifSoru.konu;
  $('soru-seviye').textContent = 'Seviye ' + aktifSoru.seviye;
  $('soru-metin').textContent = aktifSoru.soru;
  $('sonuc').className = 'sonuc gizli';
  $('btn-sonraki').classList.add('gizli');

  const kutu = $('secenekler');
  kutu.innerHTML = '';
  aktifSoru.secenekler.forEach((metin, i) => {
    const b = document.createElement('button');
    b.className = 'secenek';
    b.innerHTML = `<span class="harf">${String.fromCharCode(65 + i)})</span>${metin}`;
    b.onclick = () => cevapla(i);
    kutu.appendChild(b);
  });
  ekranGoster('ekran-soru');
}

async function cevapla(i) {
  const sonuc = await api('/api/cevap', { soruId: aktifSoru.id, cevap: i });
  const butonlar = [...$('secenekler').children];
  butonlar.forEach(b => b.disabled = true);
  butonlar[sonuc.dogru].classList.add('dogru');
  if (!sonuc.dogruMu) butonlar[i].classList.add('yanlis');

  const s = $('sonuc');
  s.className = 'sonuc ' + (sonuc.dogruMu ? 'dogru' : 'yanlis');
  $('sonuc-baslik').textContent = sonuc.dogruMu ? '✅ Doğru!' : '❌ Yanlış';
  $('sonuc-aciklama').textContent = sonuc.aciklama;
  $('btn-sonraki').classList.remove('gizli');
}

// Açılışta oturum kontrolü
(async () => {
  try { await panelYukle(); }
  catch { ekranGoster('ekran-auth'); }
})();
