import { Flame } from 'lucide-react';
import { GlassCard } from './GlassCard';

export const StreakWidget = () => {
  return (
    <GlassCard className="w-64 flex flex-col items-center justify-center text-center group">
      <div className="relative mb-3">
        <div className="absolute inset-0 bg-orange-500/20 blur-2xl rounded-full group-hover:bg-orange-500/30 transition-all" />
        <Flame className="w-12 h-12 text-orange-500 relative z-10 animate-pulse" fill="currentColor" />
      </div>
      <h3 className="text-sm font-medium text-white/60 uppercase tracking-wider">Daily Streak</h3>
      <p className="text-3xl font-display font-bold">14 Days</p>
    </GlassCard>
  );
};
