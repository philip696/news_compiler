// Minimal API client for WeWe-RSS platform (TypeScript, Node.js)
// This file provides functions to:
// - Get WeChat login QR
// - Verify login status
// - Get articles from PLATFORM_URL
// - Get accounts list

import axios, { AxiosInstance } from 'axios';

const PLATFORM_URL = process.env.PLATFORM_URL || 'https://weread.111965.xyz';

export class WeWeRSSApi {
  private client: AxiosInstance;
  private xid: string | undefined;
  private token: string | undefined;

  constructor(xid?: string, token?: string) {
    this.client = axios.create({ baseURL: PLATFORM_URL, timeout: 15000 });
    this.xid = xid;
    this.token = token;
  }

  setAuth(xid: string, token: string) {
    this.xid = xid;
    this.token = token;
  }

  async createLoginUrl() {
    const res = await this.client.get('/api/v2/login/platform');
    return res.data as { uuid: string; scanUrl: string };
  }

  async getLoginResult(uuid: string) {
    const res = await this.client.get(`/api/v2/login/platform/${uuid}`, { timeout: 120000 });
    return res.data as { message: string; vid?: number; token?: string; username?: string };
  }

  async getMpArticles(mpId: string, page = 1) {
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
    const res = await this.client.get('/trpc/account.list', {
      headers: {
        xid: this.xid,
        Authorization: `Bearer ${this.token}`,
      },
      params: {
        input: JSON.stringify({ limit: 100 }),
      },
    });
    return res.data;
  }
}

// Usage example (in test/wechat.ts):
// import { WeWeRSSApi } from './wechat-api';
// const api = new WeWeRSSApi();
// const { uuid, scanUrl } = await api.createLoginUrl();
// ...