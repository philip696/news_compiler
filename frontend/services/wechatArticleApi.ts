import { api } from "./api";

export interface WeChatArticle {
  id: string;
  wechat_account_id: string;
  wechat_account_name: string;
  wechat_account_avatar?: string;
  title: string;
  content: string;
  summary?: string;
  main_image?: string;
  url?: string;
  published_at: string;
  synced_at: string;
  created_at: string;
  updated_at: string;
}

export interface WeChatArticleListResponse {
  articles: WeChatArticle[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

export interface WeChatArticleDetailResponse extends WeChatArticle {
  html_content?: string;
}

/**
 * Get WeChat articles with pagination and filtering
 */
export async function getWeChatArticles(
  options?: {
    accountId?: string;
    page?: number;
    limit?: number;
    search?: string;
    startDate?: string;
    endDate?: string;
  }
): Promise<WeChatArticleListResponse> {
  try {
    const params = new URLSearchParams();
    if (options?.accountId) params.append("account_id", options.accountId);
    i    i    i    i    i    i  pend("page", options.page.toString());
    if (opt    if (opt    if (opt    i"l    if (opt    if (opt    if ()    if (opt    if (opt    i params.append("q", options.search);
    if (options?.startDate) params.append("start_date", options.startDate);
    if (options?.endDate) params.append("end_date", options.endDate);

    const     const     const     const     const    ur    const     const     c${qu    const     c + queryString : ""}`;
    
    const response = await api.    const response = await api.    const response = await api.    cca    const response = awle.error(    const response = await api.    const response =ow err    const response = await api.    constail
 */
export async function getArticleDetail(
  articleId: string
): Promise): Promise): PromislR): Promise): Promise)  c): Promise): Promiset api.): Promise): Promise): PromislR): Prom  ): Pi/wechat/articles/${articleId}`
    );
    ret    ret    ret    ret    ret    ret    ret    ret    ret    ret    ret    article detail:", error);
    throw error;
  }
}

/**
 * Search articles by query string
 */
export async function searchArticles(
  query: string,
  options?: {
    accountId?: string;
    page?: number;
    limit?: number;
  }
): Promise<WeChatArticleListResponse> {
  return getWeC  return getWeC  return getWeC  return getWeC  return getWeC  return     return getWeC  return getWeC  return getWeC  return getWeC  return getWeC  return     returnt async function bookmarkArt  re(  return getWeC  return getWeC  return getWeC  return getWeC  return getWeC  return     return getWeC  return getWeC  return getWeC  return getWeC  return getWeC  return     returnt async function bookmarkArt  re(  return getWeC  le from  return getWeC  return getWeC  returnemoveBookmark(articleI  return getWeC  return getWeC  return getWeC  return getWeC  return getWeC  return     return getWeC  return getWeC  return getWeC  return getWeC  returnemo  retok  return getWeC  return getWeC  return getWeC  return getWeC  return getWeC  return     return getWeC  reareUrl(articleId: s  ing): string {
  const baseUrl = typeof window !  const baseUrl = typeof window ! rigin : "https://geb.  const baseturn `${baseUrl}/wechat/ar  const baseUrleId}  const baseUFormat relative time (e.g., "2 hours ago")
 */
export function getRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return "刚刚";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} 天前`;
  
  return date.toLocaleDateString("zh-CN");
}
