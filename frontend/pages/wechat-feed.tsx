'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { api } from '../services/api';
import { wechatCdnImageProxyUrl } from '../utils/wechatImageProxy';

interface Article {
  id: string;
  mpId: string;
  title: string;
  picUrl: string;
  publishTime: string | number;
  liked?: boolean;
  bookmarked?: boolean;
}

const getGebToken = (): string | null => {
  try {
    if (typeof window === 'undefined') return null;
    const raw = localStorage.getItem('auth-storage');
    if (!raw) return null;
    return JSON.parse(raw)?.state?.token ?? null;
  } catch {
    return null;
  }
};

export default function WeChatFeedPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const mpId = searchParams.get('account');
  const queryClient = useQueryClient();

  const gebToken = typeof window !== 'undefined' ? getGebToken() : null;

  const { data: articles = [], isLoading, error } = useQuery<Article[]>({
    queryKey: ['wechatArticles', mpId],
    queryFn: async () => {
      const res = await api.get<Article[]>('/api/wechat/articles', {
        params: { mpId },
      });
      return res.data;
    },
    enabled: !!mpId && !!gebToken,
  });

  const wechatArticlesKey = ['wechatArticles', mpId] as const;

  const toggleLike = async (e: React.MouseEvent, article: Article) => {
    e.preventDefault();
    e.stopPropagation();
    const wasLiked = !!article.liked;
    const previous = queryClient.getQueryData<Article[]>(wechatArticlesKey);
    queryClient.setQueryData<Article[]>(wechatArticlesKey, (old) =>
      (old ?? []).map((a) =>
        a.id === article.id ? { ...a, liked: !wasLiked } : a
      )
    );
    try {
      if (wasLiked) {
        await api.delete('/api/articles/like', {
          data: { article_id: article.id },
        });
      } else {
        await api.post('/api/articles/like', { article_id: article.id });
      }
    } catch (err) {
      console.error('Like failed:', err);
      if (previous !== undefined) {
        queryClient.setQueryData(wechatArticlesKey, previous);
      }
    }
  };

  const toggleBookmark = async (e: React.MouseEvent, article: Article) => {
    e.preventDefault();
    e.stopPropagation();
    const wasBm = !!article.bookmarked;
    const previous = queryClient.getQueryData<Article[]>(wechatArticlesKey);
    queryClient.setQueryData<Article[]>(wechatArticlesKey, (old) =>
      (old ?? []).map((a) =>
        a.id === article.id ? { ...a, bookmarked: !wasBm } : a
      )
    );
    try {
      if (wasBm) {
        await api.delete('/api/articles/bookmark', {
          data: { article_id: article.id },
        });
      } else {
        await api.post('/api/articles/bookmark', { article_id: article.id });
      }
    } catch (err) {
      console.error('Bookmark failed:', err);
      if (previous !== undefined) {
        queryClient.setQueryData(wechatArticlesKey, previous);
      }
    }
  };

  if (!gebToken) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="rounded-lg bg-yellow-50 border border-yellow-200 p-6 text-center">
          <p className="text-slate-700 mb-4">Please log in to GEB first to view articles.</p>
          <button onClick={() => router.push('/')} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg">
            Go to Home
          </button>
        </div>
      </div>
    );
  }

  if (!mpId) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="rounded-lg bg-red-50 border border-red-200 p-6 text-center">
          <p className="text-slate-700 mb-4">No account selected.</p>
          <button onClick={() => router.back()} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg">
            Go Back
          </button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4 text-center">
        <div className="animate-spin h-8 w-8 border-4 border-blue-200 border-t-blue-600 rounded-full mx-auto" />
        <p className="text-slate-600 text-sm mt-3">Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="rounded-lg bg-red-50 border border-red-200 p-6 text-center">
          <p className="text-red-700 mb-4">Failed to load articles.</p>
          <button onClick={() => router.back()} className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg">
            Go Back
          </button>
        </div>
      </div>
    );
  }

  const formatDate = (ts: string | number) => {
    const d = typeof ts === 'number' ? new Date(ts * 1000) : new Date(ts);
    return isNaN(d.getTime()) ? '' : d.toLocaleDateString();
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Official Account Articles</h1>
          <p className="text-sm text-slate-500 mt-1">
            {mpId} · {articles.length} articles
          </p>
        </div>
        <button onClick={() => router.back()} className="text-slate-600 hover:text-slate-900 font-medium">
          ← Back
        </button>
      </div>

      {articles.length === 0 ? (
        <div className="rounded-lg bg-slate-50 border border-slate-200 p-8 text-center">
          <p className="text-slate-600">No articles cached yet. Try syncing from the sidebar.</p>
        </div>
      ) : (
        <ul className="divide-y divide-slate-200 border border-slate-200 rounded-lg bg-white overflow-hidden">
          {articles.map((article) => (
            <li key={article.id} className="flex items-stretch">
              <Link
                href={`/article/${article.id}`}
                className="flex flex-1 items-center gap-4 px-4 py-3 hover:bg-slate-50 transition-colors min-w-0"
              >
                {article.picUrl ? (
                  <img
                    src={wechatCdnImageProxyUrl(article.picUrl)}
                    alt=""
                    loading="lazy"
                    onError={(e) => {
                      (e.currentTarget as HTMLImageElement).style.display = 'none';
                    }}
                    className="w-16 h-16 object-cover rounded-md flex-shrink-0 bg-slate-100"
                  />
                ) : (
                  <div className="w-16 h-16 rounded-md flex-shrink-0 bg-slate-100" />
                )}
                <div className="flex-1 min-w-0">
                  <h2 className="text-sm font-medium text-slate-900 line-clamp-2 hover:text-blue-600">
                    {article.title}
                  </h2>
                  <p className="text-xs text-slate-400 mt-1 tabular-nums">
                    {formatDate(article.publishTime)}
                  </p>
                </div>
              </Link>
              <div className="flex items-center gap-1 pr-3 pl-1 border-l border-slate-100 bg-slate-50/80">
                <button
                  type="button"
                  onClick={(e) => toggleLike(e, article)}
                  className={`flex h-9 w-9 items-center justify-center rounded-full border transition-colors ${
                    article.liked
                      ? 'bg-red-500 border-red-500 text-white'
                      : 'bg-white border-slate-200 text-slate-500 hover:border-red-200 hover:text-red-500'
                  }`}
                  title={article.liked ? 'Unlike' : 'Like'}
                  aria-pressed={article.liked}
                >
                  <svg
                    className={`h-4 w-4 ${article.liked ? 'scale-110' : ''}`}
                    fill={article.liked ? 'currentColor' : 'none'}
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
                  onClick={(e) => toggleBookmark(e, article)}
                  className={`flex h-9 w-9 items-center justify-center rounded-full border transition-colors ${
                    article.bookmarked
                      ? 'bg-amber-500 border-amber-500 text-white'
                      : 'bg-white border-slate-200 text-slate-500 hover:border-amber-200 hover:text-amber-600'
                  }`}
                  title={article.bookmarked ? 'Remove bookmark' : 'Bookmark'}
                  aria-pressed={article.bookmarked}
                >
                  <svg
                    className={`h-4 w-4 ${article.bookmarked ? 'scale-110' : ''}`}
                    fill={article.bookmarked ? 'currentColor' : 'none'}
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
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
