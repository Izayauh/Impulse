import React, { useState } from 'react';
import { motion } from 'motion/react';
import { Mail, ArrowRight, CheckCircle2, Loader2 } from 'lucide-react';
import { RELEASE_PAGE_URL } from '@/src/lib/site';

type FormState = 'idle' | 'submitting' | 'success' | 'error';

export function BetaSignup() {
  const [email, setEmail] = useState('');
  const [state, setState] = useState<FormState>('idle');
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    setState('submitting');
    setErrorMsg('');

    try {
      const res = await fetch('/api/beta-signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      });

      const data = await res.json();

      if (res.ok && data.success) {
        setState('success');
      } else {
        setErrorMsg(data.error || 'Something went wrong. Please try again.');
        setState('error');
      }
    } catch {
      setErrorMsg('Network error. Please check your connection and try again.');
      setState('error');
    }
  };

  return (
    <section id="beta" className="py-40 px-6 bg-surface-muted/30 border-y border-white/5">
      <div className="max-w-7xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <span className="inline-block px-4 py-1.5 rounded-full glass text-xs font-bold tracking-widest uppercase text-brand mb-6">
            Limited Beta
          </span>
          <h2 className="font-display text-4xl md:text-6xl font-bold mb-6 tracking-tight">
            Get early access
          </h2>
          <p className="text-white/60 text-lg mb-16 max-w-2xl mx-auto">
            Impulse is in private beta. Sign up with your email and we'll send you
            a license key to start dictating immediately.
          </p>
        </motion.div>

        <div className="max-w-md mx-auto relative group">
          <div className="absolute inset-0 bg-brand/30 blur-[100px] rounded-full -z-10 group-hover:bg-brand/40 transition-all duration-700" />
          <div className="glass rounded-[32px] p-10 text-left border-brand/20 shadow-2xl relative">
            {state === 'success' ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-center py-6"
              >
                <CheckCircle2 className="w-12 h-12 text-green-400 mx-auto mb-4" />
                <h3 className="text-2xl font-bold mb-2">You're in!</h3>
                <p className="text-white/60">
                  Check your email for your beta license key and download link.
                </p>
                <a
                  href={RELEASE_PAGE_URL}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex mt-6 items-center gap-2 rounded-xl bg-white/8 px-4 py-3 text-sm font-semibold text-white hover:bg-white/12 transition-colors"
                >
                  Download the Windows beta
                  <ArrowRight className="w-4 h-4" />
                </a>
              </motion.div>
            ) : (
              <>
                <h3 className="text-2xl font-bold mb-2">Join the Beta</h3>
                <p className="text-white/60 mb-8">
                  Free during beta. No credit card required.
                </p>

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="relative">
                    <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/30" />
                    <input
                      type="email"
                      required
                      placeholder="you@example.com"
                      value={email}
                      onChange={(e) => {
                        setEmail(e.target.value);
                        if (state === 'error') setState('idle');
                      }}
                      disabled={state === 'submitting'}
                      className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-4 py-4 text-white placeholder:text-white/30 focus:outline-none focus:border-brand/50 focus:ring-1 focus:ring-brand/30 transition-all disabled:opacity-50"
                    />
                  </div>

                  {state === 'error' && (
                    <motion.p
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="text-red-400 text-sm"
                    >
                      {errorMsg}
                    </motion.p>
                  )}

                  <button
                    type="submit"
                    disabled={state === 'submitting'}
                    className="w-full bg-brand hover:bg-brand-dark text-white font-bold py-4 rounded-xl transition-all active:scale-95 shadow-[0_0_20px_rgba(255,75,130,0.3)] disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {state === 'submitting' ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Signing up...
                      </>
                    ) : (
                      <>
                        Get Beta Access
                        <ArrowRight className="w-5 h-5" />
                      </>
                    )}
                  </button>
                </form>

                <p className="text-white/30 text-xs mt-6 text-center">
                  We'll only email your license key. No spam, ever.
                </p>
                <a
                  href={RELEASE_PAGE_URL}
                  target="_blank"
                  rel="noreferrer"
                  className="block mt-4 text-center text-sm text-brand hover:text-brand-light transition-colors"
                >
                  Already have a beta key? Download the Windows build.
                </a>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
