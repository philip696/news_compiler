// Mini simulation of the full WeRead QR login → token → DB → fetch → parse → store → frontend read flow
// This is a simplified, in-memory version for demonstration/testing

interface Account {
  id: string;
  token: string;
  name: string;
  status: 'ENABLE' | 'INVALID';
}

interface Article {
  id: string;
  mpId: string;
  title: string;
  content: string;
}

// In-memory DB
const db = {
  accounts: [] as Account[],
  articles: [] as Article[],
};

// (A) Simulate QR login and get token
function simulateQrLogin(): { uuid: string; scanUrl: string } {
  return { uuid: 'uuid-123', scanUrl: 'https://fake-qr-url/uuid-123' };
}

function simulateGetLoginResult(uuid: string) {
  // Always succeed for demo
  return {
    message: 'success',
    vid: 'acc-1',
    token: 'session-token-abc',
    username: 'TestUser',
  };
}

// (B) Store token in DB
function upsertAccount({ id, token, name, status }: Account) {
  const idx = db.accounts.findIndex((a) => a.id === id);
  if (idx >= 0) {
    db.accounts[idx] = { id, token, name, status };
  } else {
    db.accounts.push({ id, token, name, status });
  }
}

// (C) Use token to fetch articles (simulate HTTP call)
function fetchArticlesWithToken(mpId: string, token: string): Article[] {
  // Simulate HTTP call using token
  if (token !== 'session-token-abc') throw new Error('Invalid token');
  // Simulate response
  return [
    { id: 'art-1', mpId, title: 'Article 1', content: 'Content 1' },
    { id: 'art-2', mpId, title: 'Article 2', content: 'Content 2' },
  ];
}

// (D) Store articles in DB
function storeArticles(articles: Article[]) {
  for (const art of articles) {
    const idx = db.articles.findIndex((a) => a.id === art.id);
    if (idx >= 0) db.articles[idx] = art;
    else db.articles.push(art);
  }
}

// (E) Read from DB (simulate frontend read)
function listArticles(mpId: string) {
  return db.articles.filter((a) => a.mpId === mpId);
}

// --- Simulate the full flow ---
console.log('Step A: QR login');
const qr = simulateQrLogin();
console.log('QR:', qr);

console.log('Step B: Poll login result');
const login = simulateGetLoginResult(qr.uuid);
console.log('Login result:', login);

console.log('Step C: Store account in DB');
upsertAccount({ id: login.vid, token: login.token, name: login.username, status: 'ENABLE' });
console.log('Accounts in DB:', db.accounts);

console.log('Step D: Fetch articles using token');
const articles = fetchArticlesWithToken('mp-123', login.token);
console.log('Fetched articles:', articles);

console.log('Step E: Store articles in DB');
storeArticles(articles);
console.log('Articles in DB:', db.articles);

console.log('Step F: Frontend reads articles');
const frontendArticles = listArticles('mp-123');
console.log('Frontend sees:', frontendArticles);
