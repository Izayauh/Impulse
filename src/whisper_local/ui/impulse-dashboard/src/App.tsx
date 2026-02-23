import { Sidebar } from './components/Sidebar';
import { XPWidget } from './components/XPWidget';
import { StreakWidget } from './components/StreakWidget';
import { ProgressChart } from './components/ProgressChart';
import { AchievementWidget } from './components/AchievementWidget';
import { QuoteWidget } from './components/QuoteWidget';
import { motion } from 'motion/react';

export default function App() {
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
              Welcome back, <span className="text-gradient">Horne</span>
            </h1>
            <p className="text-white/50 text-lg">You're on a roll! Keep up the momentum.</p>
          </motion.div>
          
          <div className="flex gap-4">
            <div className="px-4 py-2 rounded-2xl glass-card flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-sm font-medium text-white/70">System Online</span>
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

          {/* Middle Row: Progress and Quote */}
          <motion.div 
            className="flex gap-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <QuoteWidget />
            <ProgressChart />
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
                  { title: 'Code Master', desc: 'Solve 10 snippets today', progress: 60 },
                  { title: 'Word Smith', desc: 'Learn 5 new terms', progress: 20 },
                ].map((challenge) => (
                  <div key={challenge.title} className="glass-card rounded-3xl p-6 hover:border-pink-500/30 transition-all cursor-pointer group">
                    <h4 className="font-bold mb-1 group-hover:text-pink-400 transition-colors">{challenge.title}</h4>
                    <p className="text-xs text-white/50 mb-4">{challenge.desc}</p>
                    <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-pink-500 rounded-full" 
                        style={{ width: `${challenge.progress}%` }} 
                      />
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
