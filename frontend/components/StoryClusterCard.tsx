import { motion } from "framer-motion";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import { Story } from "../hooks/useFeed";
import { api, BASE_URL } from "../services/api";

type Size = "compact" | "regular" | "featured";

type Props = {
  story: Story;
  onBookmark: (articleId: string) => Promise<void>;
  onLike: (articleId: string) => Promise<void>;
  size?: Size;
  className?: string;
};

const getLogoPath = (sourceId: string): string => {
  const logoMap: { [key: string]: string } = {
    "techcrunch": "/images/logos/techcrunch.png",
    "bbc": "/images/logos/bbc.png",
    "cnn": "/images/logos/cnn.png",
    "reuters": "/images/logos/reuters.png",
    "theverge": "/images/logos/theverge.jpg",
  };
  return logoMap[sourceId] || `/images/logos/${sourceId}.png`;
};

export default function StoryClusterCard({ story, onBookmark, onLike, size = "regular", className = "" }: Props) {
  const router = useRouter();
  const [isLiked, setIsLiked] = useState(false);
  const [isBookmarked, setIsBookmarked] = useState(false);
  const [loading, setLoading] = useState(true);
  
  // Dynamic sizing configurations
  const sizeConfig = {
    compact: {
      padding: "p-4",
      titleSize: "text-base font-semibold",
      descriptionSize: "text-xs",
      badgeSize: "text-[10px]",
      contentLines: "line-clamp-2"
    },
    regular: {
      padding: "p-5",
      titleSize: "text-lg font-bold",
      descriptionSize: "text-xs",
      badgeSize: "text-[10px]",
      contentLines: "line-clamp-3"
    },
    featured: {
      padding: "p-8",
      titleSize: "text-2xl md:text-3xl font-extrabold",
      descriptionSize: "text-sm",
      badgeSize: "text-xs px-3 py-1",
      contentLines: "line-clamp-4"
    }
  };

  const config = sizeConfig[size];
  
  // Use article's main_image if available, otherwise a predictable placeholder
  let imgUrl = `https://images.unsplash.com/photo-${1500000000000 + (story.cluster_id.charCodeAt(0) % 10000)}?auto=format&fit=crop&w=800&q=80`;
  if (story.articles.length > 0 && story.articles[0].main_image) {
    imgUrl = story.articles[0].main_image;
    if (imgUrl.startsWith('/data')) {
      imgUrl = `${BASE_URL}${imgUrl}`;
    }
  }

  const handleCardClick = () => {
    if (story.articles.length > 0) {
      router.push(`/article/${story.articles[0].id}`);
    }
  };

  // Fetch article state from backend on mount
  useEffect(() => {
    const fetchArticleState = async () => {
      if (story.articles.length === 0) {
        setLoading(false);
        return;
      }

      try {
        const response = await api.get(`/api/feed/article/${story.articles[0].id}`);
        setIsLiked(response.data.liked || false);
        setIsBookmarked(response.data.bookmarked || false);
      } catch (error) {
        console.error('Failed to fetch article state:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchArticleState();
  }, [story.articles]);

  const handleLike = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (story.articles.length > 0) {
      try {
        await onLike(story.articles[0].id);
        // Fetch updated state from backend
        const response = await api.get(`/api/feed/article/${story.articles[0].id}`);
        setIsLiked(response.data.liked || false);
      } catch (error) {
        console.error("Failed to like article:", error);
      }
    }
  };

  const handleBookmark = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (story.articles.length > 0) {
      try {
        await onBookmark(story.articles[0].id);
        // Fetch updated state from backend
        const response = await api.get(`/api/feed/article/${story.articles[0].id}`);
        setIsBookmarked(response.data.bookmarked || false);
      } catch (error) {
        console.error("Failed to bookmark article:", error);
      }
    }
  };

  return (
    <motion.article
      onClick={handleCardClick}
      initial={{ opacity: 0, scale: 0.98, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={`${className} group relative flex flex-col overflow-hidden rounded-3xl bg-slate-900 shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 cursor-pointer h-full w-full min-h-[250px] border border-white/10`}
    >
      {/* Background Image placeholder */}
      <div 
        className="absolute inset-0 bg-cover bg-center transition-transform duration-700 group-hover:scale-105"
        style={{ backgroundImage: `url(${imgUrl})` }} 
      />
      {/* Gradient Overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/40 to-black/20 transition-opacity duration-300 group-hover:opacity-90" />
      
      {/* Content Container */}
      <div className={`relative flex flex-1 flex-col justify-between ${config.padding} h-full z-10`}>
        
        {/* Top Region */}
        <div className="flex justify-between items-start w-full">
          {/* Top Badges */}
          <div>
            {story.topic && (
              <span className={`inline-block rounded-lg bg-black/50 backdrop-blur-md px-2.5 py-0.5 ${config.badgeSize} font-bold uppercase tracking-wider text-white border border-white/20 shadow-sm`}>
                {story.topic}
              </span>
            )}
          </div>
          
          {/* Actions / Read Label */}
          <div className="flex flex-col gap-2 items-end">
             <div className="rounded-full bg-black/60 backdrop-blur-md px-3 py-1.5 text-[10px] sm:text-xs font-semibold text-white flex items-center gap-1.5 border border-white/20 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-y-[-5px] group-hover:translate-y-0">
               <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
               </svg>
               <span className="hidden sm:inline">Click to Read</span>
               <span className="sm:hidden">Read</span>
             </div>
             
             {/* Interaction Buttons */}
             <div className="flex gap-2">
                <button
                  onClick={handleLike}
                  className={`flex ${size === 'compact' ? 'h-7 w-7' : 'h-8 w-8'} items-center justify-center rounded-full backdrop-blur-md transition-all shadow-sm border ${
                    isLiked
                      ? 'bg-red-500/90 border-red-500 text-white'
                      : 'bg-black/40 border-white/20 text-white hover:bg-black/60 hover:scale-105'
                  } opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-[10px] group-hover:translate-x-0`}
                  title="Like"
                >
                  <svg className={`h-4 w-4 transition-transform ${isLiked ? 'scale-110' : ''}`} fill={isLiked ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                  </svg>
                </button>
                <button
                  onClick={handleBookmark}
                  className={`flex ${size === 'compact' ? 'h-7 w-7' : 'h-8 w-8'} items-center justify-center rounded-full backdrop-blur-md transition-all shadow-sm border ${
                    isBookmarked
                      ? 'bg-amber-500/90 border-amber-500 text-white'
                      : 'bg-black/40 border-white/20 text-white hover:bg-black/60 hover:scale-105'
                  } opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-[10px] group-hover:translate-x-0 delay-75`}
                  title="Bookmark"
                >
                  <svg className={`h-4 w-4 transition-transform ${isBookmarked ? 'scale-110' : ''}`} fill={isBookmarked ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                  </svg>
                </button>
             </div>
          </div>
        </div>

        {/* Bottom Region */}
        <div className="flex flex-col gap-3 mt-auto">
          <h3 className={`${config.contentLines} ${config.titleSize} leading-tight tracking-tight text-white drop-shadow-md`}>
            {story.headline}
          </h3>
          
          <div className={`flex items-center gap-3 ${config.descriptionSize} text-slate-300 drop-shadow-sm`}>
            <div className="flex items-center gap-2 border-r border-white/20 pr-3">
              <div className="flex -space-x-1.5 overflow-hidden">
                {story.sources.slice(0, 3).map((source, i) => (
                  <div 
                    key={source} 
                    className="flex h-4 w-4 sm:h-5 sm:w-5 items-center justify-center rounded-[4px] ring-[1.5px] ring-black/50 bg-white/90 overflow-hidden shadow-sm flex-shrink-0"
                    title={source}
                  >
                    <img 
                      src={getLogoPath(source)}
                      alt={source}
                      className="h-full w-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none';
                        const parent = (e.target as HTMLElement).parentElement;
                        if (parent) {
                          parent.classList.add('flex', 'items-center', 'justify-center', 'bg-slate-800', 'text-[6px]', 'font-bold', 'text-white');
                          parent.textContent = source.substring(0, 1).toUpperCase();
                        }
                      }}
                    />
                  </div>
                ))}
              </div>
              <span className="font-semibold text-white/90">
                {story.sources.length === 1 ? story.sources[0] : `${story.sources.length} Sources`}
              </span>
            </div>
            
            {story.articles.length > 0 && story.articles[0].published_at && (
              <span className="text-white/70 font-medium">
                {new Date(story.articles[0].published_at).toLocaleDateString(undefined, {month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'})}
              </span>
            )}
          </div>
        </div>
      </div>
    </motion.article>
  );
}
