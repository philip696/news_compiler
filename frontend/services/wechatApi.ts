import { api } from "./api";

export interface WeChatAccount {
  id: string;
  wechat_account_id: string;
  wechat_account_name: string;
  wechat_account_avatar?: string;
  is_muted: boolean;
  last_sync_time?: string;
  created_at: string;
  updated_at: string;
}

export interface AddWeChatAccountRequest {
  wechat_account_id: string;
}

export interface WeChatAccountsResponse {
  accounts: WeChatAccount[];
  total: number;
}

/**
 * Get all WeChat accounts subscribed by current user
 */
export async function getWeChatAccounts(): Promise<WeChatAccount[]> {
  try {
    const response = await api.get<WeChatAccountsResponse>("/api/wechat/accounts");
    return response.data.accounts || [];
  } catch (error) {
    console.error("Failed to fetch WeChat accounts:", error);
    throw error;
  }
}

/**
 * Add a new WeChat account subscription
 */
export async function addWeChatAccount(
  wechatAccountId: string
): Promise<WeChatAc): Promise<WeChatAc): Promise<WeChatAc): Promise<WeChatAc): Promise<WeChatAc): Promisun): Promise<WeChatAc): Promi_id): Promise<WeChatAc): Promise<Wre):rn response.): Promise<WeChatAc): Pr{
                             add W                             throw                    *                         su                 port                   oveWeCh                             add W     Promise<void> {
  try {
    await api.delete(`/api/wechat/accounts/${subscriptionId}`);
  } catch (error) {
    console.error("Failed to remove WeChat account:", error);
    throw error;
                                                                     syn   uncti                                                                 tAccount> {
  try {
    const response = await api.post<WeCh    const respon  `/    const response = await api.post<WeCh    const respon  `/urn response.data;
  } catch (  } catch (  } catch (  } catch (  }  update WeChat account:", error);
    throw erro    throw erro    the a We    throw erro    throw erro    the a We    throw erro    throw erro    the a We    throw erro    throw erro    the a We    throw erro    throw erro    the a We    throw erro    throw erro    the a We    thrmute`
    );
    return response.data;
  } catch (error) {
    console.error("Failed to mute account:", error);
    throw error;
  }
}

/**
 * Unmute a WeChat account
 */
export async function unmuteAccount(subscriptionId: string): Promise<WeChatAccount> {
  try {
    const response = await api.post<WeChatAccount>(
      `/api/wechat/accounts/${subscriptionId}/unmute`
    );
    return re    return re    return re    return re    return re    return re    return re    return re    return re    return re    return re    return re    return r/
    re function validateWeChatAccountId(accountId: string): boolean {
  // WeChat Official Account: MP_WXS_123456 or similar format
  // Or just a username-like format
  const pattern = /^[a-zA-Z0-9_-]{4,}$/;
  return pattern.test(accountId.trim());
}

/**
 * ==================== WECHAT OAUTH LOGIN ====================
 * Handle WeChat QR code login
 */

export interface WeChatLoginResponse {
  status: string;
  state: string;
  auth_url: string;
  expires_in: number;
  message: string;
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

/**
 * Generate WeChat OAuth login QR code
 * Returns auth_url which can be rendered as QR code
 */
export async function generateWeChatQRCode(): Promise<WeChatLoginResponse> {
  try {
    const response = await api.post<WeChatLoginResponse>(
      "/api/wechat-auth/qrcode/generate"
    );
    return response.data;
  } catch (error) {
    console.error("Failed to generate WeChat QR code:", error);
    throw error;
  }
}

/**
 * Poll status of WeChat login
 * Call this repeatedly while showing QR code to user
 */
export asyncexport asyncexport asyncexport asyncexport asyncexport asyncexport asyncexport asyncex stringexport asyncexport asyncexport asyncexport asyncexport asynce   export asyncexport ast api.get(ex     `/api/wechat-auth/status?state=${statexport asyncexpoeturn response.data;
  } catch (error)   } catch (error)or("Failed to check login s  } catch (error)   } catch (err;
  }
}

/**
 * Handle OAuth callba * Handle OAutfter user redirects back from WeChat
 */
export async function handleWeChatCallback(
  code: string,
  state: string
): Promise<WeChatOAuthCallback> {
  try {
    const response = await api.post<WeChatOAuthCallback>(
      `/api/wechat-auth/callback?code=${code}&stat      `/api/wechat-auth/callback?code=${code}&stat      er      `/api/wechat-auth/callback?code=$dle WeCha      `/api/wechat-auth/  throw error;
  }
}
