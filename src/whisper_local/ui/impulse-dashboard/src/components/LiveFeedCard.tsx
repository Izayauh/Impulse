import { useAppStore } from '../lib/store';
import { Copy, Check } from 'lucide-react';
import { useState } from 'react';

export const LiveFeedCard = () => {
  const stats = useAppStore(state => state.stats);
  const showToast = useAppStore(state => state.showToast);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  const feed = stats?.recentTranscripts?.length ? stats.recentTranscripts.map(t => ({
    label: 'RECENT',
    text: t.text,
    words: t.words
  })) : [
    {
      label: 'RECENT',
      text: 'like there has to be more to what is going on with that than just what you told me here, with these seven, what is the, help me get to the nitty gritty. Like if you had to like actively make those vocals sound professional, what would you do?',
      words: 150
    },
    {
      label: 'RECENT',
      text: 'Do whatever you gotta do like this should not it should not be a you come back to me in like a minute or two it should be like a probably at minimum like 10 minute task.',
      words: 37
    },
    {
      label: 'RECENT',
      text: "Yeah. I need you to create a prompt so that I can deep research this and so that it can find like the proper way to build this out with it. Considering that I don't want it to be like a week long project., I just want it to get the foundation of everything. Right. And it needs to also research the assets, the type, how we could do, artistic design without me having to really artistically designed anything, but like also me having input on it., if what I'm saying, and everything like that,",
      words: 97
    },
    {
      label: 'RECENT',
      text: "Exactly. I want it to feel like I'm playing a game a little bit, but I don't want it to be a game exactly, if what I'm saying. It should just feel exciting when I click onto it. I think I really want to model it a little bit after, I'm thinking, OG Civ and Rise of Kingdoms type of vibes. And then, I also kind of want it to feel a little bit Skyrim., I love those kind of games. I don't want it to be a game, but it should feel like I'm entering a game and then it should feel exciting like that. And it should feel almost like it should just feel like that. And we can keep it really, really simple with everything. Almost you're playing OG RuneScape with the simplicity of the feeling of it and everything like that.",
      words: 146
    },
    {
      label: 'RECENT',
      text: "Can you save that MD file and any future ones that I need to interact with personally to this directory here?",
      words: 21
    }
  ];

  const handleCopy = async (text: string, index: number) => {
    await useAppStore.getState().copyToClipboard(text);
    setCopiedIdx(index);
    showToast('Copied to clipboard ✓');
    setTimeout(() => {
      setCopiedIdx(null);
    }, 2000);
  };

  return (
    <div className="bg-[#131317]/80 backdrop-blur-md rounded-2xl h-full flex flex-col border border-white/[0.08] hover:border-white/10 transition-colors shadow-xl overflow-hidden relative">
      <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-pink-500/10 blur-[100px] translate-x-1/3 -translate-y-1/3 rounded-full pointer-events-none" />
      
      <div className="p-6 border-b border-white/[0.08] flex justify-between items-center bg-[#15151A]/80 sticky top-0 z-20 backdrop-blur-xl">
        <div>
          <h2 className="text-2xl font-display font-semibold mb-1">Live Feed</h2>
          <p className="text-white/50 text-[15px]">Recent Dictations</p>
        </div>
        <div className="px-3 py-1 rounded-full border border-pink-500/30 bg-pink-500/10 text-pink-500 text-xs font-bold tracking-widest uppercase flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-pink-500 shadow-[0_0_8px_rgba(236,72,153,0.8)] animate-pulse" />
          LIVE
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-2 relative z-10 custom-scrollbar">
        {feed.map((item, i) => (
          <div key={i} className="group p-5 rounded-2xl hover:bg-white/[0.03] border border-transparent hover:border-white/5 transition-all flex items-start gap-4">
            <span className="text-[11px] font-bold text-white/30 tracking-widest uppercase w-16 pt-0.5 shrink-0">
              {item.label}
            </span>
            <div className="flex-1 min-w-0 pr-4">
              <p className="text-white/80 text-[15px] leading-relaxed mb-4 group-hover:text-white transition-colors line-clamp-4">
                {item.text}
              </p>
              <span className="text-pink-500/90 text-sm font-semibold tracking-wide">
                + {item.words} words
              </span>
            </div>
            <button
              onClick={() => handleCopy(item.text, i)}
              className="px-4 py-2 mt-1 rounded-xl bg-white/5 border border-white/10 text-white/60 text-sm font-medium hover:bg-white/10 hover:text-white transition-all shrink-0 focus-visible:ring-2 focus-visible:ring-pink-500/50 focus-visible:outline-none active:scale-95 flex items-center gap-1.5"
            >
              {copiedIdx === i ? (
                <><Check className="w-3.5 h-3.5 text-emerald-400" /> Copied</>
              ) : (
                <><Copy className="w-3.5 h-3.5" /> Copy</>
              )}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
