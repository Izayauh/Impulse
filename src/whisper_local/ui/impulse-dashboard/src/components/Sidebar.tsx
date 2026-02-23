import { Home, Code, Book, Trophy, Zap, Settings, LogOut, Brain } from 'lucide-react';
import { cn } from '../lib/utils';

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
      <div className="flex items-center gap-3 mb-12 px-2">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-pink-500 to-rose-600 flex items-center justify-center shadow-lg shadow-pink-500/20">
          <Brain className="w-6 h-6 text-white" />
        </div>
        <span className="text-xl font-display font-bold tracking-tight">Impulse</span>
      </div>

      <nav className="flex-1 space-y-2">
        {navItems.map((item) => (
          <button
            key={item.label}
            className={cn(
              "w-full flex items-center gap-4 px-4 py-3 rounded-2xl transition-all duration-200 group",
              item.active 
                ? "bg-white/10 text-white shadow-inner" 
                : "text-white/50 hover:text-white hover:bg-white/5"
            )}
          >
            <item.icon className={cn(
              "w-5 h-5",
              item.active ? "text-pink-500" : "group-hover:text-pink-400"
            )} />
            <span className="font-medium">{item.label}</span>
            {item.active && (
              <div className="ml-auto w-1.5 h-1.5 rounded-full bg-pink-500 shadow-[0_0_8px_rgba(236,72,153,0.8)]" />
            )}
          </button>
        ))}
      </nav>

      <div className="mt-auto space-y-2">
        <button className="w-full flex items-center gap-4 px-4 py-3 rounded-2xl text-white/50 hover:text-white hover:bg-white/5 transition-all">
          <Settings className="w-5 h-5" />
          <span className="font-medium">Settings</span>
        </button>
        <button className="w-full flex items-center gap-4 px-4 py-3 rounded-2xl text-rose-400/70 hover:text-rose-400 hover:bg-rose-400/10 transition-all">
          <LogOut className="w-5 h-5" />
          <span className="font-medium">Logout</span>
        </button>
      </div>
    </aside>
  );
};
