import { AnimatePresence, motion } from 'motion/react';
import { useAppStore } from '../lib/store';
import { Check } from 'lucide-react';

export const Toast = () => {
  const toast = useAppStore(state => state.toast);

  return (
    <AnimatePresence>
      {toast.visible && (
        <motion.div
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 10, scale: 0.95 }}
          transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="fixed bottom-8 left-1/2 -translate-x-1/2 z-[200] flex items-center gap-2.5 px-5 py-3 rounded-xl bg-[#1a1a22] border border-pink-500/30 shadow-[0_8px_32px_rgba(0,0,0,0.5),0_0_20px_rgba(236,72,153,0.15)] backdrop-blur-xl"
        >
          <div className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center">
            <Check className="w-3 h-3 text-emerald-400" />
          </div>
          <span className="text-sm font-medium text-white/90">{toast.message}</span>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
