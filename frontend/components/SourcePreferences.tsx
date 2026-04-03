type Props = {
  sourceIds: string[];
  onMute: (sourceId: string) => Promise<void>;
  onPrefer: (sourceId: string) => Promise<void>;
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

export default function SourcePreferences({ sourceIds, onMute, onPrefer }: Props) {

  return (
    <section className="rounded-3xl border border-slate-200/60 bg-white/70 backdrop-blur-md p-5 shadow-sm">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-900">Sources</h2>
      <div className="space-y-2">
        {sourceIds.map((sourceId) => (
          <div key={sourceId} className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 p-3 hover:bg-slate-100 transition-colors">
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <div className="h-8 w-8 flex-shrink-0 rounded-lg bg-gradient-to-br from-slate-700 to-slate-900 border border-slate-200 overflow-hidden flex items-center justify-center relative">
                <img 
                  src={getLogoPath(sourceId)}
                  alt={sourceId}
                  className="h-full w-full object-cover absolute inset-0"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none';
                  }}
                />
                <span className="text-xs font-bold text-white uppercase relative z-10">
                  {sourceId.substring(0, 2)}
                </span>
              </div>
              <span className="text-xs font-medium text-slate-700 truncate">{sourceId.replace(/_/g, " ").toUpperCase()}</span>
            </div>
            <div className="flex gap-2 ml-2">
              <button 
                onClick={() => onPrefer(sourceId)} 
                className="rounded-lg bg-green-100 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-200 transition-colors flex-shrink-0"
              >
                Prefer
              </button>
              <button 
                onClick={() => onMute(sourceId)} 
                className="rounded-lg bg-red-100 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-200 transition-colors flex-shrink-0"
              >
                Mute
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
