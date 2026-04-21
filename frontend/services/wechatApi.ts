import { api } from "./api";

/** Pool account (GET /api/wechat/accounts) or MP feed row (GET /api/wechat/mps) — UI may use either shape. */
export interface WeChatAccount {
  id: string;
  name?: string | null;
  status?: number;
  blockedToday?: boolean;
  mpName?: string;
  mpCover?: string;
  mpIntro?: string;
  updateTime?: number;
  syncTime?: number;
  articleCount?: number;
  is_muted?: boolean;
  wechat_account_id?: string;
  wechat_account_name?: string;
  wechat_account_avatar?: string;
  last_sync_time?: string;
  created_at?: string;
  updated_at?: string;
}

export interface AddWeChatAccountRequest {
  wechat_account_id: string;
}

export interface WeChatAccountsResponse {
  accounts: WeChatAccount[];
  total: number;
}

/**
 * Subscribed Official Accounts (MP feeds) — matches GET /api/wechat/mps.
 */
export async function getWeChatAccounts(): Promise<WeChatAccount[]> {
  const response = await api.get<WeChatAccount[]>("/api/wechat/mps");
  return Array.isArray(response.data) ? response.data : [];
}

/**
 * Add an Official Account: wxs article URL, or raw mp id (POST /mps or /mps/by-id).
 */
export async function addWeChatAccount(input: string): Promise<unknown> {
  const s = input.trim();
  if (!s) {
    throw new Error("empty input");
  }
  if (s.startsWith("https://mp.weixin.qq.com/s/")) {
    const response = await api.post("/api/wechat/mps", { wxsLink: s });
    return response.data;
  }
  const response = await api.post("/api/wechat/mps/by-id", {
    mpId: s,
    name: s,
  });
  return response.data;
}

export function validateWeChatAccountId(accountId: string): boolean {
  const t = accountId.trim();
  if (t.startsWith("https://mp.weixin.qq.com/s/")) {
    return true;
  }
  return /^[a-zA-Z0-9_-]{4,}$/.test(t);
}

/** Remove a subscribed MP feed */
export async function removeWeChatAccount(mpId: string): Promise<void> {
  await api.delete(`/api/wechat/mps/${encodeURIComponent(mpId)}`);
}

/** Refresh latest articles for an MP */
export async function updateWeChatAccount(mpId: string): Promise<unknown> {
  const response = await api.post(
    `/api/wechat/mps/${encodeURIComponent(mpId)}/sync`
  );
  return response.data;
}

/** No mute API on backend — kept for UI compatibility */
export async function muteAccount(id: string): Promise<WeChatAccount> {
  console.warn("muteAccount: not supported by API", id);
  return { id, is_muted: true };
}

export async function unmuteAccount(id: string): Promise<WeChatAccount> {
  console.warn("unmuteAccount: not supported by API", id);
  return { id, is_muted: false };
}

// --- WeChat OAuth (dashboard / wechat_login.py) ---

export interface WeChatLoginResponse {
  status: string;
  state: string;
  auth_url: string;
  expires_in: number;
  message?: string;
  error?: string;
}

export interface WeChatOAuthCallback {
  status: string;
  user: {
    openid: string;
    nickname?: string;
    avatar?: string;
  };
  access_token: string;
}

export interface WeChatLoginStatusResponse {
  status: "pending" | "completed" | "expired" | "error";
  message?: string;
  user?: {
    openid: string;
    nickname?: string;
    avatar?: string;
  };
  access_token?: string;
}

export async function generateWeChatQRCode(): Promise<WeChatLoginResponse> {
  const response = await api.post<WeChatLoginResponse>(
    "/api/wechat-auth/qrcode/generate"
  );
  return response.data;
}

export async function checkWeChatLoginStatus(
  state: string
): Promise<WeChatLoginStatusResponse> {
  const response = await api.get<WeChatLoginStatusResponse>(
    "/api/wechat-auth/status",
    { params: { state } }
  );
  return response.data;
}

export async function handleWeChatCallback(
  code: string,
  state: string
): Promise<WeChatOAuthCallback> {
  const response = await api.post<WeChatOAuthCallback>(
    `/api/wechat-auth/callback?${new URLSearchParams({ code, state }).toString()}`
  );
  return response.data;
}
