import { motion } from 'motion/react';
import { Brain, Sparkles, Loader2 } from 'lucide-react';
import { cn } from '@/src/lib/utils';

interface FloatingPillProps {
  className?: string;
  isProcessing?: boolean;
}

export function FloatingPill({ className, isProcessing = false }: FloatingPillProps) {
  return (
    <motion.div
      initial={{ y: 20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ delay: 0.1, duration: 0.4, ease: "easeOut" }}
      className={cn(
        "glass-dark rounded-full px-6 py-3 flex items-center gap-4 shadow-2xl relative overflow-hidden",
        "border transition-all duration-500",
        isProcessing ? "border-brand/40 shadow-[0_0_15px_rgba(233,30,99,0.2)]" : "border-white/10 glow-pink",
        className
      )}
    >
      <div className="relative flex items-center justify-center w-5 h-5">
        {!isProcessing && <div className="absolute inset-0 bg-brand blur-md opacity-20 animate-pulse" />}
        {isProcessing ? (
          <Loader2 className="w-5 h-5 text-brand animate-spin relative z-10" />
        ) : (
          <Brain className="w-5 h-5 text-brand relative z-10" />
        )}
      </div>

      <div className="flex gap-1 items-center h-4 min-w-[50px] justify-center">
        {isProcessing ? (
          <span className="text-white/60 text-sm animate-pulse tracking-wide font-medium">Stylizing...</span>
        ) : (
          [...Array(12)].map((_, i) => (
            <motion.div
              key={i}
              animate={{
                height: [4, Math.random() * 16 + 4, 4],
              }}
              transition={{
                duration: 0.8,
                repeat: Infinity,
                delay: i * 0.05,
              }}
              className="w-1 bg-brand/60 rounded-full"
            />
          ))
        )}
      </div>

      <div className="h-4 w-px bg-white/10 mx-2" />

      <div className="flex items-center gap-2 text-sm font-medium text-white/90">
        <Sparkles className="w-4 h-4 text-brand" />
        <span>Professional Stylization</span>
      </div>
    </motion.div>
  );
}
