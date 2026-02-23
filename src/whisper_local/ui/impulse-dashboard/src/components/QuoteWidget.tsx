import { GlassCard } from './GlassCard';

export const QuoteWidget = () => {
  return (
    <GlassCard className="flex-1 flex flex-col justify-center relative overflow-hidden group p-8 cursor-default">
      <div className="absolute -right-10 -bottom-10 w-40 h-40 bg-pink-500/10 blur-3xl rounded-full group-hover:bg-gradient-to-tl from-rose-500/30 to-orange-500/20 transition-all duration-700 animate-pulse-glow" />
      <div className="absolute top-0 left-0 w-2 h-full bg-gradient-to-b from-pink-500 via-rose-500 to-orange-500 opacity-50 group-hover:opacity-100 transition-opacity" />

      <p className="text-3xl font-display font-light leading-tight text-transparent bg-clip-text bg-gradient-to-br from-white to-white/60 group-hover:from-white group-hover:to-pink-100 italic relative z-10 drop-shadow-md">
        "Your velocity determines your destiny."
      </p>

      <div className="flex items-center gap-3 mt-6 relative z-10">
        <div className="w-10 h-[2px] bg-gradient-to-r from-pink-500 to-transparent" />
        <span className="text-xs font-bold text-pink-500/70 uppercase tracking-[0.2em] group-hover:text-pink-400 transition-colors">Impulse Core</span>
      </div>
    </GlassCard>
  );
};
