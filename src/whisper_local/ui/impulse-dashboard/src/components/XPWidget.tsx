import { GlassCard } from './GlassCard';
import { useAppStore } from '../lib/store';

export const XPWidget = () => {
  const stats = useAppStore(state => state.stats);
  const xp = stats?.xp || 0;
  const xpToNextLevel = stats?.xpToNextLevel || 1;
  const level = stats?.level || 1;
  const progressPercent = Math.min(100, (xp / xpToNextLevel) * 100).toFixed(1);

  return (
    <GlassCard className="flex-1 flex items-center gap-6 group">
      <div className="relative">
        <div className="absolute inset-0 bg-pink-500/20 blur-xl rounded-2xl group-hover:bg-pink-500/40 transition-all duration-500 animate-pulse-glow" />
        <div className="w-16 h-16 rounded-2xl overflow-hidden border border-pink-500/30 transform group-hover:scale-105 transition-transform duration-300 font-bold bg-gradient-to-br from-zinc-800 to-zinc-950 flex items-center justify-center text-2xl text-white shadow-lg relative z-10">
          WL
        </div>
        <div className="absolute -bottom-2 -right-2 bg-gradient-to-r from-pink-500 to-rose-400 text-white text-[10px] font-bold px-2.5 py-1 rounded-full shadow-[0_4px_12px_rgba(236,72,153,0.5)] z-20 transform group-hover:-translate-y-1 transition-transform duration-300">
          PRO
        </div>
      </div>

      <div className="flex-1">
        <div className="flex justify-between items-end mb-2">
          <div>
            <h3 className="text-sm font-medium text-white/50 uppercase tracking-widest mb-1 group-hover:text-white/70 transition-colors">Current Rank</h3>
            <p className="text-2xl font-display font-medium text-white group-hover:text-pink-100 transition-colors">Level {level}</p>
          </div>
          <span className="text-sm font-bold text-pink-400 drop-shadow-[0_0_8px_rgba(236,72,153,0.6)]">{progressPercent}%</span>
        </div>

        <div className="h-3 w-full bg-black/40 rounded-full overflow-hidden border border-white/5 shadow-inner">
          <div
            className="h-full bg-gradient-to-r from-pink-500 via-rose-400 to-orange-400 rounded-full shadow-[0_0_20px_rgba(236,72,153,0.7)] transition-all duration-1000 ease-out relative overflow-hidden"
            style={{ width: `${progressPercent}%` }}
          >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent -translate-x-[100%] animate-[shimmer_2s_infinite]" />
          </div>
        </div>
      </div>
    </GlassCard>
  );
};
