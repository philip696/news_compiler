import { api } from "./api";

/** Matches `/api/wechat/articles` rows plus optional legacy fields */
export interface WeChatArticle {
  id: string;
  mpId?: string;
  title: string;
  picUrl?: string;
  publishTime?: string | number;
  liked?: boolean;
  bookmarked?: boolean;
  wechat_account_id?: string;
  wechat_account_name?: string;
  wechat_account_avatar?: string;
  main_image?: string;
  content?: string;
  summary?: string;
  url?: string;
  published_at?: string;
  synced_at?: string;
  created_at?: string;
  updated_at?: string;
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

export async function getWeChatArticles(options?: {
  accountId?: string;
  page?: number;
  limit?: number;
  search?: string;
  startDate?: string;
  endDate?: string;
}): Promise<WeChatArticleListResponse> {
  const params: Record<string, string> = {};
  if (options?.accountId) params.mpId = options.accountId;
  if (options?.page != null) params.page = String(options.page);
  if (options?.limit != null) params.limit = String(options.limit);
  if (options?.search) params.q = options.search;
  if (options?.startDate) params.start_date = options.startDate;
  if (options?.endDate) params.end_date = options.endDate;

  const response = await api.get<WeChatArticle[]>("/api/wechat/articles", {
    params,
  });
  const articles = Array.isArray(response.data) ? response.data : [];
  return {
    articles,
    total: articles.length,
    page: options?.page ?? 1,
    limit: options?.limit ?? Math.max(articles.length, 1),
    has_more: false,
  };
}

export async function getArticleDetail(
  articleId: string,
  mpId?: string
): Promise<WeChatArticleDetailResponse> {
  const { articles } = await getWeChatArticles({ accountId: mpId });
  const found = articles.find((a) => a.id === articleId);
  if (!found) {
    throw new Error(`Article not found: ${articleId}`);
  }
  return found;
}

export async function searchArticles(
  query: string,
  options?: { accountId?: string; page?: number; limit?: number }
): Promise<WeChatArticleListResponse> {
  return getWeChatArticles({ ...options, search: query });
}

export function getShareUrl(articleId: string): string {
  if (typeof window === "undefined") {
    return `/wechat/article/${articleId}`;
  }
  return `${window.location.origin}/wechat/article/${articleId}`;
}

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
