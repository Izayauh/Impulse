import { useAppStore } from '../lib/store';
import { Flame } from 'lucide-react';

export const WelcomeCard = () => {
  const stats = useAppStore(state => state.stats);
  const userName = stats?.userName || 'User';
  const level = stats?.level || 10;
  const xp = stats?.xp || 22170;
  const xpToNextLevel = stats?.xpToNextLevel || 38436;
  const dayStreak = stats?.dayStreak || 1;
  const thisWeek = stats?.thisWeek || 2602;
  const progressPct = Math.min(100, (xp / xpToNextLevel) * 100);
  
  return (
    <div className="bg-[#131317]/80 backdrop-blur-md rounded-2xl p-6 border border-white/[0.08] relative overflow-hidden group hover:border-white/10 transition-colors shadow-lg">
      <div className="absolute top-0 right-0 w-64 h-64 bg-pink-500/5 blur-3xl translate-x-1/2 -translate-y-1/2 rounded-full" />
      
      <div className="flex gap-4 items-start mb-5 relative z-10">
        <div className="w-12 h-16 bg-gradient-to-b from-white/10 to-transparent rounded-full flex flex-col justify-end items-center pb-2 relative overflow-hidden shadow-inner shrink-0">
           <div className="absolute top-0 inset-x-0 h-1/2 bg-gradient-to-b from-white/20 to-transparent"></div>
           <div className="w-3 h-3 bg-pink-500 rounded-full shadow-[0_0_10px_rgba(236,72,153,0.8)]"></div>
        </div>
        
        <div className="flex-1 min-w-0">
          <h1 className="text-[28px] font-display font-medium leading-tight mb-1 tracking-tight">
            Welcome<br/>back, <b>{userName}</b>
          </h1>
          <p className="text-white/50 text-[15px] font-medium">
            Voice performance at a glance.
          </p>
        </div>
      </div>

      {/* Stats badges — wrapped layout to prevent overflow */}
      <div className="flex flex-wrap gap-2 mb-5 relative z-10">
        <span className="px-3 py-1 bg-fuchsia-900/40 text-fuchsia-200 text-xs font-semibold rounded-full border border-fuchsia-500/30">
          Lvl {level}
        </span>
        <span className="px-3 py-1 bg-cyan-900/20 text-cyan-300 text-xs font-semibold rounded-full border border-cyan-500/30 tabular-nums">
          {xp.toLocaleString()} XP
        </span>
        <span className="flex items-center gap-1.5 px-3 py-1 bg-orange-900/40 text-orange-200 text-xs font-semibold rounded-full border border-orange-500/30">
          <Flame className="w-3.5 h-3.5 text-orange-500 fill-orange-500" />
          {dayStreak} Day{dayStreak !== 1 ? 's' : ''} Streak
        </span>
        <span className="px-3 py-1 bg-amber-900/20 text-amber-300 text-xs font-semibold rounded-full border border-amber-500/30 tabular-nums">
          {thisWeek.toLocaleString()} Weekly
        </span>
      </div>
      
      <div className="relative z-10">
        <div className="flex justify-between items-end mb-2">
          <span className="text-[10px] font-bold text-white/50 tracking-widest uppercase">
            Current Rank Progress
          </span>
          <span className="text-xs font-medium text-pink-300/80 tabular-nums">
            {xp.toLocaleString()} / {xpToNextLevel.toLocaleString()}
          </span>
        </div>
        <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden border border-white/5">
          <div 
            className="h-full rounded-full bg-gradient-to-r from-pink-500 via-purple-500 to-emerald-400 transition-all duration-1000"
            style={{ width: `${progressPct}%` }}
          ></div>
        </div>
      </div>
    </div>
  );
};
