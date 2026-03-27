import { TrendingUp } from 'lucide-react';
import { useAppStore } from '../lib/store';
import { useMemo } from 'react';

export const VelocityCard = () => {
  const stats = useAppStore(state => state.stats);

  const data = useMemo(() => {
    const days = stats?.last7Days || [
      { day: 'Sat', words: 424 },
      { day: 'Sun', words: 300 },
      { day: 'Mon', words: 450 },
      { day: 'Tue', words: 320 },
      { day: 'Wed', words: 350 },
      { day: 'Thu', words: 400 },
      { day: 'Fri', words: 2178 },
    ];

    const maxValue = Math.max(...days.map(d => d.words), 1);
    const lastIdx = days.length - 1;

    return days.map((d, i) => ({
      day: d.day,
      value: d.words,
      height: Math.max(8, (d.words / maxValue) * 100),
      active: i === lastIdx,
    }));
  }, [stats]);

  return (
    <div className="bg-[#131317]/80 backdrop-blur-md rounded-2xl p-6 border border-white/[0.08] hover:border-white/10 transition-colors shadow-lg grow min-h-[240px]">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h3 className="text-xl font-display font-semibold mb-1">Velocity</h3>
          <p className="text-white/50 text-[15px]">Words transcribed last 7 days</p>
        </div>
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-100/10 text-blue-200">
          <TrendingUp className="w-4 h-4" />
        </div>
      </div>

      <div
        className="relative h-40 flex items-end justify-between px-2 pt-4"
        role="img"
        aria-label={`Bar chart showing words transcribed over 7 days. Highest: ${Math.max(...data.map(d => d.value))} words.`}
      >
        {data.map((item, i) => (
          <div key={i} className="flex flex-col items-center gap-2 group/bar relative w-full h-full justify-end cursor-default">
            {/* Value label — visible on hover AND touch */}
            <span
              className={`text-[10px] absolute -top-4 font-bold transition-opacity tabular-nums ${
                item.active
                  ? 'opacity-100 text-emerald-400 drop-shadow-sm'
                  : 'opacity-0 group-hover/bar:opacity-100 text-white/70'
              }`}
              aria-label={`${item.day}: ${item.value} words`}
            >
              {item.value.toLocaleString()}
            </span>

            <div 
              style={{ height: `${item.height}%` }} 
              className={`w-10 rounded-t border-t border-x relative overflow-hidden transition-all duration-500
                ${item.active 
                  ? "bg-gradient-to-b from-teal-400 to-teal-400/10 border-teal-400/50 shadow-[0_0_15px_rgba(45,212,191,0.2)]" 
                  : "bg-gradient-to-b from-pink-500/80 to-pink-500/10 border-pink-500/50 hover:from-pink-400"}`}
            />
            <span className={`text-xs font-semibold ${item.active ? 'text-white' : 'text-white/50'}`}>
              {item.day}
            </span>
          </div>
        ))}
        {/* Baseline */}
        <div className="absolute bottom-6 left-0 right-0 h-px bg-white/5" />
      </div>
    </div>
  );
};
