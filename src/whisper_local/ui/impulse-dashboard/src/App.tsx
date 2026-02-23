import { useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { XPWidget } from './components/XPWidget';
import { StreakWidget } from './components/StreakWidget';
import { ProgressChart } from './components/ProgressChart';
import { AchievementWidget } from './components/AchievementWidget';
import { QuoteWidget } from './components/QuoteWidget';
import { RecentActivity } from './components/RecentActivity';
import { motion } from 'motion/react';
import { useAppStore } from './lib/store';

export default function App() {
  const initBridge = useAppStore(state => state.initBridge);
  const userName = useAppStore(state => state.stats?.userName || 'Writer');

  useEffect(() => {
    initBridge();
  }, [initBridge]);

  return (
    <div className="flex min-h-screen font-sans">
      <Sidebar />

      <main className="flex-1 ml-64 p-10 max-w-[1600px] mx-auto w-full">
        <header className="mb-10 flex justify-between items-end">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <h1 className="text-4xl font-display font-bold tracking-tight mb-2">
              Welcome back, <span className="text-gradient">{userName}</span>
            </h1>
            <p className="text-white/50 text-lg">You're on a roll! Keep up the momentum.</p>
          </motion.div>

          <div className="flex gap-4">
            <div className="px-5 py-2.5 rounded-full border border-emerald-500/20 bg-emerald-500/10 backdrop-blur-md flex items-center gap-3 shadow-[0_0_20px_rgba(16,185,129,0.15)] transition-all cursor-default">
              <div className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></span>
              </div>
              <span className="text-sm font-bold text-emerald-400 tracking-wide uppercase">System Online</span>
            </div>
          </div>
        </header>

        <div className="space-y-6">
          {/* Top Row: XP and Streaks */}
          <motion.div
            className="flex gap-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <XPWidget />
            <StreakWidget />
          </motion.div>

          {/* Middle Row: Progress, Quote, Recent Activity */}
          <motion.div
            className="flex gap-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <div className="w-64 flex-shrink-0 flex flex-col gap-6">
              <QuoteWidget />
            </div>
            <ProgressChart />
            <div className="w-80 flex-shrink-0">
              <RecentActivity />
            </div>
          </motion.div>

          {/* Bottom Row: Achievements and more */}
          <motion.div
            className="grid grid-cols-3 gap-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <div className="col-span-1">
              <h2 className="text-sm font-bold text-white/40 uppercase tracking-widest mb-4 px-2">Recent Achievements</h2>
              <AchievementWidget />
            </div>

            <div className="col-span-2">
              <h2 className="text-sm font-bold text-white/40 uppercase tracking-widest mb-4 px-2">Active Challenges</h2>
              <div className="grid grid-cols-2 gap-4">
                {[
                  { title: 'Code Master', desc: 'Solve 10 snippets today', progress: 60, icon: '🔥' },
                  { title: 'Word Smith', desc: 'Learn 5 new terms', progress: 20, icon: '📚' },
                ].map((challenge) => (
                  <div key={challenge.title} className="glass-card rounded-3xl p-6 transition-all duration-300 cursor-pointer group hover:-translate-y-2 relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-br from-pink-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="flex justify-between items-start mb-2 relative z-10">
                      <h4 className="font-bold text-white group-hover:text-pink-300 transition-colors drop-shadow-sm">{challenge.title}</h4>
                      <span className="text-xl group-hover:scale-125 transition-transform duration-300 drop-shadow-md">{challenge.icon}</span>
                    </div>
                    <p className="text-xs text-white/50 mb-4 relative z-10">{challenge.desc}</p>
                    <div className="h-2 w-full bg-black/40 rounded-full overflow-hidden shadow-inner border border-white/5 relative z-10">
                      <div
                        className="h-full bg-gradient-to-r from-pink-500 to-rose-400 rounded-full shadow-[0_0_10px_rgba(236,72,153,0.5)] transition-all duration-1000 relative overflow-hidden"
                        style={{ width: `${challenge.progress}%` }}
                      >
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent -translate-x-[100%] animate-[shimmer_2s_infinite]" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </main>
    </div>
  );
}
