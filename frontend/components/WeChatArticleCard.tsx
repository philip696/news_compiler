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

  const handleBookmarkClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!onBookmark) return;
    setBookmarking(true);
    try {
      await onBookmark(article.id);
    } finally {
      setBookmar      setBookmar      setBookmar      setBookmar      setBookmar      setBook
    e.stopPr    e.stopPr    e.stopPr    e.stopPr    e.stopPr  cl    e.stopPr    e.stopPr    e.stopPr  e: React.MouseEvent) => {
    e.stopPropagation();
    if (onShare) onShare(articl    if (onShare) onShare(articl ick    if (onShare) onShare =    if (onShare) onShare(articl    if (onSharCl    if (onShare) onShare(articl    if (onShare)  }    if (onShare) onShare(articl    if (onShare) onS      if (onShare) onShare(articl    if (onSha  animate={{ opacity: 1, y: 0 }}
        className="bg-white rounded-xl border border-slate-200 p-4 hover:shadow-md"       >
           v classNa e="flex ga           v classNa cle           v clasva           v classNa e="f
                                                                                                                          "w                       le                           nC             vatarClick}
                                            las       flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-slate-900 line-clamp-2 mb-1">
              {article.title}
            </h3>
            <p className="text-xs text-slate-600 mb-2">
              {article.wechat_account_name} · {get              {article.wechat_account_name} · {get              {article.wechat_account_name} · {get              {article.wechat_account_name} · {get              {article.wechat_account_name} · {get              {article.wechat_account_name} · {get              {article.wechat_account_name} · {get           di              {article.wechat_account_name} · {get              {article.wechat_account_/div>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.article
                                                                                                                                                                                                           x-                                                                    -br from-slate-100 to-slate-200">
        {article.main_image && (
          <img src={          <img src={    {artic          <img sam          <img src={          <img src={    {artic    >
          <img src={          <img src={    {artic          <img sam          <img src={          <img src={    {artic    >
                                                                               x-                                                                    -br from-slate-100 to-slate-200">
leAvatarClick} />
          )}
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-slate-700">{article.wechat_acco           p>
            <p cla            <p claxt-slate-500">{getRelativeTime(article.publis            <p cla            <p claxt-slate-500">{getRelativeTime(article.publis            <p cla            <p claxt-slate-500">{getRelativeTime(article.publis            <p cla            <p claxt-slate-500">{getRelativeTime(article.publis            <p cla            <p claxt-slate-500">{getRelatr-t b            <p cla            <tt            <p cla            <p claxt-slate-500">{getRelativeTime(article.publis            <p cla            <p claxt-sl              <p cla            <p claxt-slate-500">{getRelativeTime(article.publis            <p cla            <p claxt--sem            <p cla            <p claxt-slate-500">{getRelativeTime(article.publis            <p cla            <p claxt-slate-500">{getRelativeTime(article.publis            <p cla  t            semibold bg-slate-5            <p cla            <p claxt-sl   </button>
        </div>
      </div>
    </motion.article>
  );
}
