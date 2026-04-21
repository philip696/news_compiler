import { create } from "zustand";
import type { WeChatArticle } from "../services/wechatArticleApi";

interface WeChatArticlesState {
  articles: WeChatArticle[];
  page: number;
  limit: number;
  total: number;
  hasMore: boolean;
  loading: boolean;
  error: string | null;
  selectedAccountId: string | null;
  searchQuery: string;
  startDate: string | null;
  endDate: string | null;
  selectedArticle: WeChatArticle | null;
  showDetail: boolean;
  bookmarkedIds: Set<string>;

  setArticles: (articles: WeChatArticle[]) => void;
  appendArticles: (articles: WeChatArticle[]) => void;
  setPage: (page: number) => void;
  setTotal: (total: number) => void;
  setHasMore: (hasMore: boolean) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setSelectedAccountId: (id: string | null) => void;
  setSearchQuery: (query: string) => void;
  setDateRange: (startDate: string | null, endDate: string | null) => void;
  setSelectedArticle: (article: WeChatArticle | null) => void;
  setShowDetail: (show: boolean) => void;
  toggleBookmark: (id: string) => void;
  reset: () => void;
}

const initial = {
  articles: [] as WeChatArticle[],
  page: 1,
  limit: 20,
  total: 0,
  hasMore: false,
  loading: false,
  error: null as string | null,
  selectedAccountId: null as string | null,
  searchQuery: "",
  startDate: null as string | null,
  endDate: null as string | null,
  selectedArticle: null as WeChatArticle | null,
  showDetail: false,
  bookmarkedIds: new Set<string>(),
};

export const useWeChatArticlesStore = create<WeChatArticlesState>((set) => ({
  ...initial,

  setArticles: (articles) => set({ articles }),

  appendArticles: (more) =>
    set((state) => ({ articles: [...state.articles, ...more] })),

  setPage: (page) => set({ page }),
  setTotal: (total) => set({ total }),
  setHasMore: (hasMore) => set({ hasMore }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  setSelectedAccountId: (id) => set({ selectedAccountId: id }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setDateRange: (startDate, endDate) => set({ startDate, endDate }),
  setSelectedArticle: (article) => set({ selectedArticle: article }),
  setShowDetail: (show) => set({ showDetail: show }),

  toggleBookmark: (id) =>
    set((state) => {
      const next = new Set(state.bookmarkedIds);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return { bookmarkedIds: next };
    }),

  reset: () => set({ ...initial, bookmarkedIds: new Set<string>() }),
}));
