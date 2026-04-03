import { useQuery } from "@tanstack/react-query";
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

export const useFeed = (enabled: boolean) =>
  useQuery({
    queryKey: ["feed"],
    queryFn: async () => {
      const res = await api.get<{ stories: Story[] }>("/api/feed");
      return res.data.stories;
    },
    enabled
  });
