const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, '..', 'data');
const USERS_FILE = path.join(DATA_DIR, 'kullanicilar.json');
const SESSIONS_FILE = path.join(DATA_DIR, 'oturumlar.json');

function readJson(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf-8'));
  } catch {
    return fallback;
  }
}

function writeJson(file, data) {
  const tmp = file + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(data, null, 2));
  fs.renameSync(tmp, file);
}

const store = {
  users: readJson(USERS_FILE, { kullanicilar: {} }),
  sessions: readJson(SESSIONS_FILE, { oturumlar: {} }),

  saveUsers() { writeJson(USERS_FILE, this.users); },
  saveSessions() { writeJson(SESSIONS_FILE, this.sessions); },

  getUser(email) { return this.users.kullanicilar[email] || null; },
  setUser(email, user) { this.users.kullanicilar[email] = user; this.saveUsers(); },

  createSession(token, email) {
    this.sessions.oturumlar[token] = { email, olusturma: Date.now() };
    this.saveSessions();
  },
  getSession(token) {
    const s = this.sessions.oturumlar[token];
    if (!s) return null;
    // 30 gün geçerlilik
    if (Date.now() - s.olusturma > 30 * 24 * 3600 * 1000) {
      delete this.sessions.oturumlar[token];
      this.saveSessions();
      return null;
    }
    return s;
  },
  deleteSession(token) {
    delete this.sessions.oturumlar[token];
    this.saveSessions();
  }
};

module.exports = store;
