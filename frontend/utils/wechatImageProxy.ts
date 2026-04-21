/**
 * WeChat image CDNs (mmbiz.qpic.cn, wx.qlogo.cn, …) return a hotlink
 * placeholder unless Referer is mp.weixin.qq.com. The backend
 * GET /api/wechat/img proxies with the correct headers — use it for every
 * <img> and CSS url() that points at those hosts.
 */
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8007';

export function wechatCdnImageProxyUrl(picUrl: string | undefined | null): string {
  if (!picUrl) return '';
  return `${API_BASE}/api/wechat/img?url=${encodeURIComponent(picUrl)}`;
}
