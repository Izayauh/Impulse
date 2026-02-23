import { GlassCard } from './GlassCard';

export const XPWidget = () => {
  return (
    <GlassCard className="flex-1 flex items-center gap-6">
      <div className="relative">
        <div className="w-16 h-16 rounded-2xl overflow-hidden border-2 border-pink-500/30">
          <img 
            src="https://picsum.photos/seed/user42/200/200" 
            alt="Profile" 
            className="w-full h-full object-cover"
            referrerPolicy="no-referrer"
          />
        </div>
        <div className="absolute -bottom-2 -right-2 bg-pink-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-lg">
          PRO
        </div>
      </div>
      
      <div className="flex-1">
        <div className="flex justify-between items-end mb-2">
          <div>
            <h3 className="text-sm font-medium text-white/60 uppercase tracking-wider">Current Level</h3>
            <p className="text-2xl font-display font-bold">Level 42</p>
          </div>
          <span className="text-sm font-medium text-pink-400">75%</span>
        </div>
        
        <div className="h-3 w-full bg-white/5 rounded-full overflow-hidden border border-white/5">
          <div 
            className="h-full bg-gradient-to-r from-pink-500 to-rose-400 rounded-full shadow-[0_0_15px_rgba(236,72,153,0.4)] transition-all duration-1000 ease-out"
            style={{ width: '75%' }}
          />
        </div>
      </div>
    </GlassCard>
  );
};
