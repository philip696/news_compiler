import { useMemo, useState, useEffect, useRef, type MouseEvent } from "react";
import { useRouter } from "next/router";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import { api, setAuthToken } from "../services/api";
import { useAuthStore } from "../store/auth";
import { useHomeFeedProgressive } from "../hooks/useFeed";
import { useProtectedRoute } from "../hooks/useProtectedRoute";
import StoryClusterCard from "../components/StoryClusterCard";
import ArticleCard from "../components/ArticleCard";
import WeChatOfficialAccounts from "../components/WeChatOfficialAccounts";
import WeWeRSSQRLogin from "../components/WeWeRSSQRLogin";
import { useChatContext } from "../context/ChatContext";
import { motion } from "framer-motion";
import { wechatCdnImageProxyUrl } from "../utils/wechatImageProxy";

type Article = {
  id: string;
  title: string;
  content: string;
  main_image: string;
  source_name: string;
  published_at: string;
  url: string;
  category: string;
};

type WeReadArticle = {
  id: string;
  mpId: string;
  title: string;
  picUrl: string;
  publishTime: number | string;
  liked?: boolean;
  bookmarked?: boolean;
};

type WeReadFeed = {
  id: string;
  mpName: string;
  mpCover: string;
  articleCount: number;
  syncTime: number;
};

export default function HomePage() {
  useProtectedRoute();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { token, setToken } = useAuthStore();
  const { setPageContext } = useChatContext();
  const [username, setUsername] = useState("demo");
  const [password, setPassword] = useState("secret123");
  const [status, setStatus] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Lock background scroll + close the drawer with ESC while the mobile sidebar is open
  useEffect(() => {
    if (typeof document === "undefined") return;
    if (sidebarOpen) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      const onKey = (e: KeyboardEvent) => {
        if (e.key === "Escape") setSidebarOpen(false);
      };
      window.addEventListener("keydown", onKey);
      return () => {
        document.body.style.overflow = prev;
        window.removeEventListener("keydown", onKey);
      };
    }
  }, [sidebarOpen]);

  // Keep chat context in sync with what the user is browsing
  useEffect(() => {
    if (selectedCategory) {
      setPageContext({ type: 'category', label: selectedCategory });
    } else {
      setPageContext({ type: 'feed' });
    }
  }, [selectedCategory, setPageContext]);
  const [categoryArticles, setCategoryArticles] = useState<Article[]>([]);
  const [loadingCategory, setLoadingCategory] = useState(false);
  const [articleActions, setArticleActions] = useState<{ [key: string]: { liked: boolean; bookmarked: boolean } }>({});
  const [showWeChatLogin, setShowWeChatLogin] = useState(false);
  const [weChatAccounts, setWeChatAccounts] = useState<any[]>([]);

  // ── Search ────────────────────────────────────────────────────────── //
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const searchDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSearchInput = (value: string) => {
    setSearchInput(value);
    if (searchDebounce.current) clearTimeout(searchDebounce.current);
    if (value.trim() === "") {
      setSearchQuery("");
      return;
    }
    searchDebounce.current = setTimeout(() => setSearchQuery(value.trim()), 350);
  };

  const { data: searchResults = [], isFetching: searchLoading } = useQuery({
    queryKey: ["search", searchQuery],
    queryFn: async () => {
      const res = await api.get("/api/feed/search", { params: { q: searchQuery, limit: 60 } });
      return res.data.stories || [];
    },
    enabled: !!token && searchQuery.length > 0,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });

  const { allStories, isLoadingInitial: homeFeedLoading } = useHomeFeedProgressive(!!token);

  // Fetch categories
  const { data: categoriesData } = useQuery({
    queryKey: ["categories", token],
    queryFn: async () => {
      const response = await api.get("/api/feed/categories");
      return response.data.categories || [];
    },
    enabled: !!token,
    staleTime: 300_000,
    refetchOnWindowFocus: false,
  });

  const { data: exploreCategoriesData = [] } = useQuery<string[]>({
    queryKey: ["exploreCategories", token],
    queryFn: async () => {
      const res = await api.get("/api/feed/explore/categories");
      return res.data.categories || [];
    },
    enabled: !!token,
    staleTime: 300_000,
    refetchOnWindowFocus: false,
  });

  // Categories hidden from the sidebar (served by backend but suppressed in UI)
  const HIDDEN_CATEGORIES = useMemo(
    () =>
      new Set<string>([
        "🔗 WeChat Official Accounts",
        "🌍 World News",
        "💻 Technology",
        "📊 Business",
        "💰 Finance",
      ]),
    []
  );

  // Merged deduped category list (with hidden categories removed)
  const allCategories = useMemo(() => {
    const seen = new Set<string>();
    const merged: string[] = [];
    for (const c of [...(categoriesData || []), ...exploreCategoriesData]) {
      if (HIDDEN_CATEGORIES.has(c)) continue;
      if (!seen.has(c)) { seen.add(c); merged.push(c); }
    }
    return merged;
  }, [categoriesData, exploreCategoriesData, HIDDEN_CATEGORIES]);

  const { data: wereadFeeds = [] } = useQuery<WeReadFeed[]>({
    queryKey: ["wereadFeeds"],
    queryFn: async () => (await api.get("/api/wechat/mps")).data,
    enabled: !!token && selectedCategory === "wechat",
    refetchInterval: selectedCategory === "wechat" ? 120_000 : false,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
  });

  const [wechatMpFilter, setWechatMpFilter] = useState<string | null>(null);

  const { data: wereadArticles = [], isLoading: wereadLoading } = useQuery<WeReadArticle[]>({
    queryKey: ["wereadArticles", wechatMpFilter],
    queryFn: async () => {
      const params = wechatMpFilter ? { mpId: wechatMpFilter } : {};
      return (await api.get("/api/wechat/articles", { params })).data;
    },
    enabled: !!token && selectedCategory === "wechat",
    refetchInterval: selectedCategory === "wechat" ? 120_000 : false,
    staleTime: 45_000,
    refetchOnWindowFocus: false,
  });

  const auth = async (mode: "register" | "login") => {
    try {
      if (mode === "register") {
        await api.post("/api/auth/register", { username, password });
      }
      const login = await api.post("/api/auth/login", { username, password });
      setToken(login.data.access_token);
      setAuthToken(login.data.access_token);
      setStatus("Authenticated");
      queryClient.invalidateQueries();
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      let errorMessage = "Authentication failed";
      
      if (Array.isArray(detail)) {
        errorMessage = detail
          .map((err: any) => {
            if (typeof err === 'string') return err;
            if (typeof err === 'object' && err !== null) {
              // Try to extract msg, else JSON.stringify
              return err.msg || JSON.stringify(err);
            }
            return String(err);
          })
          .join(', ');
      } else if (typeof detail === 'string') {
        errorMessage = detail;
      } else if (typeof detail === 'object' && detail !== null) {
        errorMessage = JSON.stringify(detail);
      }
      setStatus(errorMessage);
    }
  };

  const handleCategoryClick = async (category: string) => {
    setSelectedCategory(category);
    
    // Check if clicking on WeChat Official Accounts
    if (category === "🔗 WeChat Official Accounts") {
      setShowWeChatLogin(true);
      setCategoryArticles([]);
      return;
    }
    
    // Regular category handling
    setShowWeChatLogin(false);
    setLoadingCategory(true);
    try {
      const [webRes, exploreRes] = await Promise.allSettled([
        api.get(`/api/feed/category/${encodeURIComponent(category)}?limit=50`),
        api.get(`/api/feed/explore/category/${encodeURIComponent(category)}?limit=50`),
      ]);
      const webArticles: Article[] =
        webRes.status === "fulfilled" ? webRes.value.data.articles || [] : [];
      // explore returns StoryClusterOut[] — extract the single article from each cluster
      const exploreArticles: Article[] =
        exploreRes.status === "fulfilled"
          ? (exploreRes.value.data.stories || []).flatMap((s: any) => s.articles || [])
          : [];
      // Merge, deduplicate by id
      const seen = new Set<string>();
      const merged: Article[] = [];
      for (const a of [...webArticles, ...exploreArticles]) {
        if (!seen.has(a.id)) { seen.add(a.id); merged.push(a); }
      }
      setCategoryArticles(merged);
    } catch (error) {
      console.error("Failed to load category articles:", error);
      setCategoryArticles([]);
    }
    setLoadingCategory(false);
  };

  const handleLikeArticle = async (e: React.MouseEvent, articleId: string) => {
    e.stopPropagation();
    const prevEntry = articleActions[articleId];
    const isCurrentlyLiked = prevEntry?.liked || false;
    const bookmarked = prevEntry?.bookmarked || false;
    setArticleActions((prev) => ({
      ...prev,
      [articleId]: { liked: !isCurrentlyLiked, bookmarked },
    }));
    try {
      if (isCurrentlyLiked) {
        await api.delete("/api/articles/like", { data: { article_id: articleId } });
      } else {
        await api.post("/api/articles/like", { article_id: articleId });
      }
    } catch (error) {
      console.error("Failed to like article:", error);
      setArticleActions((prev) => ({
        ...prev,
        [articleId]: { liked: isCurrentlyLiked, bookmarked },
      }));
    }
  };

  const handleBookmarkArticle = async (e: React.MouseEvent, articleId: string) => {
    e.stopPropagation();
    const prevEntry = articleActions[articleId];
    const isCurrentlyBookmarked = prevEntry?.bookmarked || false;
    const liked = prevEntry?.liked || false;
    setArticleActions((prev) => ({
      ...prev,
      [articleId]: { liked, bookmarked: !isCurrentlyBookmarked },
    }));
    try {
      if (isCurrentlyBookmarked) {
        await api.delete("/api/articles/bookmark", { data: { article_id: articleId } });
      } else {
        await api.post("/api/articles/bookmark", { article_id: articleId });
      }
    } catch (error) {
      console.error("Failed to bookmark article:", error);
      setArticleActions((prev) => ({
        ...prev,
        [articleId]: { liked, bookmarked: isCurrentlyBookmarked },
      }));
    }
  };

  const bookmark = async (articleId: string) => {
    const prevEntry = articleActions[articleId];
    const isCurrentlyBookmarked = prevEntry?.bookmarked || false;
    const liked = prevEntry?.liked || false;
    setArticleActions((prev) => ({
      ...prev,
      [articleId]: { liked, bookmarked: !isCurrentlyBookmarked },
    }));
    try {
      if (isCurrentlyBookmarked) {
        await api.delete("/api/articles/bookmark", { data: { article_id: articleId } });
      } else {
        await api.post("/api/articles/bookmark", { article_id: articleId });
      }
      setStatus(isCurrentlyBookmarked ? "Bookmark removed" : "Bookmarked article");
    } catch (error) {
      console.error("Failed to bookmark article:", error);
      setArticleActions((prev) => ({
        ...prev,
        [articleId]: { liked, bookmarked: isCurrentlyBookmarked },
      }));
      setStatus("Failed to bookmark article");
    }
  };

  const like = async (articleId: string) => {
    const prevEntry = articleActions[articleId];
    const isCurrentlyLiked = prevEntry?.liked || false;
    const bookmarked = prevEntry?.bookmarked || false;
    setArticleActions((prev) => ({
      ...prev,
      [articleId]: { liked: !isCurrentlyLiked, bookmarked },
    }));
    try {
      if (isCurrentlyLiked) {
        await api.delete("/api/articles/like", { data: { article_id: articleId } });
      } else {
        await api.post("/api/articles/like", { article_id: articleId });
      }
    } catch (error) {
      console.error("Failed to like article:", error);
      setArticleActions((prev) => ({
        ...prev,
        [articleId]: { liked: isCurrentlyLiked, bookmarked },
      }));
    }
  };

  const toggleWeChatLike = async (e: MouseEvent, article: WeReadArticle) => {
    e.preventDefault();
    e.stopPropagation();
    const id = article.id;
    const prevEntry = articleActions[id];
    const cur = prevEntry?.liked ?? article.liked ?? false;
    const bm = prevEntry?.bookmarked ?? article.bookmarked ?? false;
    setArticleActions((prev) => ({
      ...prev,
      [id]: { liked: !cur, bookmarked: bm },
    }));
    try {
      if (cur) {
        await api.delete("/api/articles/like", { data: { article_id: id } });
      } else {
        await api.post("/api/articles/like", { article_id: id });
      }
    } catch (err) {
      console.error("Failed to like WeChat article:", err);
      setArticleActions((prev) => ({
        ...prev,
        [id]: { liked: cur, bookmarked: bm },
      }));
    }
  };

  const toggleWeChatBookmark = async (e: MouseEvent, article: WeReadArticle) => {
    e.preventDefault();
    e.stopPropagation();
    const id = article.id;
    const prevEntry = articleActions[id];
    const cur = prevEntry?.bookmarked ?? article.bookmarked ?? false;
    const lk = prevEntry?.liked ?? article.liked ?? false;
    setArticleActions((prev) => ({
      ...prev,
      [id]: { liked: lk, bookmarked: !cur },
    }));
    try {
      if (cur) {
        await api.delete("/api/articles/bookmark", { data: { article_id: id } });
      } else {
        await api.post("/api/articles/bookmark", { article_id: id });
      }
    } catch (err) {
      console.error("Failed to bookmark WeChat article:", err);
      setArticleActions((prev) => ({
        ...prev,
        [id]: { liked: lk, bookmarked: cur },
      }));
    }
  };

  return (
    <div className="min-h-screen bg-[#f3f4f6] relative overflow-hidden font-sans text-slate-800">
      {/* Abstract network-node background pattern placeholder */}
      <div className="absolute inset-0 z-0 opacity-20 pointer-events-none" style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, #94a3b8 1px, transparent 0)', backgroundSize: '32px 32px' }}></div>

      {/* Navigation Bar */}
      <nav className="relative z-10 flex h-16 items-center justify-between bg-slate-900 px-4 md:px-6 shadow-md gap-2">
        {/* Logo + mobile hamburger */}
        <div className="flex items-center gap-2 md:gap-3 text-white md:w-64">
          {token && (
            <button
              onClick={() => setSidebarOpen((v) => !v)}
              aria-label={sidebarOpen ? "Close menu" : "Open menu"}
              aria-expanded={sidebarOpen}
              className="xl:hidden inline-flex h-9 w-9 items-center justify-center rounded-lg text-slate-200 hover:bg-slate-800 transition-colors"
            >
              {sidebarOpen ? (
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          )}
          <div className="flex h-8 w-8 items-center justify-center rounded bg-white text-slate-900 font-bold">S</div>
          <span className="hidden sm:inline text-xl font-semibold tracking-wide">Synergy</span>
        </div>

        {/* Search Bar */}
        <div className="flex flex-1 items-center justify-center max-w-2xl px-2 md:px-8">
          <div className="relative w-full">
            <input
              type="text"
              value={searchInput}
              onChange={(e) => handleSearchInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Escape") handleSearchInput(""); }}
              placeholder="Search articles..."
              className="w-full rounded-full bg-slate-800 border border-slate-700 py-2 pl-12 pr-10 text-sm text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-500 transition-all"
            />
            <svg className="absolute left-4 top-2.5 h-4 w-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            {searchInput && (
              <button
                onClick={() => handleSearchInput("")}
                className="absolute right-3 top-2 text-slate-400 hover:text-slate-200 transition-colors"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* Icons */}
        <div className="flex items-center justify-end gap-3 md:gap-5 md:w-64 text-slate-300">
          <button className="relative hover:text-white transition-colors">
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
            <span className="absolute top-0 right-0 h-2 w-2 rounded-full bg-red-500"></span>
          </button>
          {token && (
            <button 
              onClick={() => router.push("/profile")}
              className="h-8 w-8 overflow-hidden rounded-full border border-slate-700 bg-slate-800 flex items-center justify-center hover:border-slate-500 transition-colors"
              title="Profile"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </button>
          )}
        </div>
      </nav>

      <main
        className={`relative z-10 mx-auto max-w-screen-2xl p-4 md:p-6 lg:p-8 ${
          token
            ? "flex min-h-0 flex-col h-[calc(100dvh-4rem)] max-h-[calc(100dvh-4rem)] overflow-hidden"
            : "h-[calc(100vh-4rem)] overflow-y-auto"
        }`}
      >

        {!token && (
          <section className="mb-8 mx-auto max-w-md grid gap-4 rounded-3xl border border-slate-200/50 bg-white/80 backdrop-blur-xl p-6 shadow-xl">
            <h2 className="text-xl font-semibold text-slate-800 text-center mb-2">Access Intelligence</h2>
            <input
              className="rounded-xl border border-slate-300/50 bg-slate-50/50 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-slate-500"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Username"
            />
            <input
              className="rounded-xl border border-slate-300/50 bg-slate-50/50 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-slate-500"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              type="password"
            />
            <div className="grid grid-cols-2 gap-3 mt-2">
              <button onClick={() => auth("register")} className="rounded-xl bg-slate-200 hover:bg-slate-300 px-4 py-3 text-sm font-medium text-slate-800 transition-colors">
                Register
              </button>
              <button onClick={() => auth("login")} className="rounded-xl bg-slate-900 hover:bg-slate-800 px-4 py-3 text-sm font-medium text-white transition-colors shadow-lg">
                Login
              </button>
            </div>
            {status && <p className="text-sm text-center text-red-500 font-medium">{status}</p>}
          </section>
        )}

        {token && (
          <div className="flex min-h-0 w-full flex-1 xl:gap-8">

            {/* Mobile backdrop — taps outside close the drawer */}
            {sidebarOpen && (
              <div
                onClick={() => setSidebarOpen(false)}
                className="xl:hidden fixed inset-0 z-30 bg-slate-900/40 backdrop-blur-sm"
                aria-hidden="true"
              />
            )}

            {/* Sidebar: fixed slide-in drawer on < xl, static column on xl+ */}
            <aside
              data-testid="wechat-sidebar"
              className={`
                flex min-h-0 flex-col gap-4 flex-shrink-0 overflow-y-auto overscroll-y-contain
                bg-[#f3f4f6] xl:bg-transparent
                fixed z-40 top-16 left-0 bottom-0 w-72 p-4 pr-2 border-r border-slate-200 shadow-xl
                transform transition-transform duration-300 ease-out
                ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
                xl:static xl:translate-x-0 xl:h-full xl:max-h-full xl:self-stretch xl:p-0 xl:border-0 xl:shadow-none
                xl:w-72
              `}
              aria-hidden={!sidebarOpen && typeof window !== "undefined" && window.innerWidth < 1280}
            >
              <div className="rounded-3xl border border-slate-200/60 bg-white/80 xl:bg-white/70 backdrop-blur-md p-5 shadow-sm">
                <h3 className="font-semibold text-slate-900 mb-3">Browse</h3>
                <div className="flex flex-col gap-1">

                  {/* Top-level nav */}
                  <button
                    onClick={() => { setSelectedCategory(null); setCategoryArticles([]); setSidebarOpen(false); }}
                    className={`text-left px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      selectedCategory === null ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    🏠 Main Feed
                  </button>
                  <button
                    onClick={() => { setSelectedCategory("wechat"); setCategoryArticles([]); setWechatMpFilter(null); setSidebarOpen(false); }}
                    className={`text-left px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      selectedCategory === "wechat" ? 'bg-green-700 text-white' : 'text-slate-700 hover:bg-green-50'
                    }`}
                  >
                    🟩 WeChat Articles
                  </button>

                  {/* All categories (web + Kaggle merged) */}
                  {allCategories.length > 0 && (
                    <>
                      <p className="px-3 pt-3 pb-1 text-[10px] font-bold uppercase tracking-widest text-slate-400">
                        Categories
                      </p>
                      {allCategories.map((category: string) => (
                    <button
                      key={category}
                      onClick={() => { handleCategoryClick(category); setSidebarOpen(false); }}
                      className={`text-left px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        selectedCategory === category 
                          ? 'bg-slate-900 text-white' 
                          : 'text-slate-700 hover:bg-slate-100'
                      }`}
                    >
                      {category}
                    </button>
                  ))}
                    </>
                  )}
                </div>
              </div>

              {/* WeChat account management panel */}
              {selectedCategory === "wechat" && (
                <div className="rounded-3xl border border-green-200/60 bg-white/80 xl:bg-white/70 backdrop-blur-md p-5 shadow-sm">
                  <WeChatOfficialAccounts onLogin={() => queryClient.invalidateQueries({ queryKey: ["wereadFeeds"] })} />
              </div>
              )}
            </aside>

            {/* Main Feed, Category Articles, or WeChat Articles */}
            <section className="relative min-h-0 flex-1 overflow-y-auto overscroll-y-contain pb-12">
              {searchQuery ? (
                // ── Search Results View ───────────────────────────────── //
                <>
                  <div className="mb-6 flex items-end justify-between flex-wrap gap-2">
                    <div>
                      <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                        Results for &ldquo;{searchQuery}&rdquo;
                      </h1>
                      {!searchLoading && (
                        <p className="text-sm text-slate-500 mt-1">{searchResults.length} articles found</p>
                      )}
                    </div>
                    <button
                      onClick={() => handleSearchInput("")}
                      className="text-sm text-slate-500 hover:text-slate-800 font-medium transition-colors"
                    >
                      ✕ Clear search
                    </button>
                  </div>

                  {searchLoading ? (
                    <div className="flex flex-col justify-center items-center h-40">
                      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-slate-900" />
                      <p className="text-slate-600 text-sm mt-3">Loading...</p>
                    </div>
                  ) : searchResults.length === 0 ? (
                    <div className="rounded-2xl border border-slate-200 bg-white/70 p-12 text-center max-w-md mx-auto mt-12">
                      <p className="text-2xl mb-3">🔍</p>
                      <h3 className="font-semibold text-slate-800 mb-2">No results found</h3>
                      <p className="text-sm text-slate-500">Try a different search term.</p>
                    </div>
                  ) : (
                  <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4 auto-rows-[280px]">
                      {searchResults.map((story: any, i: number) => {
                        const pattern = i % 8;
                      let size: 'compact' | 'regular' | 'featured' = 'compact';
                      let className = '';
                        if (pattern === 0 || pattern === 5) { size = 'featured'; className = 'md:col-span-2 md:row-span-2'; }
                        else if (pattern === 1 || pattern === 4) { size = 'regular'; className = 'md:col-span-1 md:row-span-2'; }
                        return (
                          <StoryClusterCard
                            key={story.cluster_id || story.id || i}
                            story={story}
                            onBookmark={bookmark}
                            onLike={like}
                            size={size}
                            className={className}
                          />
                        );
                      })}
                    </div>
                  )}
                </>
              ) : selectedCategory === "wechat" ? (
                // ── WeChat / WeRead Articles View ─────────────────────── //
                <>
                  <div className="mb-6 flex items-end justify-between flex-wrap gap-3">
                    <div>
                      <h1 className="text-2xl font-bold tracking-tight text-slate-900">WeChat Articles</h1>
                      <p className="text-sm text-slate-500 mt-1">
                        {wereadArticles.length} articles from {wereadFeeds.length} official accounts
                      </p>
                      <p className="text-xs text-slate-400 mt-2 max-w-2xl leading-relaxed">
                        <span className="font-medium text-slate-500">Steps:</span> Login in Sidebar → Add Official Account → Sync → View Articles
                      </p>
                    </div>
                    {/* Per-feed filter pills */}
                    {wereadFeeds.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        <button
                          onClick={() => setWechatMpFilter(null)}
                          className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
                            wechatMpFilter === null ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                          }`}
                        >
                          All
                        </button>
                        {wereadFeeds.map((f) => (
                          <button
                            key={f.id}
                            onClick={() => setWechatMpFilter(f.id === wechatMpFilter ? null : f.id)}
                            className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
                              wechatMpFilter === f.id ? 'bg-green-700 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                            }`}
                          >
                            {f.mpName || f.id}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {wereadLoading ? (
                    <div className="flex flex-col justify-center items-center h-40">
                      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-green-700" />
                      <p className="text-slate-600 text-sm mt-3">Loading...</p>
                    </div>
                  ) : wereadArticles.length === 0 ? (
                    <div className="rounded-2xl border border-slate-200 bg-white/70 p-12 text-center max-w-md mx-auto mt-12">
                      <p className="text-2xl mb-3">🟩</p>
                      <h3 className="font-semibold text-slate-800 mb-2">No WeChat articles yet</h3>
                      <p className="text-sm text-slate-500">
                        Add an official account in the sidebar by pasting an article share link, then sync to import articles.
                      </p>
                    </div>
                  ) : (
                    <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4 auto-rows-[280px]">
                      {wereadArticles.map((article, i) => {
                        const mpName = wereadFeeds.find((f) => f.id === article.mpId)?.mpName || article.mpId;
                        const publishDate = typeof article.publishTime === "number"
                          ? new Date(article.publishTime * 1000).toLocaleDateString(undefined, { month: "short", day: "numeric" })
                          : new Date(article.publishTime).toLocaleDateString(undefined, { month: "short", day: "numeric" });
                      const pattern = i % 8;
                        let colSpan = "md:col-span-1 md:row-span-1";
                        let titleSize = "text-base font-semibold";
                        let lineClamp = "line-clamp-2";
                        let padding = "p-4";
                      if (pattern === 0 || pattern === 5) {
                          colSpan = "md:col-span-2 md:row-span-2";
                          titleSize = "text-2xl font-extrabold";
                          lineClamp = "line-clamp-4";
                          padding = "p-8";
                      } else if (pattern === 1 || pattern === 4) {
                          colSpan = "md:col-span-1 md:row-span-2";
                          titleSize = "text-lg font-bold";
                          lineClamp = "line-clamp-3";
                          padding = "p-5";
                        }
                        const isWl = articleActions[article.id]?.liked ?? article.liked ?? false;
                        const isWb = articleActions[article.id]?.bookmarked ?? article.bookmarked ?? false;
                        return (
                          <motion.div
                            key={article.id}
                            role="link"
                            tabIndex={0}
                            onClick={() => router.push(`/article/${article.id}`)}
                            onKeyDown={(ev) => {
                              if (ev.key === "Enter" || ev.key === " ") {
                                ev.preventDefault();
                                router.push(`/article/${article.id}`);
                              }
                            }}
                            initial={{ opacity: 0, scale: 0.98, y: 10 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            transition={{ duration: 0.3, ease: "easeOut" }}
                            className={`${colSpan} group relative flex flex-col overflow-hidden rounded-3xl bg-slate-900 shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 cursor-pointer h-full w-full min-h-[250px] border border-white/10`}
                          >
                            {/* Background image */}
                            <div
                              className="absolute inset-0 bg-cover bg-center transition-transform duration-700 group-hover:scale-105"
                              style={{
                                backgroundImage: article.picUrl
                                  ? `url("${wechatCdnImageProxyUrl(article.picUrl)}")`
                                  : "linear-gradient(135deg, #1a472a 0%, #2d6a4f 100%)",
                              }}
                            />
                            {/* Gradient overlay */}
                            <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/40 to-black/10" />
                            <div className={`relative flex flex-col justify-between ${padding} h-full z-10`}>
                              <div className="flex justify-between items-start gap-2">
                                <span className="inline-block rounded-lg bg-green-700/80 backdrop-blur-md px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white border border-green-500/30">
                                  WeChat
                                </span>
                                <div className="flex items-center gap-1.5 flex-shrink-0">
                                  <button
                                    type="button"
                                    onClick={(e) => toggleWeChatLike(e, article)}
                                    className={`flex h-8 w-8 items-center justify-center rounded-full backdrop-blur-md transition-all shadow-sm border ${
                                      isWl
                                        ? "bg-red-500/90 border-red-500 text-white"
                                        : "bg-black/40 border-white/20 text-white hover:bg-black/60"
                                    }`}
                                    title={isWl ? "Unlike" : "Like"}
                                  >
                                    <svg
                                      className="h-4 w-4"
                                      fill={isWl ? "currentColor" : "none"}
                                      stroke="currentColor"
                                      viewBox="0 0 24 24"
                                    >
                                      <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth="2"
                                        d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
                                      />
                                    </svg>
                                  </button>
                                  <button
                                    type="button"
                                    onClick={(e) => toggleWeChatBookmark(e, article)}
                                    className={`flex h-8 w-8 items-center justify-center rounded-full backdrop-blur-md transition-all shadow-sm border ${
                                      isWb
                                        ? "bg-amber-500/90 border-amber-500 text-white"
                                        : "bg-black/40 border-white/20 text-white hover:bg-black/60"
                                    }`}
                                    title={isWb ? "Remove bookmark" : "Bookmark"}
                                  >
                                    <svg
                                      className="h-4 w-4"
                                      fill={isWb ? "currentColor" : "none"}
                                      stroke="currentColor"
                                      viewBox="0 0 24 24"
                                    >
                                      <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth="2"
                                        d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
                                      />
                                    </svg>
                                  </button>
                                  <span className="hidden sm:inline rounded-full bg-black/50 backdrop-blur-md px-2 py-1 text-[10px] font-semibold text-white/80 border border-white/10 opacity-0 group-hover:opacity-100 transition-opacity">
                                    Open ↗
                                  </span>
                                </div>
                              </div>
                              <div className="flex flex-col gap-2 mt-auto pointer-events-none">
                                <h3 className={`${lineClamp} ${titleSize} leading-tight tracking-tight text-white drop-shadow-md`}>
                                  {article.title}
                                </h3>
                                <div className="flex items-center gap-2 text-xs text-slate-300">
                                  <span className="font-semibold text-white/90">{mpName}</span>
                                  <span className="text-white/40">·</span>
                                  <span className="text-white/70">{publishDate}</span>
                                </div>
                              </div>
                            </div>
                          </motion.div>
                        );
                      })}
                    </div>
                  )}
                </>
              ) : selectedCategory === null ? (
                // ── Main Feed View (Web + Kaggle merged) ──────────────── //
                <>
                  <div className="mb-6 flex items-end justify-between flex-wrap gap-2">
                    <div>
                      <h1 className="text-2xl font-bold tracking-tight text-slate-900">Intelligence Feed</h1>
                    </div>
                  </div>

                  {homeFeedLoading ? (
                    <div className="flex flex-col justify-center items-center h-40">
                      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-slate-900" />
                      <p className="text-slate-600 text-sm mt-3">Loading...</p>
                    </div>
                  ) : allStories.length === 0 ? (
                    <div className="rounded-2xl border border-slate-200 bg-white/70 p-12 text-center max-w-md mx-auto mt-8">
                      <p className="text-slate-600">No stories in your feed yet.</p>
                    </div>
                  ) : (
                    <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4 auto-rows-[280px]">
                      {allStories.map((story: any, i: number) => {
                        const pattern = i % 8;
                        let size: 'compact' | 'regular' | 'featured' = 'compact';
                        let className = '';
                        if (pattern === 0 || pattern === 5) { size = 'featured'; className = 'md:col-span-2 md:row-span-2'; }
                        else if (pattern === 1 || pattern === 4) { size = 'regular'; className = 'md:col-span-1 md:row-span-2'; }
                      return (
                        <StoryClusterCard 
                            key={story.cluster_id || story.id || i}
                          story={story} 
                          onBookmark={bookmark} 
                          onLike={like}
                          size={size}
                          className={className}
                        />
                      );
                    })}
                  </div>
                  )}
                </>
              ) : showWeChatLogin ? (
                // WeChat QR Login View
                <>
                  <div className="mb-6 flex items-end justify-between">
                    <div>
                      <h1 className="text-2xl font-bold tracking-tight text-slate-900">🔗 WeChat Official Accounts</h1>
                      <p className="text-sm text-slate-500 mt-1">Connect your WeChat account to add articles</p>
                    </div>
                  </div>
                  <div className="rounded-3xl border border-slate-200/60 bg-white/70 backdrop-blur-md p-8 shadow-sm">
                    <WeWeRSSQRLogin
                      onAccountAdded={(account) => {
                        setWeChatAccounts(prev => [...prev, account]);
                      }}
                      onError={(error) => {
                        console.error("WeChat login error:", error);
                      }}
                    />
                  </div>
                </>
              ) : (
                // ── Category Articles View ────────────────────────────── //
                <>
                  <div className="mb-6 flex items-end justify-between flex-wrap gap-2">
                    <div>
                      <h1 className="text-2xl font-bold tracking-tight text-slate-900">{selectedCategory}</h1>
                      <p className="text-sm text-slate-500 mt-1">Browse articles from this category</p>
                    </div>
                    <span className="text-sm font-medium text-slate-500 uppercase tracking-wider">{categoryArticles.length} articles</span>
                  </div>
                  {loadingCategory ? (
                    <div className="flex flex-col justify-center items-center h-40">
                      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-slate-900" />
                      <p className="text-slate-600 text-sm mt-3">Loading...</p>
                    </div>
                  ) : (
                    <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4 auto-rows-[280px]">
                      {categoryArticles.map((article, idx) => {
                        let size: 'compact' | 'regular' | 'featured' = 'compact';
                        let className = '';
                        const pattern = idx % 8;
                        if (pattern === 0 || pattern === 5) {
                          size = 'featured';
                          className = 'md:col-span-2 md:row-span-2';
                        } else if (pattern === 1 || pattern === 4) {
                          size = 'regular';
                          className = 'md:col-span-1 md:row-span-2';
                        } else {
                          size = 'compact';
                          className = 'md:col-span-1 md:row-span-1';
                        }
                        return (
                          <ArticleCard
                            key={article.id}
                            article={article}
                            onLike={handleLikeArticle}
                            onBookmark={handleBookmarkArticle}
                            isLiked={articleActions[article.id]?.liked || false}
                            isBookmarked={articleActions[article.id]?.bookmarked || false}
                            size={size}
                            className={className}
                          />
                        );
                      })}
                    </div>
                  )}
                </>
              )}

            </section>
          </div>
        )}
      </main>
    </div>
  );
}
