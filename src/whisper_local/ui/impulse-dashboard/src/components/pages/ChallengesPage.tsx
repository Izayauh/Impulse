import { motion } from 'motion/react';
import { Flame, Target, Zap, Trophy } from 'lucide-react';

const challenges = [
  { id: 1, title: 'Daily Warm-Up', description: 'Dictate at least 100 words today', progress: 82, target: 100, xp: 25, icon: Flame, color: 'orange', active: true },
  { id: 2, title: 'Speed Sprint', description: 'Reach 160 WPM in a single session', progress: 142, target: 160, xp: 75, icon: Zap, color: 'cyan', active: true },
  { id: 3, title: 'Streak Keeper', description: 'Maintain your daily streak', progress: 1, target: 1, xp: 50, icon: Target, color: 'emerald', active: true, completed: true },
  { id: 4, title: 'Volume King', description: 'Transcribe 1,000 words in a single day', progress: 823, target: 1000, xp: 150, icon: Trophy, color: 'pink', active: true },
];

const colorMap: Record<string, { bg: string; text: string; fill: string; border: string }> = {
  orange: { bg: 'from-orange-500/20 to-amber-500/10', text: 'text-orange-400', fill: 'bg-gradient-to-r from-orange-500 to-amber-400', border: 'border-orange-500/20' },
  cyan: { bg: 'from-cyan-500/20 to-blue-500/10', text: 'text-cyan-400', fill: 'bg-gradient-to-r from-cyan-500 to-blue-400', border: 'border-cyan-500/20' },
  emerald: { bg: 'from-emerald-500/20 to-teal-500/10', text: 'text-emerald-400', fill: 'bg-gradient-to-r from-emerald-500 to-teal-400', border: 'border-emerald-500/20' },
  pink: { bg: 'from-pink-500/20 to-rose-500/10', text: 'text-pink-400', fill: 'bg-gradient-to-r from-pink-500 to-rose-400', border: 'border-pink-500/20' },
};

export const ChallengesPage = () => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="pb-8"
    >
      <header className="mb-8">
        <h1 className="text-3xl font-display font-semibold mb-2">Daily Challenges</h1>
        <p className="text-white/50 text-[15px]">Complete challenges to earn bonus XP</p>
      </header>

      <div className="space-y-4">
        {challenges.map((c, i) => {
          const style = colorMap[c.color] || colorMap.pink;
          const pct = Math.min(100, (c.progress / c.target) * 100);
          const completed = c.completed || pct >= 100;

          return (
            <motion.div
              key={c.id}
              initial={{ opacity: 0, x: -16 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08, duration: 0.35 }}
              className={`group bg-[#121216]/80 backdrop-blur-md rounded-2xl p-6 border transition-all shadow-lg ${completed ? 'border-emerald-500/20 bg-emerald-500/[0.02]' : 'border-white/[0.08] hover:border-pink-500/20'}`}
            >
              <div className="flex items-start gap-4">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${style.bg} flex items-center justify-center border ${style.border} shrink-0 transition-transform duration-300 group-hover:scale-105`}>
                  <c.icon className={`w-6 h-6 ${style.text}`} />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="font-semibold text-white text-lg flex items-center gap-2">
                      {c.title}
                      {completed && (
                        <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full border border-emerald-500/30 font-bold">DONE</span>
                      )}
                    </h3>
                    <span className="text-sm font-bold text-pink-400">+{c.xp} XP</span>
                  </div>
                  <p className="text-white/50 text-sm mb-3">{c.description}</p>

                  <div className="flex items-center gap-3">
                    <div className="flex-1 h-2.5 bg-white/5 rounded-full overflow-hidden border border-white/5">
                      <motion.div
                        className={`h-full rounded-full ${completed ? 'bg-gradient-to-r from-emerald-500 to-teal-400' : style.fill}`}
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ delay: i * 0.08 + 0.2, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
                      />
                    </div>
                    <span className="text-xs font-bold text-white/60 shrink-0 tabular-nums">
                      {c.progress} / {c.target}
                    </span>
                  </div>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
};
