import { motion } from 'motion/react';
import { AppWindow, BookA, Cpu, Flame, Hand, PlaneTakeoff } from 'lucide-react';

// Every claim here is a shipped behavior, not a roadmap item. The site doubles
// as a work sample, so nothing on it should be something the app can't do.
const features = [
  {
    title: 'Works in every app',
    description:
      "There's no Impulse window to paste out of. Hold the key and the text lands in whatever has focus: your email, your DAW, your browser, your terminal.",
    icon: AppWindow,
    className: 'md:col-span-2 md:row-span-2 bg-gradient-to-br from-brand/10 to-transparent',
    hasGlow: true,
  },
  {
    title: 'Hands-free mode',
    description: 'Tap Ctrl+Win+Alt once to record without holding anything. Tap again to stop.',
    icon: Hand,
    className: 'bg-surface-muted/50 hover:bg-surface-muted transition-colors',
  },
  {
    title: 'Knows your hardware',
    description:
      'Probes what your GPU can actually run instead of trusting spec sheets, picks the right model, and self-corrects if the fast path fails.',
    icon: Cpu,
    className: 'bg-surface-muted/50 hover:bg-surface-muted transition-colors',
  },
  {
    title: 'Works on a plane',
    description:
      'A fallback model ships in the installer. Airplane mode on, wifi dead, tunnel: it keeps typing.',
    icon: PlaneTakeoff,
    className: 'bg-surface-muted/50 hover:bg-surface-muted transition-colors',
  },
  {
    title: 'Learns your words',
    description:
      'Add names, jargon, and snippets so "Ableton" never comes out as "abel tone" again.',
    icon: BookA,
    className: 'bg-surface-muted/50 hover:bg-surface-muted transition-colors',
  },
  {
    title: 'Streaks and stats',
    description:
      'Daily word counts, streaks, and achievements. Habits stick when you can see them.',
    icon: Flame,
    className: 'md:col-span-2 bg-gradient-to-r from-orange-500/5 to-brand/5',
  },
];

export function Features() {
  return (
    <section id="features" className="py-32 px-6 max-w-7xl mx-auto">
      <div className="text-center mb-20">
        <h2 className="font-display text-4xl md:text-6xl font-bold mb-6">
          Most people talk at 150 words a minute. <br className="hidden md:block" />
          <span className="text-brand">Almost nobody types that fast.</span>
        </h2>
        <p className="text-white/60 text-lg max-w-2xl mx-auto">
          Emails, messages, notes mid-session, whole documents. If you'd rather say it than type it,
          Impulse is the shortest path from thought to text.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {features.map((feature, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.08 }}
            className={`group relative overflow-hidden rounded-3xl border border-white/5 p-8 flex flex-col justify-between ${feature.className}`}
          >
            {feature.hasGlow && (
              <div className="absolute top-0 right-0 w-64 h-64 bg-brand/20 blur-[80px] rounded-full -z-10 group-hover:bg-brand/30 transition-colors" />
            )}
            <div className="relative z-10 h-full flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <feature.icon className="w-6 h-6 text-brand" />
                </div>
                <h3 className="text-2xl font-bold mb-3">{feature.title}</h3>
                <p className="text-white/60 leading-relaxed text-lg">{feature.description}</p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
