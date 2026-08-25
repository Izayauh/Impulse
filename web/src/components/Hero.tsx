import { motion } from 'motion/react';
import { Play } from 'lucide-react';
import { useRef, useState } from 'react';
import { PRICE } from '@/src/lib/site';

export function Hero() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);

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
              className="bg-white text-black px-8 py-4 rounded-2xl font-bold text-lg hover:bg-white/90 transition-all active:scale-95 shadow-[0_0_40px_rgba(255,255,255,0.15)] w-full sm:w-auto text-center"
            >
              Get Impulse for {PRICE}
            </a>
            <a
              href="#demo"
              className="glass px-8 py-4 rounded-2xl font-bold text-lg hover:bg-white/10 transition-all active:scale-95 w-full sm:w-auto text-center"
            >
              Watch the demo
            </a>
          </div>

          <p className="text-sm text-white/40 mb-20">
            Windows 10/11 &middot; works fully offline &middot; or{' '}
            <a href="#beta" className="underline underline-offset-4 hover:text-white/70 transition-colors">
              try the beta free
            </a>
          </p>
        </motion.div>

        {/* Real product footage, not a mockup */}
        <motion.div
          id="demo"
          initial={{ opacity: 0, scale: 0.95, y: 40 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.8 }}
          className="relative w-full max-w-5xl mx-auto scroll-mt-32"
        >
          <div className="relative rounded-3xl overflow-hidden border border-white/10 shadow-2xl shadow-brand/10 bg-black">
            <video
              ref={videoRef}
              src="/demo.mp4"
              poster="/demo-poster.jpg"
              controls={playing}
              preload="metadata"
              playsInline
              className="w-full h-auto block"
              onPlay={() => setPlaying(true)}
            />
            {!playing && (
              <button
                aria-label="Play the demo video"
                onClick={() => videoRef.current?.play()}
                className="absolute inset-0 flex items-center justify-center group cursor-pointer"
              >
                <span className="w-20 h-20 rounded-full bg-brand flex items-center justify-center shadow-2xl shadow-brand/40 group-hover:scale-110 transition-transform">
                  <Play className="w-8 h-8 text-white translate-x-0.5" fill="currentColor" />
                </span>
              </button>
            )}
          </div>
          <p className="text-sm text-white/40 mt-4">
            Unedited screen capture. The airplane-mode part is the point: it keeps working with the network off.
          </p>

          <div className="absolute -top-10 -right-10 w-40 h-40 bg-brand/20 blur-3xl rounded-full -z-10" />
          <div className="absolute -bottom-10 -left-10 w-60 h-60 bg-blue-500/20 blur-3xl rounded-full -z-10" />
        </motion.div>
      </div>
    </section>
  );
}
