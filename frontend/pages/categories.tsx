import { useRouter } from "next/router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../services/api";
import { useAuthStore } from "../store/auth";
import { useProtectedRoute } from "../hooks/useProtectedRoute";

export default function CategoriesPage() {
  useProtectedRoute();
  const router = useRouter();
  const { token } = useAuthStore();

  // Fetch available categories
  const { data: categoriesData, isLoading, error } = useQuery({
    queryKey: ["categories", token],
    queryFn: async () => {
      if (!token) throw new Error("Not authenticated");
      const response = await api.get("/api/feed/categories", {
        headers: { Authorization: `Bearer ${token}` }
      });
      return response.data;
    },
    enabled: !!token,
  });

  const categories = categoriesData?.categories || [];

  const handleCategoryClick = (categoryName: string) => {
    router.push(`/category/${encodeURIComponent(categoryName)}`);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#f3f4f6] flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">Loading...</h1>
        </div>
      </div>
    );
  }

  if (error || categories.length === 0) {
    return (
      <div className="min-h-screen bg-[#f3f4f6] flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">No Categories Found</h1>
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
            onClick={() => router.push("/")}
            className="flex h-8 w-8 items-center justify-center rounded bg-slate-800 hover:bg-slate-700 transition-colors"
            title="Back"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <span className="text-xl font-semibold tracking-wide">Browse Categories</span>
        </div>
        <div className="flex-1" />
        <button
          onClick={() => router.push("/")}
          className="text-sm font-medium text-slate-300 hover:text-white transition-colors"
        >
          Back to Feed
        </button>
      </nav>

      <main className="relative z-10 mx-auto max-w-6xl px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {categories.map((category: string) => (
            <button
              key={category}
              onClick={() => handleCategoryClick(category)}
              className="group relative p-8 rounded-2xl bg-white/80 backdrop-blur-md border border-slate-200/60 shadow-lg hover:shadow-2xl hover:bg-white transition-all duration-300 text-left"
            >
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 text-white font-bold group-hover:from-blue-600 group-hover:to-blue-700 transition-all">
                  {category.charAt(0)}
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-slate-900 group-hover:text-blue-600 transition-colors line-clamp-2">
                    {category}
                  </h3>
                </div>
              </div>
              
              <div className="mt-4 pt-4 border-t border-slate-200/50">
                <p className="text-sm text-slate-600 group-hover:text-slate-700 transition-colors">
                  Browse 100 articles
                </p>
              </div>

              {/* Hover arrow */}
              <div className="absolute right-6 bottom-6 flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100 text-blue-600 group-hover:bg-blue-600 group-hover:text-white transition-all group-hover:translate-x-1">
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </button>
          ))}
        </div>
      </main>
    </div>
  );
}
