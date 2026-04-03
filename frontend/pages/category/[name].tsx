import { useRouter } from "next/router";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../services/api";
import { useAuthStore } from "../../store/auth";
import { useProtectedRoute } from "../../hooks/useProtectedRoute";
import ArticleCard from "../../components/ArticleCard";

interface Article {
  id: string;
  title: string;
  content: string;
  url: string;
  source_id: string;
  source_name: string;
  published_at: string;
  topic: string;
  topic_confidence: number;
  logo_url: string;
  main_image: string;
  category: string;
}

interface ArticleActions {
  [articleId: string]: {
    liked: boolean;
    bookmarked: boolean;
  };
}

export default function CategoryPage() {
  useProtectedRoute();
  const router = useRouter();
  const { token } = useAuthStore();
  const { name } = router.query;
  const [articleActions, setArticleActions] = useState<ArticleActions>({});

  // Fetch articles for this category
  const { data: categoryData, isLoading, error } = useQuery({
    queryKey: ["category", name, token],
    queryFn: async () => {
      if (!token || !name) throw new Error("Missing credentials or category");
      const response = await api.get(`/api/feed/category/${name}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      return response.data;
    },
    enabled: !!token && !!name,
  });

  const articles = categoryData?.articles || [];
  const categoryName = typeof name === "string" ? decodeURIComponent(name) : "";

  const handleLike = async (e: React.MouseEvent, articleId: string) => {
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

  const handleBookmark = async (e: React.MouseEvent, articleId: string) => {
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

  if (!token) {
    return (
      <div className="min-h-screen bg-[#f3f4f6] flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">Access Denied</h1>
          <p className="text-slate-600">Please log in to view articles</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#f3f4f6] flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">Loading...</h1>
          <p className="text-slate-600">Fetching articles from {categoryName}</p>
        </div>
      </div>
    );
  }

  if (error || articles.length === 0) {
    return (
      <div className="min-h-screen bg-[#f3f4f6] flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">No Articles Found</h1>
          <p className="text-slate-600 mb-4">No articles available for {categoryName}</p>
          <button
            onClick={() => router.push("/categories")}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Back to Categories
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f3f4f6] relative overflow-hidden font-sans text-slate-800">
      {/* Abstract background */}
      <div className="absolute inset-0 z-0 opacity-20 pointer-events-none" style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, #94a3b8 1px, transparent 0)', backgroundSize: '32px 32px' }}></div>

      {/* Navigation Bar */}
      <nav className="relative z-10 flex h-16 items-center justify-between bg-slate-900 px-6 shadow-md">
        <div className="flex w-full items-center gap-3 text-white">
          <button 
            onClick={() => router.push("/categories")}
            className="flex h-8 w-8 items-center justify-center rounded bg-slate-800 hover:bg-slate-700 transition-colors"
            title="Back to Categories"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <span className="text-xl font-semibold tracking-wide">{categoryName}</span>
          <span className="ml-auto text-sm font-medium text-slate-400">{articles.length} articles</span>
        </div>
      </nav>

      <main className="relative z-10 mx-auto max-w-6xl px-8 py-12">
        <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4 auto-rows-[280px]">
          {articles.map((article: Article, idx: number) => {
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
                onLike={handleLike}
                onBookmark={handleBookmark}
                isLiked={articleActions[article.id]?.liked || false}
                isBookmarked={articleActions[article.id]?.bookmarked || false}
                size={size}
                className={className}
              />
            );
          })}
        </div>

        <div className="mt-12 text-center">
          <button
            onClick={() => router.push("/categories")}
            className="px-6 py-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            Browse More Categories
          </button>
        </div>
      </main>
    </div>
  );
}
