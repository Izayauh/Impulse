import { motion } from 'motion/react';
import { PRICE } from '@/src/lib/site';
import { HeroDemo } from './HeroDemo';

export function Hero() {
  return (
    <section className="relative pt-36 pb-24 overflow-hidden flex flex-col items-center">
      {/* Background glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full -z-10 overflow-hidden">
        <div className="absolute top-[-10%] left-[10%] w-[40%] h-[40%] bg-brand/10 blur-[120px] rounded-full" />
        <div className="absolute bottom-[10%] right-[10%] w-[30%] h-[30%] bg-blue-500/10 blur-[100px] rounded-full" />
      </div>

      <div className="max-w-7xl mx-auto px-6 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <span className="inline-block px-4 py-1.5 rounded-full glass text-xs font-bold tracking-widest uppercase text-brand mb-6">
            Runs 100% on your PC &middot; Pay once
          </span>

          <h1 className="font-display text-5xl sm:text-6xl md:text-8xl font-bold tracking-tighter mb-8 leading-[1.02] max-w-5xl mx-auto">
            Talk. It types. <br />
            <span className="text-gradient">Nothing leaves your PC.</span>
          </h1>

          <p className="text-lg md:text-xl text-white/60 max-w-2xl mx-auto mb-10 leading-relaxed font-medium">
            Impulse is Windows dictation that runs Whisper on your own machine.
            Hold a key, speak, and the words land in whatever app you're in.
            No cloud, no account, no subscription. {PRICE}, once.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-4">
            <a
              href="#pricing"
              className="bg-brand hover:bg-brand-dark text-white px-8 py-4 rounded-2xl font-bold text-lg transition-all active:scale-95 shadow-[0_0_40px_rgba(246,51,154,0.35)] w-full sm:w-auto text-center"
            >
              Get Impulse for {PRICE}
            </a>
            <a
              href="#beta"
              className="glass px-8 py-4 rounded-2xl font-bold text-lg hover:bg-white/10 transition-all active:scale-95 w-full sm:w-auto text-center"
            >
              Try the beta free
            </a>
          </div>

          <p className="text-sm text-white/40 mb-20">
            Windows 10/11 &middot; works fully offline &middot; licence key by email in seconds
          </p>
        </motion.div>

        {/* The whole product, drawn instead of filmed, so it stays sharp at any size */}
        <motion.div
          id="demo"
          initial={{ opacity: 0, scale: 0.97, y: 30 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ delay: 0.25, duration: 0.7, ease: 'easeOut' }}
          className="relative w-full max-w-5xl mx-auto scroll-mt-32"
        >
          <HeroDemo />
          <p className="text-sm text-white/40 mt-5 max-w-2xl mx-auto">
            The whole product in one loop: hold <span className="text-white/70 font-semibold">Ctrl+Win</span>, talk, let go.
            Filler words come out, punctuation goes in, and the text lands where your cursor is.
            Airplane mode stays on the entire time.
          </p>

          <div className="absolute -top-10 -right-10 w-40 h-40 bg-brand/20 blur-3xl rounded-full -z-10" />
          <div className="absolute -bottom-10 -left-10 w-60 h-60 bg-blue-500/20 blur-3xl rounded-full -z-10" />
        </motion.div>
      </div>
    </section>
  );
}
