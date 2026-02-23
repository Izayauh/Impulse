import { GlassCard } from './GlassCard';

export const QuoteWidget = () => {
  return (
    <GlassCard className="flex-1 flex flex-col justify-center relative overflow-hidden group">
      <div className="absolute -right-10 -bottom-10 w-40 h-40 bg-pink-500/10 blur-3xl rounded-full group-hover:bg-pink-500/20 transition-all" />
      <p className="text-2xl font-display font-light leading-tight text-white/90 italic mb-4">
        "Your velocity determines your destiny."
      </p>
      <div className="flex items-center gap-2">
        <div className="w-8 h-0.5 bg-pink-500/50" />
        <span className="text-xs font-medium text-white/40 uppercase tracking-widest">Impulse Core</span>
      </div>
    </GlassCard>
  );
};
