import { useRouter } from "next/router";
import { useQuery } from "@tanstack/react-query";
import { api, BASE_URL } from "../services/api";
import { useAuthStore } from "../store/auth";
import { useProtectedRoute } from "../hooks/useProtectedRoute";
import ArticleCard from "../components/ArticleCard";

interface BookmarkedArticle {
  id: string;
  title: string;
  url: string;
  source_name: string;
  cluster_id: string;
  published_at: string;
}

const getLogoPath = (sourceName: string): string => {
  const normalized = sourceName.toLowerCase().trim();
  const logoMap: { [key: string]: string } = {
    "techcrunch": "tech_crunch.png",
    "bbc": "wired.png",
    "cnn": "cnn.png",
    "reuters": "reuters.png",
    "the verge": "theverge.jpg",
    "theverge": "theverge.jpg",
    "wired": "wired.png",
  };
  const filename = logoMap[normalized] || "wired.png";
  return `${BASE_URL}/data/logos/${filename}`;
};

export default function ProfilePage() {
  useProtectedRoute();
  const router = useRouter();
  const { token, setToken } = useAuthStore();

  const { data: bookmarks = [] } = useQuery({
    queryKey: ["bookmarks", token],
    queryFn: async () => (await api.get<BookmarkedArticle[]>("/api/user/bookmarks")).data,
    enabled: !!token,
  });

  const { data: likes = [] } = useQuery({
    queryKey: ["likes", token],
    queryFn: async () => (await api.get<BookmarkedArticle[]>("/api/user/likes")).data,
    enabled: !!token,
  });

  return (
    <div className="min-h-screen bg-[#f3f4f6] relative overflow-hidden font-sans text-slate-800">
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
          <button
            onClick={() => {
              setToken("");
              router.push("/");
            }}
            className="rounded-lg bg-red-600 hover:bg-red-700 px-4 py-2 text-sm font-medium text-white transition-colors"
          >
            Logout
          </button>
        </div>
      </nav>

      <main className="relative z-10 mx-auto max-w-screen-2xl p-8">
        <div className="mb-12">
          <h1 className="text-4xl font-bold tracking-tight text-slate-900 mb-2">My Profile</h1>
          <p className="text-lg text-slate-600">View your bookmarks and liked articles</p>
        </div>

        <div className="grid gap-12">
          {/* Bookmarks Section */}
          <section>
            <h2 className="mb-8 text-3xl font-bold text-slate-900 flex items-center gap-3">
              <svg className="h-8 w-8 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
                <path d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
              Bookmarks ({bookmarks.length})
            </h2>

            {bookmarks.length === 0 ? (
              <div className="text-center py-16 rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50">
                <svg className="h-16 w-16 mx-auto text-slate-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                </svg>
                <p className="text-slate-500 text-lg">No bookmarks yet. Start bookmarking articles!</p>
              </div>
            ) : (
              <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4 auto-rows-[280px]">
                {bookmarks.map((article, idx) => {
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
          </section>

          {/* Likes Section */}
          <section>
            <h2 className="mb-8 text-3xl font-bold text-slate-900 flex items-center gap-3">
              <svg className="h-8 w-8 text-red-600" fill="currentColor" viewBox="0 0 24 24">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
              </svg>
              Liked Articles ({likes.length})
            </h2>

            {likes.length === 0 ? (
              <div className="text-center py-16 rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50">
                <svg className="h-16 w-16 mx-auto text-slate-300 mb-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
                </svg>
                <p className="text-slate-500 text-lg">No liked articles yet. Start liking articles!</p>
              </div>
            ) : (
              <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4 auto-rows-[280px]">
                {likes.map((article, idx) => {
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
                      isLiked={true}
                      size={size}
                      className={className}
                    />
                  );
                })}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
