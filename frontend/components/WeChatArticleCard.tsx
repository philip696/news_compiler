import { useState } from "react";
import { motion } from "framer-motion";
import { WeChatArticle, getRelativeTime } from "../services/wechatArticleApi";

interface WeChatArticleCardProps {
  article: WeChatArticle;
  onAvatarClick?: (accountId: string) => void;
  onReadClick?: (article: WeChatArticle) => void;
  onBookmark?: (articleId: string) => Promise<void>;
  onShare?: (article: WeChatArticle) => void;
  isBookmarked?: boolean;
  compact?: boolean;
}

function timeLabel(a: WeChatArticle): string {
  const raw = a.published_at ?? a.publishTime;
  if (raw === undefined || raw === null || raw === "") return "";
  const s = typeof raw === "number" ? new Date(raw).toISOString() : String(raw);
  return getRelativeTime(s);
}

export function WeChatArticleCard({
  article,
  onAvatarClick,
  onReadClick,
  onBookmark,
  onShare,
  isBookmarked = false,
  compact = false,
}: WeChatArticleCardProps) {
  const [bookmarking, setBookmarking] = useState(false);

  const accountLabel =
    article.wechat_account_name || article.wechat_account_id || article.mpId || "";
  const imageSrc = article.main_image || article.picUrl;
  const published = timeLabel(article);

  const handleBookmarkClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!onBookmark) return;
    setBookmarking(true);
    try {
      await onBookmark(article.id);
    } finally {
      setBookmarking(false);
    }
  };

  const handleShareClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onShare?.(article);
  };

  if (compact) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white rounded-xl border border-slate-200 p-4 hover:shadow-md"
      >
        <div className="flex gap-3">
          {article.wechat_account_avatar ? (
            <button
              type="button"
              className="shrink-0 w-10 h-10 rounded-full overflow-hidden"
              onClick={() =>
                article.wechat_account_id &&
                onAvatarClick?.(article.wechat_account_id)
              }
            >
              <img
                src={article.wechat_account_avatar}
                alt=""
                className="w-full h-full object-cover"
              />
            </button>
          ) : null}
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-slate-900 line-clamp-2 mb-1">
              {article.title}
            </h3>
            <p className="text-xs text-slate-600">
              {accountLabel}
              {published ? ` · ${published}` : ""}
            </p>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.article
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-xl border border-slate-200 overflow-hidden hover:shadow-md cursor-pointer"
      onClick={() => onReadClick?.(article)}
    >
      {imageSrc ? (
        <div className="aspect-[2/1] bg-gradient-to-br from-slate-100 to-slate-200">
          <img
            src={imageSrc}
            alt=""
            className="w-full h-full object-cover"
          />
        </div>
      ) : (
        <div className="aspect-[2/1] bg-gradient-to-br from-slate-100 to-slate-200" />
      )}
      <div className="p-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <p className="text-xs font-semibold text-slate-700 line-clamp-1">
            {accountLabel}
          </p>
          {published ? (
            <span className="text-xs text-slate-500 shrink-0">{published}</span>
          ) : null}
        </div>
        <h3 className="text-base font-semibold text-slate-900 line-clamp-2 mb-3">
          {article.title}
        </h3>
        <div className="flex gap-2">
          {onBookmark ? (
            <button
              type="button"
              onClick={handleBookmarkClick}
              disabled={bookmarking}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200"
            >
              {bookmarking ? "…" : isBookmarked ? "Saved" : "Save"}
            </button>
          ) : null}
          {onShare ? (
            <button
              type="button"
              onClick={handleShareClick}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200"
            >
              Share
            </button>
          ) : null}
        </div>
      </div>
    </motion.article>
  );
}
