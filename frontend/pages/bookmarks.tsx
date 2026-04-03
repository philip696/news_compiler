import { useEffect, useState } from "react";
import { useRouter } from "next/router";
import { api, setAuthToken } from "../services/api";
import { useAuthStore } from "../store/auth";
import { useProtectedRoute } from "../hooks/useProtectedRoute";
import ArticleCard from "../components/ArticleCard";

export default function BookmarksPage() {
  useProtectedRoute();
  const router = useRouter();
  const { token } = useAuthStore();
  const [items, setItems] = useState<any[]>([]);

  useEffect(() => {
    if (!token) return;
    setAuthToken(token);
    api.get("/api/user/bookmarks").then((res) => setItems(res.data));
  }, [token]);

  return (
    <main className="min-h-screen bg-[#f3f4f6] relative overflow-hidden font-sans text-slate-800">
      {/* Background pattern */}
      <div className="absolute inset-0 z-0 opacity-20 pointer-events-none" style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, #94a3b8 1px, transparent 0)', backgroundSize: '32px 32px' }}></div>

      {/* Navigation Bar */}
      <nav className="relative z-10 flex h-16 items-center justify-between bg-slate-900 px-6 shadow-md">
        <div className="flex w-64 items-center gap-3 text-white cursor-pointer" onClick={() => router.push("/")}>
          <div className="flex h-8 w-8 items-center justify-center rounded bg-white text-slate-900 font-bold">S</div>
          <span className="text-xl font-semibold tracking-wide">Synergy</span>
        </div>

        <div className="flex-1" />

        <div className="flex w-64 items-center justify-end gap-5 text-slate-300">
          <button 
            onClick={() => router.push("/")}
            className="hover:text-white transition-colors"
            title="Back to Feed"
          >
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </button>
        </div>
      </nav>

      <div className="relative z-10 mx-auto max-w-screen-2xl p-8">
        <header className="mb-8">
          <h1 className="text-4xl font-bold tracking-tight text-slate-900 mb-2">Bookmarks</h1>
          <p className="text-lg text-slate-600">Your saved articles</p>
        </header>

        {items.length === 0 ? (
          <div className="text-center py-12">
            <svg className="h-16 w-16 mx-auto text-slate-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
            </svg>
            <p className="text-slate-500 text-lg">No bookmarks yet. Start bookmarking articles!</p>
          </div>
        ) : (
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4 auto-rows-[280px]">
            {items.map((article, idx) => {
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
                  isBookmarked={true}
                  size={size}
                  className={className}
                />
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
