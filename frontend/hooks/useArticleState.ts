import { useState, useEffect } from 'react';
import { api } from '../services/api';

interface ArticleState {
  liked: boolean;
  bookmarked: boolean;
  loading: boolean;
}

export function useArticleState(articleId: string) {
  const [state, setState] = useState<ArticleState>({
    liked: false,
    bookmarked: false,
    loading: true,
  });

  useEffect(() => {
    const fetchArticleState = async () => {
      try {
        const response = await api.get(`/api/feed/article/${articleId}`);
        setState({
          liked: response.data.liked || false,
          bookmarked: response.data.bookmarked || false,
          loading: false,
        });
      } catch (error) {
        console.error('Failed to fetch article state:', error);
        setState(prev => ({ ...prev, loading: false }));
      }
    };

    fetchArticleState();
  }, [articleId]);

  const updateLiked = async (liked: boolean) => {
    setState(prev => ({ ...prev, liked }));
  };

  const updateBookmarked = async (bookmarked: boolean) => {
    setState(prev => ({ ...prev, bookmarked }));
  };

  return {
    ...state,
    updateLiked,
    updateBookmarked,
  };
}
