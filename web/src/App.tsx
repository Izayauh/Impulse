import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { Features } from './components/Features';
import { Gamification } from './components/Gamification';
import { BetaSignup } from './components/BetaSignup';
import { Footer } from './components/Footer';
import { motion } from 'motion/react';

export default function App() {
  return (
    <div className="min-h-screen selection:bg-brand selection:text-white">
      <Navbar />

      <main>
        <Hero />

        <Features />

        {/* Immersive Visualizer Section */}
        <section className="py-40 relative overflow-hidden">
          <div className="absolute inset-0 bg-brand/5 -z-10" />
          <div className="max-w-4xl mx-auto px-6 text-center">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              className="mb-16"
            >
              <h2 className="font-display text-4xl md:text-7xl font-bold mb-8">
                The sound of <br />
                <span className="text-brand">pure focus.</span>
              </h2>
              <p className="text-white/60 text-xl leading-relaxed">
                Our dynamic audio engine visualizes your voice in real-time,
                providing subtle feedback that keeps you locked in the zone.
              </p>
            </motion.div>

            <div className="flex items-center justify-center gap-2 h-40">
              {[...Array(40)].map((_, i) => (
                <motion.div
                  key={i}
                  animate={{
                    height: [20, Math.random() * 120 + 20, 20],
                    opacity: [0.2, 0.8, 0.2]
                  }}
                  transition={{
                    duration: 1.2,
                    repeat: Infinity,
                    delay: i * 0.03,
                    ease: "easeInOut"
                  }}
                  className="w-1.5 bg-brand rounded-full glow-pink"
                />
              ))}
            </div>
          </div>
        </section>

        <Gamification />

        <BetaSignup />

        {/* Final CTA */}
        <section className="py-40 px-6">
          <div className="max-w-5xl mx-auto glass rounded-[48px] p-12 md:p-24 text-center relative overflow-hidden border-brand/20">
            <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-brand/10 to-blue-500/10 -z-10" />
            <h2 className="font-display text-4xl md:text-7xl font-bold mb-8 leading-tight">
              Ready to level up <br />
              your workflow?
            </h2>
            <p className="text-white/60 text-xl mb-12 max-w-xl mx-auto">
              Join early adopters who are dictating their way to a more productive life. Free during beta.
            </p>
            <button
              onClick={() => {
                document.getElementById('beta')?.scrollIntoView({ behavior: 'smooth' });
              }}
              className="bg-brand hover:bg-brand-dark text-white px-10 py-5 rounded-2xl font-bold text-xl transition-all shadow-2xl shadow-brand/40 active:scale-95 w-full sm:w-auto"
            >
              Join the Beta
            </button>
          </div>
        </section>
      </main>

      <Footer />

      {/* Sticky Mobile CTA */}
      <div className="fixed bottom-6 left-6 right-6 z-50 md:hidden animate-in slide-in-from-bottom-10 fade-in duration-500">
        <button
          onClick={() => {
            document.getElementById('beta')?.scrollIntoView({ behavior: 'smooth' });
          }}
          className="w-full bg-brand/90 backdrop-blur-md text-white px-6 py-4 rounded-2xl font-bold shadow-[0_0_30px_rgba(233,30,99,0.3)] border border-white/10 flex items-center justify-center gap-2 active:scale-95 transition-transform"
        >
          Join the Beta
        </button>
      </div>
    </div>
  );
}
