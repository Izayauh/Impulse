import { motion } from 'motion/react';
import { InteractiveDemo } from './InteractiveDemo';

export function Hero() {
  return (
    <section className="relative pt-32 pb-20 overflow-hidden min-h-screen flex flex-col items-center">
      {/* Background Glows */}
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
            Voice Dictation Reimagined
          </span>
          <h1 className="font-display text-5xl md:text-7xl lg:text-8xl font-bold tracking-tighter mb-8 leading-[1.1] md:leading-[0.9]">
            Speak your ideas <br />
            <span className="text-gradient">into reality.</span>
          </h1>
          <p className="text-lg md:text-xl text-white/60 max-w-2xl mx-auto mb-10 leading-relaxed font-medium">
            Impulse is the AI-powered dictation layer that lives on top of every application. <span className="hidden md:inline">Perfect formatting, gamified focus, and zero friction.</span>
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-24">
            <button
              onClick={() => {
                document.getElementById('beta')?.scrollIntoView({ behavior: 'smooth' });
              }}
              className="bg-white text-black px-8 py-4 rounded-2xl font-bold text-lg hover:bg-white/90 transition-all active:scale-95 shadow-[0_0_40px_rgba(255,255,255,0.15)] w-full sm:w-auto"
            >
              Join the Beta
            </button>
            <button
              onClick={() => {
                document.getElementById('demo-section')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
              }}
              className="glass px-8 py-4 rounded-2xl font-bold text-lg hover:bg-white/10 transition-all active:scale-95 w-full sm:w-auto"
            >
              Try the Demo Below
            </button>
          </div>
        </motion.div>

        {/* Interactive Demo Container */}
        <motion.div
          id="demo-section"
          initial={{ opacity: 0, scale: 0.95, y: 40 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.8 }}
          className="relative w-full max-w-5xl mx-auto scroll-mt-32"
        >
          <InteractiveDemo />

          {/* Decorative elements */}
          <div className="absolute -top-10 -right-10 w-40 h-40 bg-brand/20 blur-3xl rounded-full -z-10" pointer-events="none" />
          <div className="absolute -bottom-10 -left-10 w-60 h-60 bg-blue-500/20 blur-3xl rounded-full -z-10" pointer-events="none" />
        </motion.div>
      </div>
    </section>
  );
}
