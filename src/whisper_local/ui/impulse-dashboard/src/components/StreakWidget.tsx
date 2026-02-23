import { Flame } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { useAppStore } from '../lib/store';

export const StreakWidget = () => {
  const dayStreak = useAppStore(state => state.stats?.dayStreak || 0);

  return (
    <GlassCard className="w-64 flex flex-col items-center justify-center text-center group cursor-default relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-orange-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
      <div className="relative mb-3 animate-float group-hover:scale-110 transition-transform duration-300">
        <div className="absolute inset-0 bg-orange-500/30 blur-2xl rounded-full group-hover:bg-orange-500/50 transition-all duration-500 animate-pulse-glow" />
        <div className="absolute inset-0 bg-rose-500/20 blur-xl rounded-full group-hover:bg-rose-500/40 transition-all duration-300" />
        <Flame className="w-12 h-12 text-orange-400 relative z-10 drop-shadow-[0_0_15px_rgba(249,115,22,0.8)] transition-all duration-300 group-hover:text-orange-300" fill="currentColor" />
      </div>
      <h3 className="text-sm font-medium text-white/50 uppercase tracking-widest mb-1 group-hover:text-white/70 transition-colors relative z-10">Daily Streak</h3>
      <p className="text-3xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-br from-white to-white/70 group-hover:from-orange-100 group-hover:to-orange-400 transition-all relative z-10">
        {dayStreak} <span className="text-2xl">{dayStreak === 1 ? 'Day' : 'Days'}</span>
      </p>
    </GlassCard>
  );
};
