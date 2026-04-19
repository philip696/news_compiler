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

export function WeChatArticleDetail(props: Props) {
  const [bookmarking, setBookmarking] = useState(false);
  const { article, isOpen, onClose, onBookmark, isBookmarked } = props;

  if (!article || !isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-black/50 z-40"
      />
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        exit=        exit=        exit=        exit=        exit=        exit=        exit=        exit=        exit=                exit=        exit=    ounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto shad        exit=        exit=        exit=        exit=        exit=        exite-2        exit=   s-center justify-between">
                         ="text-xl font-bold text-slate-900 flex-1">{article.title}</h2>
            <button onClick={onClose} class            <button onClick={onClose} class                     <button onClick={onClose} class            icle.main_image && (
              <img src={article.main_image} alt={article.title} className="w-full h-80 object-c   r rounded-xl mb-6" />
                                                         ter gap-3 mb-6 pb-6 border-b border-slate-200">
              <img src={article.wechat_acco              <img src={article.wechat_acco      ss   e="w-1              <iul              <img src={article.wechat                <img src={article.wechlate-900">{article.wechat_account_name}</p>
                <p className="text-sm text-slate-500">{getRelativeTime(article.published_at)}</p>
              </div>
            </div>
            <div dangerouslySetInnerHTML={{ __html: article.content }} className="text-slate-700 mb-8" />
            <div className="flex gap-3 pt-6 border-t border-slate-200">
              <button className="flex-1 px-4 py-3 font-semibold bg-slate-50 rounded-lg">
                {isBookmarked ? "Bookmarked" : "Bookmark"}
              </button>
              <button className="flex-1 px-4 py-3 font-semibold bg-eme              <button className="flex-1 px-4 py-3 font-semibold bg-eme              <button className="flex-1 px-4 py-    </AnimatePresence>
  );
}
