import { useRouter } from "next/router";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, BASE_URL } from "../../services/api";
import { useAuthStore } from "../../store/auth";
import { useProtectedRoute } from "../../hooks/useProtectedRoute";

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
  authors?: string;
  liked?: boolean;
  bookmarked?: boolean;
}

const getLogoPath = (sourceId: string): string => {
  const normalized = sourceId.toLowerCase().trim();
  const logoMap: { [key: string]: string } = {
    "techcrunch": "tech_crunch.png",
    "bbc": "wired.png",
    "cnn": "cnn.png",
    "reuters": "reuters.png",
    "theverge": "theverge.jpg",
    "wired": "wired.png",
  };
  const baseName = normalized.split('.')[0];
  const filename = logoMap[normalized] || logoMap[baseName] || "wired.png";
  return `${BASE_URL}/data/logos/${filename}`;
};

export default function ArticlePage() {
  useProtectedRoute();
  const router = useRouter();
  const { token, userId } = useAuthStore();
  const { id } = router.query;
  const queryClient = useQueryClient();
  const [isLiked, setIsLiked] = useState(false);
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [likeCount, setLikeCount] = useState(0);

  // Fetch article data from backend with like/bookmark status
  const { data: article, isLoading, error } = useQuery<Article>({
    queryKey: ["article", id, token],
    queryFn: async () => {
      if (!id || !token) throw new Error("Missing id or token");
      const response = await api.get(`/api/feed/article/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = response.data;
      // Initialize button states from API response
      setIsLiked(data.liked || false);
      setIsBookmarked(data.bookmarked || false);
      return data;
    },
    enabled: !!id && !!token,
  });

  const handleLike = async () => {
    if (!article) return;
    try {
      if (isLiked) {
        await api.delete("/api/articles/like", { 
          data: { article_id: article.id },
          headers: { Authorization: `Bearer ${token}` }
        });
        setLikeCount(Math.max(0, likeCount - 1));
      } else {
        await api.post("/api/articles/like", 
          { article_id: article.id },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setLikeCount(likeCount + 1);
      }
      setIsLiked(!isLiked);
    } catch (error) {
      console.error("Failed to like article:", error);
    }
  };

  const handleBookmark = async () => {
    if (!article) return;
    try {
      if (isBookmarked) {
        await api.delete("/api/articles/bookmark", { 
          data: { article_id: article.id },
          headers: { Authorization: `Bearer ${token}` }
        });
      } else {
        await api.post("/api/articles/bookmark", 
          { article_id: article.id },
          { headers: { Authorization: `Bearer ${token}` } }
        );
      }
      setIsBookmarked(!isBookmarked);
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
          <p className="text-slate-600">Fetching article details</p>
        </div>
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="min-h-screen bg-[#f3f4f6] flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">Article Not Found</h1>
          <p className="text-slate-600">The article you're looking for could not be loaded</p>
          <button
            onClick={() => router.push("/")}
            className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Back to Feed
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
        <div className="flex w-64 items-center gap-3 text-white">
          <button 
            onClick={() => router.back()}
            className="flex h-8 w-8 items-center justify-center rounded bg-slate-800 hover:bg-slate-700 transition-colors"
            title="Back"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <span className="text-xl font-semibold tracking-wide">[s]</span>
        </div>

        <div className="flex flex-1 items-center justify-center max-w-2xl px-8">
          <div className="text-sm text-slate-400 truncate">{article.source_name}</div>
        </div>

        <div className="w-64" />
      </nav>

      <main className="relative z-10 mx-auto max-w-4xl px-8 py-12 h-[calc(100vh-4rem)] overflow-y-auto">
        <article className="rounded-3xl border border-slate-200/60 bg-white/80 backdrop-blur-md p-12 shadow-lg">
          {/* Header */}
          <div className="mb-8">
            <div className="mb-6 flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 overflow-hidden shadow-sm">
                <img 
                  src={getLogoPath(article.source_id)}
                  alt={article.source_name}
                  className="h-full w-full object-cover"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none';
                  }}
                />
              </div>
              <div>
                <p className="font-semibold text-slate-900">{article.source_name}</p>
                <p className="text-sm text-slate-500">
                  {new Date(article.published_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </p>
              </div>
            </div>

            <div className="mb-4">
              <span className="inline-block rounded-full bg-blue-100 px-4 py-1 text-xs font-semibold uppercase tracking-wider text-blue-600 mb-4">
                {article.topic}
              </span>
              <h1 className="text-4xl font-bold leading-tight text-slate-900 mb-4">
                {article.title}
              </h1>
            </div>
          </div>

          {/* Featured Image */}
          <div className="relative h-96 w-full overflow-hidden rounded-2xl bg-slate-100 mb-8">
            {article.main_image ? (
              <>
                <img
                  src={article.main_image.startsWith('/data') ? `${BASE_URL}${article.main_image}` : article.main_image}
                  alt={article.title}
                  className="absolute inset-0 w-full h-full object-cover"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none';
                  }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-slate-900/20 to-transparent" />
              </>
            ) : (
              <div 
                className="absolute inset-0 bg-cover bg-center"
                style={{ backgroundImage: `url(https://images.unsplash.com/photo-${1500000000000 + (article.id.charCodeAt(0) % 10000)}?auto=format&fit=crop&w=1200&q=80)` }} 
              />
            )}
          </div>

          {/* Link Snippet Box */}
          <div className="mb-8 p-4 border border-slate-200 rounded-xl bg-slate-50 hover:bg-slate-100 transition-colors">
            <p className="text-xs font-semibold text-slate-500 mb-2 uppercase tracking-wide">Source Link</p>
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 break-all"
            >
              <svg className="h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
              <span className="text-sm font-medium truncate">{article.url.replace(/^https?:\/\/(www\.)?/, '')}</span>
            </a>
          </div>

          {/* Content */}
          <div className="prose prose-lg max-w-none text-slate-700 leading-relaxed">
            {article.content.split('\n').filter(p => p.trim()).map((paragraph, idx) => (
              <p key={idx} className="mb-6 text-base leading-7 whitespace-pre-wrap">
                {paragraph}
              </p>
            ))}
          </div>

          {/* Footer */}
          <div className="mt-12 border-t border-slate-200 pt-8">
            {/* Creator/Authors section */}
            {article.authors && (
              <div className="mb-6 pb-6 border-b border-slate-200">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">By</p>
                <p className="text-lg font-medium text-slate-900">{article.authors}</p>
              </div>
            )}

            {/* Top section with confidence and action buttons */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-4">
                <p className="text-sm font-medium text-slate-600">
                  Confidence: <span className="text-slate-900 font-semibold">{(article.topic_confidence * 100).toFixed(0)}%</span>
                </p>
              </div>
              <div className="flex items-center gap-3">
                {/* Like Button */}
                <button
                  onClick={handleLike}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 transform ${
                    isLiked
                      ? 'bg-red-500 text-white hover:bg-red-600 scale-105 shadow-md'
                      : 'border border-slate-300 text-slate-700 hover:bg-slate-50'
                  }`}
                  title="Like article"
                >
                  <svg className={`h-5 w-5 transition-transform ${isLiked ? 'scale-110' : ''}`} fill={isLiked ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                  </svg>
                  Like
                </button>

                {/* Bookmark Button */}
                <button
                  onClick={handleBookmark}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 transform ${
                    isBookmarked
                      ? 'bg-amber-500 text-white hover:bg-amber-600 scale-105 shadow-md'
                      : 'border border-slate-300 text-slate-700 hover:bg-slate-50'
                  }`}
                  title="Bookmark article"
                >
                  <svg className={`h-5 w-5 transition-transform ${isBookmarked ? 'scale-110' : ''}`} fill={isBookmarked ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 5a2 2 0 012-2h6a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                  </svg>
                  Bookmark
                </button>

                {/* Read Original Article Button */}
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-700 px-6 py-2 font-medium text-white transition-colors shadow-md"
                >
                  Read Original
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              </div>
            </div>

            {/* Bottom action buttons */}
            <div className="flex gap-3">
              <button
                onClick={() => router.back()}
                className="flex-1 rounded-lg border border-slate-300 hover:border-slate-400 px-6 py-3 font-medium text-slate-700 transition-colors"
              >
                Back to Feed
              </button>
              <button
                className="flex-1 rounded-lg bg-slate-100 hover:bg-slate-200 px-6 py-3 font-medium text-slate-700 transition-colors"
              >
                Share Article
              </button>
            </div>
          </div>
        </article>
      </main>
    </div>
  );
}
