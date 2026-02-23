import { Trophy, Star, Target, Zap } from 'lucide-react';
import { GlassCard } from './GlassCard';

const achievements = [
  { icon: Zap, label: 'Fast Learner', color: 'text-yellow-400', bg: 'bg-yellow-400/10' },
  { icon: Star, label: 'Top 1% Weekly', color: 'text-pink-400', bg: 'bg-pink-400/10' },
  { icon: Target, label: 'Goal Crusher', color: 'text-emerald-400', bg: 'bg-emerald-400/10' },
  { icon: Trophy, label: 'Master Mind', color: 'text-blue-400', bg: 'bg-blue-400/10' },
];

export const AchievementWidget = () => {
  return (
    <div className="grid grid-cols-2 gap-4">
      {achievements.map((item) => (
        <GlassCard key={item.label} className="p-4 flex flex-col items-center justify-center text-center group">
          <div className={`w-12 h-12 rounded-2xl ${item.bg} flex items-center justify-center mb-3 group-hover:scale-110 transition-transform`}>
            <item.icon className={`w-6 h-6 ${item.color}`} />
          </div>
          <span className="text-xs font-medium text-white/70">{item.label}</span>
        </GlassCard>
      ))}
    </div>
  );
};
