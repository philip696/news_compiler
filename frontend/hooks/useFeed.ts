import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo } from "react";
import { api } from "../services/api";

export type Story = {
  cluster_id: string;
  topic: string;
  headline: string;
  summary: string;
  article_count: number;
  sources: string[];
  score: number;
  articles: {
    id: string;
    title: string;
    content: string;
    url: string;
    source_id: string;
    source_name: string;
    published_at: string;
    topic: string;
    main_image?: string;
  }[];
};

type FeedPage = {
  stories: Story[];
  total: number;
  skip: number;
  limit: number;
};

/** First chunk is small so the grid paints quickly; later pages fill in without waiting for one huge response. */
const FEED_PAGE_SIZE = 14;

/** Delay between automatic feed page fetches so the browser can paint each batch. */
const FEED_PAGE_STAGGER_MS = 24;

/**
 * Main feed: paginated `/api/feed` with automatic "next page" chaining so stories appear in batches.
 * Explore (Kaggle) loads in one request only after the ranked feed is fully paged in — the explore API
 * reshuffles on every call, so multi-page explore would duplicate or skip items.
 */
export function useHomeFeedProgressive(enabled: boolean) {
  const feedQ = useInfiniteQuery({
    queryKey: ["feed", "paged"],
    initialPageParam: 0,
    queryFn: async ({ pageParam: skip }) => {
      const res = await api.get<FeedPage>("/api/feed", {
        params: { skip, limit: FEED_PAGE_SIZE },
      });
      return res.data;
    },
    getNextPageParam: (last) => {
      const nextSkip = last.skip + last.stories.length;
      return nextSkip < last.total ? nextSkip : undefined;
    },
    enabled,
    staleTime: 120_000,
    gcTime: 600_000,
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (!feedQ.hasNextPage || feedQ.isFetchingNextPage) return;
    const id = window.setTimeout(() => {
      feedQ.fetchNextPage();
    }, FEED_PAGE_STAGGER_MS);
    return () => window.clearTimeout(id);
  }, [
    feedQ.hasNextPage,
    feedQ.isFetchingNextPage,
    feedQ.fetchNextPage,
    feedQ.data?.pages.length,
  ]);

  const feedFlat = useMemo(
    () => feedQ.data?.pages.flatMap((p) => p.stories) ?? [],
    [feedQ.data]
  );

  const feedComplete =
    !!feedQ.data &&
    !feedQ.hasNextPage &&
    !feedQ.isFetchingNextPage;

  const exploreQ = useQuery({
    queryKey: ["explore"],
    queryFn: async () => {
      const res = await api.get<{ stories: Story[] }>("/api/feed/explore", {
        params: { limit: 50 },
      });
      return res.data.stories ?? [];
    },
    enabled: enabled && feedComplete,
    staleTime: 180_000,
    gcTime: 600_000,
    refetchOnWindowFocus: false,
  });

  const exploreStories = exploreQ.data ?? [];

  const allStories = useMemo(
    () => [...feedFlat, ...exploreStories],
    [feedFlat, exploreStories]
  );

  const isLoadingInitial =
    allStories.length === 0 &&
    (feedQ.isPending || (feedComplete && exploreQ.isPending));

  return { allStories, isLoadingInitial };
}
