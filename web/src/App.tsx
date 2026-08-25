import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { Privacy } from './components/Privacy';
import { Features } from './components/Features';
import { Pricing } from './components/Pricing';
import { Gamification } from './components/Gamification';
import { BetaSignup } from './components/BetaSignup';
import { Faq } from './components/Faq';
import { Footer } from './components/Footer';
import { PRICE } from './lib/site';

export default function App() {
  return (
    <div className="min-h-screen selection:bg-brand selection:text-white">
      <Navbar />

      <main>
        {/* Order is the argument: proof, the moat, what it does, the offer. */}
        <Hero />
        <Privacy />
        <Features />
        <Pricing />
        <Gamification />
        <BetaSignup />
        <Faq />

        {/* Final CTA */}
        <section className="py-40 px-6">
          <div className="max-w-5xl mx-auto glass rounded-[48px] p-12 md:p-24 text-center relative overflow-hidden border-brand/20">
            <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-brand/10 to-blue-500/10 -z-10" />
            <h2 className="font-display text-4xl md:text-7xl font-bold mb-8 leading-tight">
              Own your dictation.
            </h2>
            <p className="text-white/60 text-xl mb-12 max-w-xl mx-auto">
              One payment. Yours forever. And your voice stays where it was spoken.
            </p>
            <a
              href="#pricing"
              className="inline-block bg-brand hover:bg-brand-dark text-white px-10 py-5 rounded-2xl font-bold text-xl transition-all shadow-2xl shadow-brand/40 active:scale-95 w-full sm:w-auto"
            >
              Get Impulse for {PRICE}
            </a>
          </div>
        </section>
      </main>

      <Footer />

      {/* Sticky Mobile CTA */}
      <div className="fixed bottom-6 left-6 right-6 z-50 md:hidden animate-in slide-in-from-bottom-10 fade-in duration-500">
        <a
          href="#pricing"
          className="w-full bg-brand/90 backdrop-blur-md text-white px-6 py-4 rounded-2xl font-bold shadow-[0_0_30px_rgba(233,30,99,0.3)] border border-white/10 flex items-center justify-center gap-2 active:scale-95 transition-transform"
        >
          Get Impulse &middot; {PRICE}
        </a>
      </div>
    </div>
  );
}
