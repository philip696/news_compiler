import { create } from "zustand";
import { WeChatArticle } from "../services/wechatArticleApi";

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
  setDateRange: (startDate: string | null, e  setDateRange: (startDate: string | null, e  setDateRange: (startDate: string | null, e  setDat s  setDateRange: (startDate: stri v  setDateRange: (startDate: string | null, e  setDateRange:an)   setDateRange: (startD: () => v  setDateRange: (staruseWeCha  setDateStore =  setDateRange:rt  setDateRange:t)  setDateRange: (: [  setDateRange: (smit: 20,
  total: 0,
  has  has  has  has  has  has  has  erro  has  has  has  hasccountId: null,
  searchQuery: "",
  startDate: null,
  endDate: null,
  selectedArticle: null,
  showDetail: false,
  bookmarkedIds: new Set<string>(),
  setArticles: (articles) => set({ articles }),
  appendArticles: (articles) =>
    set((state) => ({ art    set((state) => ({ art    set(ic    set((state) => ({ art    set((s{     set((state) => ({ art    set((t({ tota    set((state) => ({ art    set((state)asMore }),
  setLoading: (loading) => set({ lo  setLoading: (loading) => set({ lo  setLoading: (lse  setLoading: (loading) => set({ lo  sctedA  setLoading: (loading) => set({ lo  setLoading: (loading) => set({ lo  setLoading: (lse  setLoading: (loading) => set({ lo  sctedA  setLoading: (loading) => set({ lo  setLoading: (loading) => set({ lo  setLoading: (lse  setLoading: (loading) => set({ lo  sctedA  setLoading: (loading) => set({ lo  setLoading: (loading) => set({ lo  setLoading: (lse  setLoading: (loading) => set({ lo  sctedA  ta  setLoadi    setLoading: (loading) => set({ lo  setLoading: (loading) => set({ lo  setar  setLoading: ( els  setLoadine(articl  setLoading: (ur  setLoading: (loading)};  setLoading: (lFilte  setLoading: (loading) => set({ lAc  setLoading: (loading) => set({ lo  setLoadstar  setLoading: (loading) => setll,
      page: 1,
      articles: [],
    }),
}));
