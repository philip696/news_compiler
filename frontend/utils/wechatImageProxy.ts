/**
 * WeChat image CDNs (*.qpic.cn, *.qlogo.cn, …) return a hotlink
 * placeholder unless Referer is mp.weixin.qq.com. The backend
 * GET /api/wechat/img proxies with the correct headers — use it for every
 * <img> and CSS url() that points at those hosts.
 *
 * Reuse the same origin normalization as axios (`services/api.ts`) so a trailing
 * slash in NEXT_PUBLIC_API_URL does not produce `//api/...` (404 on Railway).
 */
import { BASE_URL, joinUrl } from '../services/api';

/** Hostname suffixes allowed by /api/wechat/img — keep in sync with backend wechat.py. */
export function isWeChatCdnUrl(raw: string | undefined | null): boolean {
  const s = (raw ?? '').trim();
  if (!s) return false;
  try {
    const u = new URL(s.startsWith('//') ? `https:${s}` : s);
    const h = u.hostname.toLowerCase();
    return h.endsWith('.qpic.cn') || h.endsWith('.qlogo.cn');
  } catch {
    return /\.(qpic|qlogo)\.cn(\/|$|\?|#|&)/i.test(s);
  }
}

export function wechatCdnImageProxyUrl(picUrl: string | undefined | null): string {
  if (!picUrl) return '';
  return `${joinUrl(BASE_URL, '/api/wechat/img')}?url=${encodeURIComponent(picUrl)}`;
}
