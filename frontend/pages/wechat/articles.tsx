import Link from "next/link";

/**
 * Placeholder route (tests and legacy links may target `/wechat/articles`).
 * Main WeChat article browsing is on `/wechat-feed` or the home WeChat integration.
 */
export default function WeChatArticlesPlaceholderPage() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6">
      <h1 className="text-2xl font-bold text-slate-900 mb-2">WeChat articles</h1>
      <p className="text-slate-600 mb-6 text-center max-w-md">
        This page is no longer used. Open the feed from the home page or use
        WeChat Official Accounts.
      </p>
      <Link
        href="/"
        className="text-blue-600 hover:underline font-medium"
      >
        ← Back to home
      </Link>
    </div>
  );
}
