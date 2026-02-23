import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { Features } from './components/Features';
import { Gamification } from './components/Gamification';
import { Footer } from './components/Footer';
import { motion } from 'motion/react';

export default function App() {
  return (
    <div className="min-h-screen selection:bg-brand selection:text-white">
      <Navbar />

      <main>
        <Hero />

        {/* Social Proof / Logo Cloud */}
        <section className="py-20 border-y border-white/5 bg-white/[0.02]">
          <div className="max-w-7xl mx-auto px-6 text-center">
            <p className="text-white/20 text-xs font-bold uppercase tracking-[0.3em] mb-12">
              Trusted by creators at
            </p>
            <div className="flex flex-wrap justify-center items-center gap-12 md:gap-24 opacity-30 grayscale contrast-125">
              <div className="flex items-center gap-2"><svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" /></svg><span className="font-display font-bold text-2xl tracking-tighter">Linear</span></div>
              <div className="flex items-center gap-2"><svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L2 22h20L12 2z" /></svg><span className="font-display font-bold text-2xl tracking-tighter">Vercel</span></div>
              <div className="flex items-center gap-2"><svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor"><rect width="10" height="20" rx="5" x="7" y="2" /></svg><span className="font-display font-bold text-2xl tracking-tighter">Stripe</span></div>
              <div className="flex items-center gap-2"><svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="8" /></svg><span className="font-display font-bold text-2xl tracking-tighter">Figma</span></div>
              <div className="flex items-center gap-2"><svg className="w-6 h-6" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2c5.523 0 10 4.477 10 10s-4.477 10-10 10S2 17.523 2 12 6.477 2 12 2zm0 4a6 6 0 100 12 6 6 0 000-12z" /></svg><span className="font-display font-bold text-2xl tracking-tighter">Arc</span></div>
            </div>
          </div>
        </section>

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

        {/* Pricing Section */}
        <section id="pricing" className="py-40 px-6 bg-surface-muted/30 border-y border-white/5">
          <div className="max-w-7xl mx-auto text-center">
            <h2 className="font-display text-4xl md:text-6xl font-bold mb-6 tracking-tight">Simple, transparent pricing</h2>
            <p className="text-white/60 text-lg mb-20 max-w-2xl mx-auto">
              Start dictating in minutes. No credit card required for the free 14-day trial.
            </p>

            <div className="max-w-md mx-auto relative group">
              <div className="absolute inset-0 bg-brand/30 blur-[100px] rounded-full -z-10 group-hover:bg-brand/40 transition-all duration-700" />
              <div className="glass rounded-[32px] p-12 text-left border-brand/20 shadow-2xl relative">
                <div className="absolute top-0 right-0 px-4 py-1.5 bg-brand text-white text-xs font-bold rounded-bl-2xl rounded-tr-[32px] uppercase tracking-wider">
                  Most Popular
                </div>
                <h3 className="text-2xl font-bold mb-2">Pro Subscription</h3>
                <p className="text-white/60 mb-6">For power users and creators delivering at the speed of thought.</p>
                <div className="mb-8 flex items-baseline gap-2">
                  <span className="text-6xl font-display font-bold">$12</span>
                  <span className="text-white/40 font-medium">/month</span>
                </div>

                <ul className="space-y-4 mb-10 text-white/80">
                  <li className="flex items-center gap-3"><svg className="w-5 h-5 text-brand shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg> Unlimited local dictation</li>
                  <li className="flex items-center gap-3"><svg className="w-5 h-5 text-brand shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg> AI stylization models</li>
                  <li className="flex items-center gap-3"><svg className="w-5 h-5 text-brand shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg> Custom vocabulary & snippets</li>
                  <li className="flex items-center gap-3"><svg className="w-5 h-5 text-brand shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12" /></svg> Gamified streaks & stats</li>
                </ul>

                <button className="w-full bg-white hover:bg-white/90 text-black font-bold py-4 rounded-xl transition-all active:scale-95 shadow-[0_0_20px_rgba(255,255,255,0.1)]">
                  Start 14-Day Free Trial
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="py-40 px-6">
          <div className="max-w-5xl mx-auto glass rounded-[48px] p-12 md:p-24 text-center relative overflow-hidden border-brand/20">
            <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-brand/10 to-blue-500/10 -z-10" />
            <h2 className="font-display text-4xl md:text-7xl font-bold mb-8 leading-tight">
              Ready to level up <br />
              your workflow?
            </h2>
            <p className="text-white/60 text-xl mb-12 max-w-xl mx-auto">
              Join 50,000+ professionals who are dictating their way to a more productive life. No hidden fees, instant setup.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-6">
              <button className="bg-brand hover:bg-brand-dark text-white px-10 py-5 rounded-2xl font-bold text-xl transition-all shadow-2xl shadow-brand/40 active:scale-95 w-full sm:w-auto">
                Download for Windows
              </button>
              <button
                onClick={() => {
                  document.getElementById('pricing')?.scrollIntoView({ behavior: 'smooth' });
                }}
                className="glass px-10 py-5 rounded-2xl font-bold text-xl hover:bg-white/10 transition-all active:scale-95 w-full sm:w-auto text-white">
                Start 14-Day Free Trial
              </button>
            </div>
          </div>
        </section>
      </main>

      <Footer />

      {/* Sticky Mobile CTA */}
      <div className="fixed bottom-6 left-6 right-6 z-50 md:hidden animate-in slide-in-from-bottom-10 fade-in duration-500">
        <button
          onClick={() => {
            document.getElementById('pricing')?.scrollIntoView({ behavior: 'smooth' });
          }}
          className="w-full bg-brand/90 backdrop-blur-md text-white px-6 py-4 rounded-2xl font-bold shadow-[0_0_30px_rgba(233,30,99,0.3)] border border-white/10 flex items-center justify-center gap-2 active:scale-95 transition-transform"
        >
          Download for Windows
        </button>
      </div>
    </div>
  );
}
