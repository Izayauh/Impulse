import { motion } from 'motion/react';
import { Brain } from 'lucide-react';

export function Navbar() {
  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="fixed top-0 left-0 right-0 z-50 flex justify-center p-6"
    >
      <div className="glass rounded-2xl px-6 py-3 flex items-center justify-between w-full max-w-7xl">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-brand rounded-lg flex items-center justify-center shadow-lg shadow-brand/20">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <span className="font-display font-bold text-xl tracking-tight">Impulse</span>
        </div>
        
        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-white/70">
          <a href="#features" className="hover:text-white transition-colors">Features</a>
          <a href="#gamification" className="hover:text-white transition-colors">Productivity</a>
          <a href="#beta" className="hover:text-white transition-colors">Beta</a>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-brand/10 border border-brand/20 text-[10px] font-bold uppercase tracking-wider text-brand">
            <span className="w-1.5 h-1.5 rounded-full bg-brand animate-pulse" />
            Beta
          </div>
          <button
            onClick={() => {
              document.getElementById('beta')?.scrollIntoView({ behavior: 'smooth' });
            }}
            className="bg-brand hover:bg-brand-dark text-white px-5 py-2 rounded-xl text-sm font-semibold transition-all shadow-lg shadow-brand/20 active:scale-95"
          >
            Join Beta
          </button>
        </div>
      </div>
    </motion.nav>
  );
}
