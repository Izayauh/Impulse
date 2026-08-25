import { motion } from 'motion/react';
import { Check } from 'lucide-react';
import { BUY_URL, CONTACT_EMAIL, PRICE } from '@/src/lib/site';

const included = [
  'Lifetime licence for the computers you own',
  'Every future update, no upgrade fee',
  'Works fully offline after install',
  'Personal and commercial use',
  'Full refund if it does not work on your machine',
];

// Cloud dictation subscriptions run $10-15/month; two years is the honest
// horizon a daily tool gets judged on.
const comparison = [
  { label: 'Price today', impulse: PRICE, cloud: '$12 to $15 / month' },
  { label: 'Price after two years', impulse: `still ${PRICE}`, cloud: '$300 or more' },
  { label: 'Where your audio goes', impulse: 'nowhere', cloud: 'their servers' },
  { label: 'Works offline', impulse: 'yes', cloud: 'no' },
  { label: 'Word limits', impulse: 'none', cloud: 'metered on free tiers' },
  { label: 'Account required', impulse: 'no', cloud: 'yes' },
];

export function Pricing() {
  return (
    <section id="pricing" className="py-32 px-6 max-w-7xl mx-auto scroll-mt-20">
      <div className="text-center mb-16 max-w-3xl mx-auto">
        <h2 className="font-display text-4xl md:text-6xl font-bold mb-6">
          Pay once. <span className="text-brand">That's it.</span>
        </h2>
        <p className="text-white/60 text-lg leading-relaxed">
          Subscriptions make sense when someone else is paying for servers.
          Impulse runs on your computer, so there are no servers to pay for,
          and no reason to charge you every month.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start max-w-5xl mx-auto">
        {/* The offer */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="glass rounded-[32px] p-10 border-brand/20 relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 w-64 h-64 bg-brand/15 blur-[80px] rounded-full -z-10" />
          <div className="flex items-end gap-3 mb-2">
            <span className="font-display text-7xl font-bold">{PRICE}</span>
            <span className="text-white/50 text-lg mb-3">once, forever</span>
          </div>
          <p className="text-white/60 mb-8">One licence. No renewal. No account.</p>

          <ul className="space-y-4 mb-10">
            {included.map((item, i) => (
              <li key={i} className="flex items-start gap-3 text-white/80">
                <Check className="w-5 h-5 text-brand mt-0.5 shrink-0" />
                <span>{item}</span>
              </li>
            ))}
          </ul>

          <a
            href={BUY_URL}
            target="_blank"
            rel="noreferrer"
            className="block w-full bg-brand hover:bg-brand-dark text-white text-center px-8 py-5 rounded-2xl font-bold text-xl transition-all shadow-2xl shadow-brand/40 active:scale-95"
          >
            Get Impulse for {PRICE}
          </a>
          <p className="text-center text-xs text-white/40 mt-4">
            Secure checkout by Lemon Squeezy &middot; licence key arrives by email &middot;{' '}
            <a href="#beta" className="underline underline-offset-2 hover:text-white/70">
              or try the beta free first
            </a>
          </p>
        </motion.div>

        {/* The comparison */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.1 }}
          className="rounded-[32px] border border-white/10 overflow-hidden"
        >
          <div className="grid grid-cols-3 text-sm font-bold uppercase tracking-wider text-white/40 px-8 pt-8 pb-4">
            <span />
            <span className="text-brand normal-case tracking-normal text-base">Impulse</span>
            <span className="normal-case tracking-normal text-base text-white/60">Cloud apps</span>
          </div>
          {comparison.map((row, i) => (
            <div
              key={i}
              className={`grid grid-cols-3 px-8 py-5 text-[15px] ${i % 2 === 0 ? 'bg-white/[0.03]' : ''}`}
            >
              <span className="text-white/50">{row.label}</span>
              <span className="font-semibold text-white">{row.impulse}</span>
              <span className="text-white/50">{row.cloud}</span>
            </div>
          ))}
          <p className="px-8 py-6 text-sm text-white/40 leading-relaxed">
            Questions before buying? Email{' '}
            <a href={`mailto:${CONTACT_EMAIL}`} className="text-white/70 underline underline-offset-2">
              {CONTACT_EMAIL}
            </a>{' '}
            and you'll get an answer from the person who built it.
          </p>
        </motion.div>
      </div>
    </section>
  );
}
