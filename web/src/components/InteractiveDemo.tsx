import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Mic, Loader2, Play, CheckCircle2 } from 'lucide-react';
import { cn } from '@/src/lib/utils';
import { FloatingPill } from './FloatingPill';

export function InteractiveDemo() {
    const [state, setState] = useState<'idle' | 'listening' | 'processing' | 'done'>('idle');
    const [inputText, setInputText] = useState('');
    const [outputHtml, setOutputHtml] = useState('');

    // Auto-progress demo
    useEffect(() => {
        if (state === 'listening') {
            const typeText = "This is a quick demo of how I can speak to quickly generate code and styled text without tying my hands to the keyboard.";
            let i = 0;
            const interval = setInterval(() => {
                setInputText(typeText.slice(0, i));
                i++;
                if (i > typeText.length) {
                    clearInterval(interval);
                    setTimeout(() => setState('processing'), 500);
                }
            }, 30);
            return () => clearInterval(interval);
        }

        if (state === 'processing') {
            const timer = setTimeout(() => {
                setOutputHtml(`
<p><span class="text-brand">const</span> demo = <span class="text-blue-400">new</span> <span class="text-yellow-400">Demo</span>({
  <span class="text-emerald-400">speed</span>: <span class="text-orange-400">"blazing"</span>,
  <span class="text-emerald-400">friction</span>: <span class="text-orange-400">0</span>
});</p>
<p>&nbsp;</p>
<p class="text-white/80">// It instantly formats thoughts into perfect code structure.</p>
        `);
                setState('done');
            }, 1500);
            return () => clearTimeout(timer);
        }
    }, [state]);

    const reset = () => {
        setState('idle');
        setInputText('');
        setOutputHtml('');
    };

    return (
        <div className="glass rounded-3xl p-4 shadow-2xl relative overflow-hidden border border-white/10 w-full max-w-4xl mx-auto">
            {/* Fake Application Window */}
            <div className="bg-[#0a0a0d] rounded-2xl w-full min-h-[360px] p-8 text-left font-mono text-sm md:text-base border border-white/5 relative z-0 flex flex-col">
                {/* Window controls */}
                <div className="flex gap-2 mb-6">
                    <div className="w-3 h-3 rounded-full bg-red-500/30" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/30" />
                    <div className="w-3 h-3 rounded-full bg-green-500/30" />
                </div>

                {/* Content Area */}
                <div className="flex-1 relative">
                    <AnimatePresence mode="popLayout">
                        {state === 'idle' && (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                className="absolute inset-0 flex items-center justify-center"
                            >
                                <div className="text-center text-white/40 max-w-sm">
                                    <p className="mb-4">Click below to see Impulse in action.</p>
                                </div>
                            </motion.div>
                        )}

                        {(state === 'listening' || (state === 'processing' && inputText)) && (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                className="text-white/60 mb-8 max-w-2xl"
                            >
                                <span className="text-white/30 mr-4">Raw Input:</span>
                                {"\""}{inputText}{state === 'listening' && <span className="animate-pulse">|</span>}{"\""}
                            </motion.div>
                        )}

                        {state === 'processing' && (
                            <motion.div
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0 }}
                                className="flex items-center gap-3 text-brand font-sans"
                            >
                                <Loader2 className="w-5 h-5 animate-spin" />
                                <span className="font-semibold tracking-wide">Stylizing output...</span>
                            </motion.div>
                        )}

                        {state === 'done' && (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.98 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0 }}
                                className="space-y-2 mt-4"
                                dangerouslySetInnerHTML={{ __html: outputHtml }}
                            />
                        )}
                    </AnimatePresence>
                </div>
            </div>

            {/* Floating UI Overlays */}
            <AnimatePresence>
                {state === 'idle' && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 10, scale: 0.95 }}
                        className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20"
                    >
                        <button
                            onClick={() => setState('listening')}
                            className="bg-brand hover:bg-brand-dark text-white rounded-full pl-5 pr-6 py-3 flex items-center gap-3 font-semibold shadow-[0_0_30px_rgba(233,30,99,0.4)] transition-all active:scale-95"
                        >
                            <Mic className="w-5 h-5" />
                            Try Interactive Demo
                        </button>
                    </motion.div>
                )}

                {(state === 'listening' || state === 'processing') && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 10 }}
                        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20"
                    >
                        <FloatingPill
                            isProcessing={state === 'processing'}
                            className="shadow-[0_0_40px_rgba(233,30,99,0.3)]"
                        />
                    </motion.div>
                )}

                {state === 'done' && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20 flex gap-3"
                    >
                        <div className="glass bg-black/50 rounded-full pl-4 pr-6 py-2 flex items-center gap-2 text-sm text-white/80 border-green-500/20 shadow-[0_0_20px_rgba(34,197,94,0.1)]">
                            <CheckCircle2 className="w-4 h-4 text-green-400" />
                            <span>Transcribed in 1.2s</span>
                        </div>
                        <button
                            onClick={reset}
                            className="bg-white/10 hover:bg-white/20 Backdrop-blur-md border border-white/10 rounded-full px-5 py-2 text-sm font-semibold transition-all active:scale-95 flex items-center gap-2"
                        >
                            <Play className="w-4 h-4" />
                            Replay
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
