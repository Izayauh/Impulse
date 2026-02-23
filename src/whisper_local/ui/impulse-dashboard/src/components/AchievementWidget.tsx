import { Trophy, Star, Target, Zap, Lock } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { useAppStore } from '../lib/store';

export const AchievementWidget = () => {
  const allAchievements = useAppStore(state => state.achievements);
  const unlocked = allAchievements.filter(a => a.unlocked);

  // Show up to 4 recent achievements
  const displays = unlocked.slice(0, 4);

  const iconMap: Record<string, any> = {
    '100': Zap,
    '500': Zap,
    '1K': Star,
    '10K': Trophy,
    '120': Target
  };

  const colorMap = [
    { color: 'text-amber-400', bg: 'bg-gradient-to-br from-yellow-400/20 to-orange-500/10', glow: 'group-hover:shadow-[0_0_20px_rgba(251,191,36,0.3)]' },
    { color: 'text-pink-400', bg: 'bg-gradient-to-br from-pink-400/20 to-rose-500/10', glow: 'group-hover:shadow-[0_0_20px_rgba(244,114,182,0.3)]' },
    { color: 'text-emerald-400', bg: 'bg-gradient-to-br from-emerald-400/20 to-teal-500/10', glow: 'group-hover:shadow-[0_0_20px_rgba(52,211,153,0.3)]' },
    { color: 'text-blue-400', bg: 'bg-gradient-to-br from-blue-400/20 to-indigo-500/10', glow: 'group-hover:shadow-[0_0_20px_rgba(96,165,250,0.3)]' },
  ];

  return (
    <div className="grid grid-cols-2 gap-4">
      {displays.map((item, i) => {
        const Icon = iconMap[item.icon] || Trophy;
        const style = colorMap[i % colorMap.length];
        return (
          <GlassCard key={item.name} className="p-4 flex flex-col items-center justify-center text-center group cursor-default relative overflow-hidden">
            <div className="absolute inset-0 bg-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            <div className={`w-14 h-14 rounded-2xl ${style.bg} flex items-center justify-center mb-3 transition-all duration-300 transform group-hover:-translate-y-1 group-hover:scale-110 ${style.glow} border border-white/5`}>
              <Icon className={`w-7 h-7 ${style.color}`} fill="currentColor" fillOpacity={0.2} strokeWidth={1.5} />
            </div>
            <span className="text-sm font-medium text-white/70 group-hover:text-white transition-colors relative z-10">{item.name}</span>
          </GlassCard>
        );
      })}
    </div>
  );
};
