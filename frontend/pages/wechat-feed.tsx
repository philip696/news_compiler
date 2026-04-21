'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

interface Article {
  id: string;
  mpId: string;
  title: string;
  picUrl: string;
  publishTime: string | number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8007';

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

  const gebToken = typeof window !== 'undefined' ? getGebToken() : null;

  const { data: articles = [], isLoading, error } = useQuery<Article[]>({
    queryKey: ['wechatArticles', mpId],
    queryFn: async () => {
      const res = await axios.get(`${API_BASE}/api/wechat/articles`, {
        params: { mpId },
        headers: { Authorization: `Bearer ${gebToken}` },
      });
      return res.data;
    },
    enabled: !!mpId && !!gebToken,
  });

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
        <div className="animate-spin h-8 w-8 border-4 border-blue-200 border-t-blue-600 rounded-full mx-auto mb-4" />
        <p className="text-slate-600">Loading articles…</p>
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
      {/* Header */}
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

      {/* Articles List */}
      <div className="space-y-4">
        {articles.length === 0 ? (
          <div className="rounded-lg bg-slate-50 border border-slate-200 p-8 text-center">
            <p className="text-slate-600">No articles cached yet. Try syncing from the sidebar.</p>
          </div>
        ) : (
          articles.map((article) => (
            <article
              key={article.id}
              className="border border-slate-200 rounded-lg overflow-hidden hover:shadow-md transition-shadow bg-white"
            >
              <a
                href={`https://mp.weixin.qq.com/s/${article.id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="block p-5 hover:bg-slate-50 transition-colors"
              >
                <div className="flex gap-4">
                  {article.picUrl && (
                    <img
                      src={article.picUrl}
                      alt={article.title}
                      className="w-20 h-20 object-cover rounded-lg flex-shrink-0"
                    />
                  )}
                  <div className="flex-1 min-w-0">
                    <h2 className="text-base font-semibold text-slate-900 line-clamp-2 hover:text-blue-600">
                      {article.title}
                    </h2>
                    <p className="text-xs text-slate-400 mt-2">{formatDate(article.publishTime)}</p>
                  </div>
                </div>
              </a>
            </article>
          ))
        )}
      </div>
    </div>
  );
}
