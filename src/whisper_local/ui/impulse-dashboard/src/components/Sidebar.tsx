import { Home, Code, Book, Trophy, Zap, Settings, LogOut, Brain } from 'lucide-react';
import { cn } from '../lib/utils';
import { motion } from 'motion/react';

const navItems = [
  { icon: Home, label: 'Home', active: true },
  { icon: Code, label: 'Snippets', active: false },
  { icon: Book, label: 'Dictionary', active: false },
  { icon: Trophy, label: 'Achievements', active: false },
  { icon: Zap, label: 'Challenges', active: false },
];

export const Sidebar = () => {
  return (
    <aside className="w-64 h-screen glass-panel fixed left-0 top-0 flex flex-col p-6 z-50">
      <div className="flex items-center gap-3 mb-12 px-2 animate-float">
        <div className="relative group">
          <div className="absolute inset-0 bg-pink-500/40 blur-xl rounded-xl group-hover:bg-pink-500/60 transition-all duration-300 animate-pulse-glow" />
          <div className="relative w-10 h-10 rounded-xl bg-gradient-to-br from-pink-500 via-rose-500 to-orange-500 flex items-center justify-center shadow-lg transform group-hover:scale-110 transition-transform">
            <Brain className="w-6 h-6 text-white" />
          </div>
        </div>
        <span className="text-xl font-display font-bold tracking-tight text-white group-hover:text-pink-400 transition-colors">Impulse</span>
      </div>

      <nav className="flex-1 space-y-2">
        {navItems.map((item, i) => (
          <motion.button
            key={item.label}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
            className={cn(
              "w-full flex items-center gap-4 px-4 py-3 rounded-2xl transition-all duration-300 group relative overflow-hidden",
              item.active
                ? "text-white"
                : "text-white/50 hover:text-white"
            )}
          >
            {item.active && (
              <div className="absolute inset-0 bg-gradient-to-r from-pink-500/20 to-transparent border border-pink-500/30 rounded-2xl" />
            )}
            {!item.active && (
              <div className="absolute inset-0 bg-white/5 opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl" />
            )}
            <item.icon className={cn(
              "w-5 h-5 relative z-10 transition-transform group-hover:scale-110",
              item.active ? "text-pink-500 drop-shadow-[0_0_8px_rgba(236,72,153,0.8)]" : "group-hover:text-pink-400"
            )} />
            <span className="font-medium relative z-10">{item.label}</span>
            {item.active && (
              <div className="ml-auto w-1.5 h-1.5 rounded-full bg-pink-500 shadow-[0_0_8px_rgba(236,72,153,1)] relative z-10" />
            )}
          </motion.button>
        ))}
      </nav>

      <div className="mt-auto space-y-2">
        <button className="w-full flex items-center gap-4 px-4 py-3 rounded-2xl text-white/50 hover:text-white hover:bg-white/5 transition-all group overflow-hidden relative">
          <Settings className="w-5 h-5 group-hover:rotate-90 transition-transform duration-500" />
          <span className="font-medium">Settings</span>
        </button>
        <button className="w-full flex items-center gap-4 px-4 py-3 rounded-2xl text-rose-400/70 hover:text-rose-400 hover:bg-rose-400/10 transition-all group">
          <LogOut className="w-5 h-5 group-hover:-translate-x-1 transition-transform" />
          <span className="font-medium">Logout</span>
        </button>
      </div>
    </aside>
  );
};
