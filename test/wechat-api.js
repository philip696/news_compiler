const axios = require('axios');

const PLATFORM_URL = process.env.PLATFORM_URL || 'https://weread.111965.xyz';

class WeWeRSSApi {
  constructor(xid, token) {
    this.client = axios.create({ baseURL: PLATFORM_URL, timeout: 15000 });
    this.xid = xid;
    this.token = token;
  }

  setAuth(xid, token) {
    this.xid = xid;
    this.token = token;
  }

  async createLoginUrl() {
    const res = await this.client.get('/api/v2/login/platform');
    return res.data;
  }

  async getLoginResult(uuid) {
    const res = await this.client.get(`/api/v2/login/platform/${uuid}`, { timeout: 120000 });
    return res.data;
  }

  async getMpArticles(mpId, page = 1) {
    if (!this.xid || !this.token) throw new Error('Auth required');
    const res = await this.client.get(`/api/v2/platform/mps/${mpId}/articles`, {
      headers: {
        xid: this.xid,
        Authorization: `Bearer ${this.token}`,
      },
      params: { page },
    });
    return res.data;
  }

  async getAccounts() {
    if (!this.xid || !this.token) throw new Error('Auth required');
    // tRPC expects POST with JSON body { input: { ... } }
    const res = await this.client.post('/trpc/account.list', {
      input: { limit: 100 },
    }, {
      headers: {
        xid: this.xid,
        Authorization: `Bearer ${this.token}`,
      },
    });
    // tRPC response shape: { result: { data: { items: [...] } } }
    return res.data.result?.data?.items || [];
  }
}

module.exports = { WeWeRSSApi };
