import { GlassCard } from './GlassCard';
import { useAppStore } from '../lib/store';
import { Clock } from 'lucide-react';
import { motion } from 'motion/react';

export const RecentActivity = () => {
    const transcripts = useAppStore(state => state.stats?.recentTranscripts || []);

    return (
        <GlassCard className="flex flex-col h-[350px] relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-32 h-32 bg-pink-500/10 blur-3xl rounded-full group-hover:bg-rose-500/20 transition-all duration-700" />
            <div className="flex justify-between items-center mb-6 relative z-10">
                <div>
                    <h3 className="text-lg font-display font-bold text-white group-hover:text-pink-100 transition-colors">Live Feed</h3>
                    <p className="text-sm text-white/50">Recent Dictations</p>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-pink-500 shadow-[0_0_8px_rgba(236,72,153,0.8)] animate-pulse" />
                    <span className="text-xs font-bold text-pink-400">LIVE</span>
                </div>
            </div>

            <div className="flex-1 w-full overflow-y-auto pr-2 space-y-3 scrollbar-thin scrollbar-thumb-pink-500/20 scrollbar-track-transparent relative z-10">
                {transcripts.map((t, idx) => (
                    <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.1 }}
                        key={idx}
                        className="flex gap-4 items-center p-4 rounded-2xl bg-white/5 border border-white/5 hover:bg-white/10 hover:border-pink-500/30 transition-all duration-300 group/item cursor-pointer"
                    >
                        <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gradient-to-br from-zinc-800 to-zinc-900 flex items-center justify-center border border-white/10 group-hover/item:border-pink-500/50 shadow-inner transition-colors">
                            <Clock className="w-4 h-4 text-white/50 group-hover/item:text-pink-400 transition-colors" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-white/90 truncate group-hover/item:text-white transition-colors">{t.text}</p>
                            <div className="flex justify-between items-center mt-1">
                                <span className="text-xs text-white/40">{t.time}</span>
                                <span className="text-xs font-bold text-transparent bg-clip-text bg-gradient-to-r from-pink-400 to-rose-400 group-hover/item:drop-shadow-[0_0_8px_rgba(236,72,153,0.6)] transition-all">+{t.words} words</span>
                            </div>
                        </div>
                    </motion.div>
                ))}
                {transcripts.length === 0 && (
                    <div className="text-sm text-white/50 text-center py-8">
                        No recent activity yet. Start speaking!
                    </div>
                )}
            </div>
        </GlassCard>
    );
};
