import { motion } from 'motion/react';
import { Trophy, Star, Target, Zap, Lock, Award, Mic, Clock } from 'lucide-react';
import { useAppStore } from '../../lib/store';

const allAchievements = [
  { id: 1, name: 'Centurion', description: '100 words in a day', icon: Zap, rarity: 'common', xp: 25, unlocked: true, color: 'amber' },
  { id: 2, name: 'Chatterbox', description: '500 words in a day', icon: Zap, rarity: 'common', xp: 40, unlocked: true, color: 'pink' },
  { id: 3, name: 'Starter Stack', description: '1,000 total words', icon: Star, rarity: 'common', xp: 25, unlocked: true, color: 'emerald' },
  { id: 4, name: 'Speed Demon', description: 'Reach 150 WPM', icon: Target, rarity: 'epic', xp: 200, unlocked: false, progress: 95, color: 'blue' },
  { id: 5, name: 'Marathon Speaker', description: '10,000 total words', icon: Trophy, rarity: 'rare', xp: 100, unlocked: true, color: 'purple' },
  { id: 6, name: 'Early Bird', description: 'Dictate before 7 AM', icon: Clock, rarity: 'uncommon', xp: 50, unlocked: false, progress: 0, color: 'orange' },
  { id: 7, name: 'Voice Maestro', description: '50 sessions completed', icon: Mic, rarity: 'rare', xp: 75, unlocked: true, color: 'rose' },
  { id: 8, name: 'Perfectionist', description: '99% accuracy in a session', icon: Award, rarity: 'legendary', xp: 500, unlocked: false, progress: 72, color: 'yellow' },
  { id: 9, name: 'Streak Master', description: '14-day streak', icon: Zap, rarity: 'epic', xp: 250, unlocked: true, color: 'orange' },
  { id: 10, name: 'Night Owl', description: 'Dictate after midnight', icon: Clock, rarity: 'uncommon', xp: 35, unlocked: true, color: 'indigo' },
  { id: 11, name: 'Vocabulary King', description: 'Use 500 unique words', icon: Star, rarity: 'rare', xp: 150, unlocked: false, progress: 67, color: 'teal' },
  { id: 12, name: 'Ironman', description: '100K total words', icon: Trophy, rarity: 'legendary', xp: 1000, unlocked: false, progress: 55, color: 'amber' },
  { id: 13, name: 'Quick Draw', description: 'First dictation under 5 seconds', icon: Zap, rarity: 'common', xp: 15, unlocked: true, color: 'cyan' },
  { id: 14, name: 'Quick Start', description: 'First turbo dictation', icon: Target, rarity: 'uncommon', xp: 50, unlocked: false, progress: 50, color: 'violet' },
];

const colorMap: Record<string, { bg: string; text: string; glow: string; border: string }> = {
  amber: { bg: 'from-amber-400/20 to-orange-500/10', text: 'text-amber-400', glow: 'group-hover:shadow-[0_0_20px_rgba(251,191,36,0.3)]', border: 'border-amber-500/20' },
  pink: { bg: 'from-pink-400/20 to-rose-500/10', text: 'text-pink-400', glow: 'group-hover:shadow-[0_0_20px_rgba(244,114,182,0.3)]', border: 'border-pink-500/20' },
  emerald: { bg: 'from-emerald-400/20 to-teal-500/10', text: 'text-emerald-400', glow: 'group-hover:shadow-[0_0_20px_rgba(52,211,153,0.3)]', border: 'border-emerald-500/20' },
  blue: { bg: 'from-blue-400/20 to-indigo-500/10', text: 'text-blue-400', glow: 'group-hover:shadow-[0_0_20px_rgba(96,165,250,0.3)]', border: 'border-blue-500/20' },
  purple: { bg: 'from-purple-400/20 to-violet-500/10', text: 'text-purple-400', glow: 'group-hover:shadow-[0_0_20px_rgba(168,85,247,0.3)]', border: 'border-purple-500/20' },
  orange: { bg: 'from-orange-400/20 to-red-500/10', text: 'text-orange-400', glow: 'group-hover:shadow-[0_0_20px_rgba(251,146,60,0.3)]', border: 'border-orange-500/20' },
  rose: { bg: 'from-rose-400/20 to-pink-500/10', text: 'text-rose-400', glow: 'group-hover:shadow-[0_0_20px_rgba(251,113,133,0.3)]', border: 'border-rose-500/20' },
  yellow: { bg: 'from-yellow-400/20 to-amber-500/10', text: 'text-yellow-400', glow: 'group-hover:shadow-[0_0_20px_rgba(250,204,21,0.3)]', border: 'border-yellow-500/20' },
  indigo: { bg: 'from-indigo-400/20 to-blue-500/10', text: 'text-indigo-400', glow: 'group-hover:shadow-[0_0_20px_rgba(129,140,248,0.3)]', border: 'border-indigo-500/20' },
  teal: { bg: 'from-teal-400/20 to-cyan-500/10', text: 'text-teal-400', glow: 'group-hover:shadow-[0_0_20px_rgba(45,212,191,0.3)]', border: 'border-teal-500/20' },
  cyan: { bg: 'from-cyan-400/20 to-sky-500/10', text: 'text-cyan-400', glow: 'group-hover:shadow-[0_0_20px_rgba(34,211,238,0.3)]', border: 'border-cyan-500/20' },
  violet: { bg: 'from-violet-400/20 to-purple-500/10', text: 'text-violet-400', glow: 'group-hover:shadow-[0_0_20px_rgba(167,139,250,0.3)]', border: 'border-violet-500/20' },
};

const rarityLabel: Record<string, { label: string; color: string }> = {
  common: { label: 'Common', color: 'text-white/40' },
  uncommon: { label: 'Uncommon', color: 'text-emerald-400' },
  rare: { label: 'Rare', color: 'text-blue-400' },
  epic: { label: 'Epic', color: 'text-purple-400' },
  legendary: { label: 'Legendary', color: 'text-amber-400' },
};

export const AchievementsPage = () => {
  const unlocked = allAchievements.filter(a => a.unlocked);
  const locked = allAchievements.filter(a => !a.unlocked);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="pb-8"
    >
      <header className="mb-8">
        <h1 className="text-3xl font-display font-semibold mb-2">Achievements</h1>
        <p className="text-white/50 text-[15px]">{unlocked.length} / {allAchievements.length} unlocked</p>
      </header>

      {/* Unlocked */}
      <h2 className="text-sm font-bold text-white/50 uppercase tracking-widest mb-4">Unlocked</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-10">
        {unlocked.map((a, i) => {
          const style = colorMap[a.color] || colorMap.pink;
          const rarity = rarityLabel[a.rarity] || rarityLabel.common;
          return (
            <motion.div
              key={a.id}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.04, duration: 0.3 }}
              className={`group bg-[#121216]/80 backdrop-blur-md rounded-2xl p-5 border border-white/[0.08] hover:border-pink-500/20 transition-all shadow-lg flex flex-col items-center text-center cursor-default ${style.glow}`}
            >
              <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${style.bg} flex items-center justify-center mb-3 transition-transform duration-300 group-hover:scale-110 border ${style.border}`}>
                <a.icon className={`w-7 h-7 ${style.text}`} />
              </div>
              <span className="text-sm font-medium text-white mb-1">{a.name}</span>
              <span className="text-xs text-white/40 mb-2">{a.description}</span>
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-bold uppercase tracking-wider ${rarity.color}`}>{rarity.label}</span>
                <span className="text-[10px] text-pink-400 font-bold">+{a.xp} XP</span>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Locked */}
      <h2 className="text-sm font-bold text-white/50 uppercase tracking-widest mb-4">Locked</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {locked.map((a, i) => {
          const style = colorMap[a.color] || colorMap.pink;
          const rarity = rarityLabel[a.rarity] || rarityLabel.common;
          return (
            <motion.div
              key={a.id}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: (unlocked.length + i) * 0.04, duration: 0.3 }}
              className="group bg-[#121216]/40 backdrop-blur-md rounded-2xl p-5 border border-white/5 transition-all shadow-lg flex flex-col items-center text-center cursor-default opacity-60 hover:opacity-80"
            >
              <div className="w-14 h-14 rounded-2xl bg-white/5 flex items-center justify-center mb-3 border border-white/5">
                <Lock className="w-6 h-6 text-white/20" />
              </div>
              <span className="text-sm font-medium text-white/50 mb-1">{a.name}</span>
              <span className="text-xs text-white/30 mb-2">{a.description}</span>
              {a.progress !== undefined && a.progress > 0 && (
                <div className="w-full mt-1">
                  <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                    <div className="h-full bg-white/20 rounded-full" style={{ width: `${a.progress}%` }} />
                  </div>
                  <span className="text-[10px] text-white/30 mt-1 block">{a.progress}%</span>
                </div>
              )}
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
};
