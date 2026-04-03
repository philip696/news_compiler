type Topic = {
  id: string;
  name: string;
  followed: boolean;
  interest_score: number;
};

type Props = {
  topics: Topic[];
  onFollow: (topicId: string) => Promise<void>;
  onUnfollow: (topicId: string) => Promise<void>;
};

export default function TopicSelector({ topics, onFollow, onUnfollow }: Props) {
  return (
    <section className="rounded-3xl border border-slate-200/60 bg-white/70 backdrop-blur-md p-5 shadow-sm">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-900">Topics</h2>
      <div className="flex flex-wrap gap-2">
        {topics.map((topic) => (
          <button
            key={topic.id}
            onClick={() => (topic.followed ? onUnfollow(topic.id) : onFollow(topic.id))}
            className={`rounded-full px-4 py-2 text-xs font-medium transition-all duration-200 transform hover:scale-105 ${
              topic.followed 
                ? "bg-blue-600 text-white shadow-md hover:bg-blue-700" 
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            {topic.name}
          </button>
        ))}
      </div>
    </section>
  );
}
