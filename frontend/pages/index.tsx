import { useMemo, useState } from "react";
import { useRouter } from "next/router";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import { api, setAuthToken } from "../services/api";
import { useAuthStore } from "../store/auth";
import { useFeed } from "../hooks/useFeed";
import { useProtectedRoute } from "../hooks/useProtectedRoute";
import StoryClusterCard from "../components/StoryClusterCard";
import ArticleCard from "../components/ArticleCard";
import TopicSelector from "../components/TopicSelector";
import SourcePreferences from "../components/SourcePreferences";

type Topic = {
  id: string;
  name: string;
  followed: boolean;
  interest_score: number;
};

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

export default function HomePage() {
  useProtectedRoute();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { token, setToken } = useAuthStore();
  const [username, setUsername] = useState("demo");
  const [password, setPassword] = useState("secret123");
  const [status, setStatus] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [categoryArticles, setCategoryArticles] = useState<Article[]>([]);
  const [loadingCategory, setLoadingCategory] = useState(false);
  const [articleActions, setArticleActions] = useState<{ [key: string]: { liked: boolean; bookmarked: boolean } }>({});

  const { data: stories = [] } = useFeed(!!token);

  // Fetch categories
  const { data: categoriesData } = useQuery({
    queryKey: ["categories", token],
    queryFn: async () => {
      const response = await api.get("/api/feed/categories");
      return response.data.categories || [];
    },
    enabled: !!token
  });

  const { data: topics = [] } = useQuery({
    queryKey: ["topics", token],
    queryFn: async () => (await api.get<Topic[]>("/api/topics")).data,
    enabled: !!token
  });

  const sourceIds = useMemo(() => {
    const ids = new Set<string>();
    stories.forEach((story) => story.articles.forEach((article) => ids.add(article.source_id)));
    return Array.from(ids);
  }, [stories]);

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
        errorMessage = detail.map((err: any) => err.msg || String(err)).join(', ');
      } else if (typeof detail === 'string') {
        errorMessage = detail;
      }
      
      setStatus(errorMessage);
    }
  };

  const handleCategoryClick = async (category: string) => {
    setSelectedCategory(category);
    setLoadingCategory(true);
    try {
      const response = await api.get(`/api/feed/category/${encodeURIComponent(category)}?limit=50`);
      setCategoryArticles(response.data.articles || []);
    } catch (error) {
      console.error("Failed to load category articles:", error);
      setCategoryArticles([]);
    }
    setLoadingCategory(false);
  };

  const handleLikeArticle = async (e: React.MouseEvent, articleId: string) => {
    e.stopPropagation();
    try {
      const isCurrentlyLiked = articleActions[articleId]?.liked || false;
      if (isCurrentlyLiked) {
        await api.delete("/api/articles/like", { data: { article_id: articleId } });
      } else {
        await api.post("/api/articles/like", { article_id: articleId });
      }
      setArticleActions(prev => ({
        ...prev,
        [articleId]: { ...prev[articleId], liked: !isCurrentlyLiked }
      }));
    } catch (error) {
      console.error("Failed to like article:", error);
    }
  };

  const handleBookmarkArticle = async (e: React.MouseEvent, articleId: string) => {
    e.stopPropagation();
    try {
      const isCurrentlyBookmarked = articleActions[articleId]?.bookmarked || false;
      if (isCurrentlyBookmarked) {
        await api.delete("/api/articles/bookmark", { data: { article_id: articleId } });
      } else {
        await api.post("/api/articles/bookmark", { article_id: articleId });
      }
      setArticleActions(prev => ({
        ...prev,
        [articleId]: { ...prev[articleId], bookmarked: !isCurrentlyBookmarked }
      }));
    } catch (error) {
      console.error("Failed to bookmark article:", error);
    }
  };

  const follow = async (topicId: string) => {
    await api.post("/api/topics/follow", { topic_id: topicId });
    queryClient.invalidateQueries({ queryKey: ["topics", token] });
    queryClient.invalidateQueries({ queryKey: ["feed"] });
  };

  const unfollow = async (topicId: string) => {
    await api.delete("/api/topics/unfollow", { data: { topic_id: topicId } });
    queryClient.invalidateQueries({ queryKey: ["topics", token] });
    queryClient.invalidateQueries({ queryKey: ["feed"] });
  };

  const bookmark = async (articleId: string) => {
    try {
      const isCurrentlyBookmarked = articleActions[articleId]?.bookmarked || false;
      if (isCurrentlyBookmarked) {
        await api.delete("/api/articles/bookmark", { data: { article_id: articleId } });
      } else {
        await api.post("/api/articles/bookmark", { article_id: articleId });
      }
      setArticleActions(prev => ({
        ...prev,
        [articleId]: { ...prev[articleId], bookmarked: !isCurrentlyBookmarked }
      }));
      setStatus(isCurrentlyBookmarked ? "Bookmark removed" : "Bookmarked article");
    } catch (error) {
      console.error("Failed to bookmark article:", error);
      setStatus("Failed to bookmark article");
    }
  };

  const like = async (articleId: string) => {
    try {
      const isCurrentlyLiked = articleActions[articleId]?.liked || false;
      if (isCurrentlyLiked) {
        await api.delete("/api/articles/like", { data: { article_id: articleId } });
      } else {
        await api.post("/api/articles/like", { article_id: articleId });
      }
      setArticleActions(prev => ({
        ...prev,
        [articleId]: { ...prev[articleId], liked: !isCurrentlyLiked }
      }));
    } catch (error) {
      console.error("Failed to like article:", error);
    }
  };

  const muteSource = async (sourceId: string) => {
    await api.post("/api/source/mute", { source_id: sourceId });
    queryClient.invalidateQueries({ queryKey: ["feed"] });
  };

  const preferSource = async (sourceId: string) => {
    await api.post("/api/source/prefer", { source_id: sourceId });
    queryClient.invalidateQueries({ queryKey: ["feed"] });
  };

  return (
    <div className="min-h-screen bg-[#f3f4f6] relative overflow-hidden font-sans text-slate-800">
      {/* Abstract network-node background pattern placeholder */}
      <div className="absolute inset-0 z-0 opacity-20 pointer-events-none" style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, #94a3b8 1px, transparent 0)', backgroundSize: '32px 32px' }}></div>

      {/* Navigation Bar */}
      <nav className="relative z-10 flex h-16 items-center justify-between bg-slate-900 px-6 shadow-md">
        {/* Logo */}
        <div className="flex w-64 items-center gap-3 text-white">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-white text-slate-900 font-bold">S</div>
          <span className="text-xl font-semibold tracking-wide">Synergy</span>
        </div>

        {/* Search Bar */}
        <div className="flex flex-1 items-center justify-center max-w-2xl px-8">
          <div className="relative w-full">
            <input
              type="text"
              placeholder="Search intelligence..."
              className="w-full rounded-full bg-slate-800 border border-slate-700 py-2 pl-12 pr-4 text-sm text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-500 transition-all"
            />
            <svg className="absolute left-4 top-2.5 h-4 w-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>

        {/* Icons */}
        <div className="flex w-64 items-center justify-end gap-5 text-slate-300">
          {token && (
            <button 
              onClick={() => router.push("/categories")}
              className="hover:text-white transition-colors flex items-center gap-2 px-3 py-1 rounded-lg hover:bg-slate-800"
              title="Browse Categories"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6a2 2 0 012-2h12a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V6z" />
              </svg>
              <span className="hidden md:inline text-sm font-medium">Categories</span>
            </button>
          )}
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

      <main className="relative z-10 mx-auto max-w-screen-2xl p-8 h-[calc(100vh-4rem)] overflow-y-auto">

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
          <div className="flex gap-8 h-full">
            {/* Sidebar with Categories */}
            <aside className="w-72 hidden xl:flex flex-col gap-4 flex-shrink-0 max-h-[calc(100vh-8rem)] overflow-y-auto">
              <div className="rounded-3xl border border-slate-200/60 bg-white/70 backdrop-blur-md p-5 shadow-sm sticky top-0">
                <h3 className="font-semibold text-slate-900 mb-4">📚 Categories</h3>
                <div className="flex flex-col gap-2 max-h-96 overflow-y-auto">
                  <button
                    onClick={() => {
                      setSelectedCategory(null);
                      setCategoryArticles([]);
                    }}
                    className={`text-left px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      selectedCategory === null 
                        ? 'bg-slate-900 text-white' 
                        : 'text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    🏠 Main Feed
                  </button>
                  {categoriesData && Array.isArray(categoriesData) && categoriesData.map((category: string) => (
                    <button
                      key={category}
                      onClick={() => handleCategoryClick(category)}
                      className={`text-left px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        selectedCategory === category 
                          ? 'bg-slate-900 text-white' 
                          : 'text-slate-700 hover:bg-slate-100'
                      }`}
                    >
                      {category}
                    </button>
                  ))}
                </div>
              </div>
            </aside>

            {/* Main Feed or Category Articles */}
            <section className="flex-1 pb-12">
              {selectedCategory === null ? (
                // Main Feed View
                <>
                  <div className="mb-6 flex items-end justify-between">
                    <h1 className="text-2xl font-bold tracking-tight text-slate-900">Intelligence Feed</h1>
                    <span className="text-sm font-medium text-slate-500 uppercase tracking-wider">{stories.length} updates</span>
                  </div>
                  <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4 auto-rows-[280px]">
                    {stories.map((story, i) => {
                      let size: 'compact' | 'regular' | 'featured' = 'compact';
                      let className = '';
                      
                      const pattern = i % 8;
                      
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
                        <StoryClusterCard 
                          key={story.cluster_id} 
                          story={story} 
                          onBookmark={bookmark} 
                          onLike={like}
                          size={size}
                          className={className}
                        />
                      );
                    })}
                  </div>
                </>
              ) : (
                // Category Articles View
                <>
                  <div className="mb-6 flex items-end justify-between">
                    <div>
                      <h1 className="text-2xl font-bold tracking-tight text-slate-900">{selectedCategory}</h1>
                      <p className="text-sm text-slate-500 mt-1">Browse articles from this category</p>
                    </div>
                    <span className="text-sm font-medium text-slate-500 uppercase tracking-wider">{categoryArticles.length} articles</span>
                  </div>
                  {loadingCategory ? (
                    <div className="flex justify-center items-center h-40">
                      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-slate-900"></div>
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
