import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { WeChatArticle, getRelativeTime } from "../services/wechatArticleApi";

interface Props {
  article: WeChatArticle | null;
  isOpen: boolean;
  onClose: () => void;
  onBookmark?: (articleId: string) => Promise<void>;
  isBookmarked?: boolean;
}

function timeLabel(a: WeChatArticle): string {
  const raw = a.published_at ?? a.publishTime;
  if (raw === undefined || raw === null || raw === "") return "";
  const s = typeof raw === "number" ? new Date(raw).toISOString() : String(raw);
  return getRelativeTime(s);
}

export function WeChatArticleDetail(props: Props) {
  const [bookmarking, setBookmarking] = useState(false);
  const { article, isOpen, onClose, onBookmark, isBookmarked } = props;

  const handleBookmark = async () => {
    if (!article || !onBookmark) return;
    setBookmarking(true);
    try {
      await onBookmark(article.id);
    } finally {
      setBookmarking(false);
    }
  };

  return (
    <AnimatePresence>
      {article && isOpen ? (
        <>
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 z-40"
          />
          <motion.div
            key="panel"
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 50 }}
            className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-3xl max-h-[90vh] overflow-y-auto -translate-x-1/2 -translate-y-1/2 bg-white rounded-2xl shadow-xl p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-4 mb-4">
              <h2 className="text-xl font-bold text-slate-900 flex-1">{article.title}</h2>
              <button
                type="button"
                onClick={onClose}
                className="text-slate-500 hover:text-slate-800 shrink-0"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            {(article.main_image || article.picUrl) ? (
              <img
                src={article.main_image || article.picUrl}
                alt=""
                className="w-full max-h-80 object-cover rounded-xl mb-6"
              />
            ) : null}

            <div className="flex items-center gap-3 mb-6 pb-6 border-b border-slate-200">
              {article.wechat_account_avatar ? (
                <img
                  src={article.wechat_account_avatar}
                  alt=""
                  className="w-12 h-12 rounded-full object-cover"
                />
              ) : (
                <div className="w-12 h-12 rounded-full bg-slate-200" />
              )}
              <div>
                <p className="font-semibold text-slate-900">
                  {article.wechat_account_name || article.mpId || "WeChat"}
                </p>
                {timeLabel(article) ? (
                  <p className="text-sm text-slate-500">{timeLabel(article)}</p>
                ) : null}
              </div>
            </div>

            {article.content ? (
              <div
                dangerouslySetInnerHTML={{ __html: article.content }}
                className="prose prose-slate max-w-none text-slate-700 mb-8"
              />
            ) : article.summary ? (
              <p className="text-slate-700 mb-8 whitespace-pre-wrap">{article.summary}</p>
            ) : null}

            <div className="flex gap-3 pt-6 border-t border-slate-200">
              {onBookmark ? (
                <button
                  type="button"
                  onClick={handleBookmark}
                  disabled={bookmarking}
                  className="flex-1 px-4 py-3 font-semibold bg-slate-100 rounded-lg hover:bg-slate-200"
                >
                  {bookmarking ? "…" : isBookmarked ? "Bookmarked" : "Bookmark"}
                </button>
              ) : null}
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-3 font-semibold bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Close
              </button>
            </div>
          </motion.div>
        </>
      ) : null}
    </AnimatePresence>
  );
}
