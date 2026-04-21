/**
 * WeChat image CDNs (*.qpic.cn, *.qlogo.cn, …) return a hotlink
 * placeholder unless Referer is mp.weixin.qq.com. The backend
 * GET /api/wechat/img proxies with the correct headers — use it for every
 * <img> and CSS url() that points at those hosts.
 *
 * In production, set NEXT_PUBLIC_API_URL to your public API origin (e.g. Railway);
 * otherwise the browser may call localhost and images will fail.
 */
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8007';

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
  return `${API_BASE}/api/wechat/img?url=${encodeURIComponent(picUrl)}`;
}
