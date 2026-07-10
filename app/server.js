const express = require('express');
const crypto = require('crypto');
const path = require('path');
const store = require('./lib/store');
const { soruSec, cevapIsle, soruBul, KANUNLAR } = require('./lib/adaptive');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// --- yardımcılar ---

function hashSifre(sifre, salt) {
  return crypto.scryptSync(sifre, salt, 64).toString('hex');
}

function tokenOku(req) {
  const h = req.headers.cookie || '';
  const m = h.match(/(?:^|;\s*)oturum=([a-f0-9]{48})/);
  return m ? m[1] : null;
}

function girisliKullanici(req) {
  const token = tokenOku(req);
  if (!token) return null;
  const s = store.getSession(token);
  if (!s) return null;
  const user = store.getUser(s.email);
  return user ? { email: s.email, user, token } : null;
}

function yetkiGerekli(req, res, next) {
  const g = girisliKullanici(req);
  if (!g) return res.status(401).json({ hata: 'Giriş yapmanız gerekiyor.' });
  req.giris = g;
  next();
}

// --- üyelik ---

app.post('/api/kayit', (req, res) => {
  const { ad, email, sifre } = req.body || {};
  if (!ad || !email || !sifre) return res.status(400).json({ hata: 'Ad, e-posta ve şifre zorunludur.' });
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return res.status(400).json({ hata: 'Geçerli bir e-posta girin.' });
  if (sifre.length < 8) return res.status(400).json({ hata: 'Şifre en az 8 karakter olmalıdır.' });
  const e = email.toLowerCase().trim();
  if (store.getUser(e)) return res.status(409).json({ hata: 'Bu e-posta ile zaten bir üyelik var.' });

  const salt = crypto.randomBytes(16).toString('hex');
  store.setUser(e, {
    ad: ad.trim(),
    salt,
    hash: hashSifre(sifre, salt),
    olusturma: new Date().toISOString().slice(0, 10),
    performans: { konular: {}, cevaplar: [] }
  });
  res.json({ tamam: true });
});

app.post('/api/giris', (req, res) => {
  const { email, sifre } = req.body || {};
  const e = (email || '').toLowerCase().trim();
  const user = store.getUser(e);
  if (!user || hashSifre(sifre || '', user.salt) !== user.hash) {
    return res.status(401).json({ hata: 'E-posta veya şifre hatalı.' });
  }
  const token = crypto.randomBytes(24).toString('hex');
  store.createSession(token, e);
  res.setHeader('Set-Cookie', `oturum=${token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${30 * 24 * 3600}`);
  res.json({ tamam: true, ad: user.ad });
});

app.post('/api/cikis', yetkiGerekli, (req, res) => {
  store.deleteSession(req.giris.token);
  res.setHeader('Set-Cookie', 'oturum=; Path=/; HttpOnly; Max-Age=0');
  res.json({ tamam: true });
});

app.get('/api/ben', yetkiGerekli, (req, res) => {
  const { user, email } = req.giris;
  const p = user.performans;
  const toplam = p.cevaplar.length;
  const dogru = p.cevaplar.filter(c => c.sonuc === 'dogru').length;
  res.json({ ad: user.ad, email, toplam, dogru, konular: p.konular });
});

// --- quiz ---

app.get('/api/kanunlar', yetkiGerekli, (req, res) => {
  res.json({ kanunlar: KANUNLAR });
});

// --- simülasyon ---

const simulasyonlar = require('./data/simulasyon.json');

app.get('/api/simulasyon', yetkiGerekli, (req, res) => {
  res.json({ kanunlar: Object.keys(simulasyonlar) });
});

app.get('/api/simulasyon/:kanun', yetkiGerekli, (req, res) => {
  const sim = simulasyonlar[req.params.kanun];
  if (!sim) return res.status(404).json({ hata: 'Bu kanun için simülasyon yok.' });
  res.json(sim);
});

app.get('/api/soru', yetkiGerekli, (req, res) => {
  const kanun = req.query.kanun || Object.keys(KANUNLAR)[0];
  if (kanun !== 'karisik' && !KANUNLAR[kanun]) {
    return res.status(400).json({ hata: 'Geçersiz kanun seçimi.' });
  }
  const soru = soruSec(req.giris.user.performans, kanun);
  if (!soru) return res.status(404).json({ hata: 'Uygun soru bulunamadı.' });
  // Doğru cevap ve açıklama istemciye gönderilmez.
  const { dogru, aciklama, ...acik } = soru;
  res.json(acik);
});

app.post('/api/cevap', yetkiGerekli, (req, res) => {
  const { soruId, cevap } = req.body || {};
  const soru = soruBul(soruId);
  if (!soru || !Number.isInteger(cevap) || cevap < 0 || cevap >= soru.secenekler.length) {
    return res.status(400).json({ hata: 'Geçersiz cevap.' });
  }
  const { user, email } = req.giris;
  const dogruMu = cevapIsle(user.performans, soru, cevap);
  store.setUser(email, user);
  res.json({
    dogruMu,
    dogru: soru.dogru,
    aciklama: soru.aciklama,
    madde: soru.madde,
    konuDurum: user.performans.konular[soru.konu]
  });
});

app.listen(PORT, () => {
  console.log(`fleur-cupcake quiz uygulaması: http://localhost:${PORT}`);
});
