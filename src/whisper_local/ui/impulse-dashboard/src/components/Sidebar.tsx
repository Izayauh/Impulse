import { Brain, Settings } from 'lucide-react';
import { cn } from '../lib/utils';
import { useAppStore, type PageId } from '../lib/store';

const navItems: { label: string; rightText: string; id: PageId }[] = [
  { label: 'Home', rightText: 'Feed', id: 'home' },
  { label: 'Snippets', rightText: '3', id: 'snippets' },
  { label: 'Dictionary', rightText: '12', id: 'dictionary' },
  { label: 'Achievements', rightText: '9/14', id: 'achievements' },
  { label: 'Challenges', rightText: 'Daily', id: 'challenges' },
];

interface SidebarProps {
  onOpenSettings?: () => void;
}

export const Sidebar = ({ onOpenSettings }: SidebarProps) => {
  const stats = useAppStore(state => state.stats);
  const activePage = useAppStore(state => state.activePage);
  const setActivePage = useAppStore(state => state.setActivePage);
  const xp = stats?.xp || 97046;
  const rank = stats?.rank || 'Voice Virtuoso';

  return (
    <aside className="w-[280px] h-screen bg-[#0E0E12] border-r border-white/[0.08] fixed left-0 top-0 flex flex-col pt-8 pb-6 px-6 z-50">
      {/* Logo */}
      <div className="flex items-center gap-3 mb-10 px-2 cursor-pointer">
        <div className="w-8 h-8 rounded-lg bg-pink-500/10 flex items-center justify-center border border-pink-500/20">
          <Brain className="w-5 h-5 text-pink-500" />
        </div>
        <span className="text-xl font-display font-semibold text-white tracking-wide">Impulse</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1.5">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setActivePage(item.id)}
            className={cn(
              "w-full flex items-center justify-between px-4 py-2.5 rounded-xl transition-all duration-200 text-sm focus-visible:ring-2 focus-visible:ring-pink-500/50 focus-visible:outline-none",
              activePage === item.id
                ? "bg-pink-500/10 text-pink-100 border border-pink-500/20 shadow-inner"
                : "text-white/50 hover:text-white hover:bg-white/5 border border-transparent"
            )}
            aria-current={activePage === item.id ? 'page' : undefined}
          >
            <span className={cn("font-medium", activePage === item.id ? "text-white" : "")}>{item.label}</span>
            <span className={cn("text-xs font-semibold", activePage === item.id ? "text-pink-300" : "text-white/30")}>
              {item.rightText}
            </span>
          </button>
        ))}
      </nav>

      {/* Profile / Rank */}
      <div className="mt-auto">
        <div className="flex items-center gap-3 p-3 bg-white/[0.02] border border-white/[0.08] rounded-2xl">
          <div className="w-10 h-10 rounded-full bg-pink-500 flex items-center justify-center text-white font-bold tracking-tighter shadow-[0_0_15px_rgba(236,72,153,0.4)]">
            WL
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-[11px] text-white/60 uppercase tracking-widest font-semibold font-display leading-tight">
              Rank: <span className="text-pink-400" title={rank}>{rank}</span>
            </h4>
            <p className="text-sm font-semibold text-emerald-400 truncate mt-0.5">
              {xp.toLocaleString()} <span className="text-white/50 text-xs">XP</span>
            </p>
          </div>
          <button 
            onClick={onOpenSettings}
            className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center text-white/50 hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-pink-500/50 focus-visible:outline-none"
            aria-label="Open settings"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};
