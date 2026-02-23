import { motion } from 'motion/react';
import { Zap, Shield, Globe, Cpu, Flame, CheckCircle } from 'lucide-react';

const features = [
  {
    title: "Instant Stylization",
    description: "Turn rough thoughts into polished prose, code, or emails instantly using our blazing fast on-device AI.",
    icon: Zap,
    className: "md:col-span-2 md:row-span-2 bg-gradient-to-br from-brand/10 to-transparent",
    hasGlow: true,
  },
  {
    title: "Global Hotkey",
    description: "One key to rule them all. Dictate into any app, anywhere.",
    icon: Globe,
    className: "bg-surface-muted/50 hover:bg-surface-muted transition-colors",
  },
  {
    title: "Privacy First",
    description: "On-device processing for maximum security. Your data never leaves your machine.",
    icon: Shield,
    className: "bg-surface-muted/50 hover:bg-surface-muted transition-colors",
  },
  {
    title: "Gamified Focus",
    description: "Build streaks, unlock achievements, and level up your productivity.",
    icon: Flame,
    className: "md:col-span-2 bg-gradient-to-r from-orange-500/5 to-brand/5",
  }
];

export function Features() {
  return (
    <section id="features" className="py-32 px-6 max-w-7xl mx-auto">
      <div className="text-center mb-20">
        <h2 className="font-display text-4xl md:text-6xl font-bold mb-6">Built for the speed of thought.</h2>
        <p className="text-white/60 text-lg max-w-2xl mx-auto">
          Impulse isn't just a component; it's an extension of your mind.
          Designed to keep you firmly in the flow state.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {features.map((feature, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
            className={`group relative overflow-hidden rounded-3xl border border-white/5 p-8 flex flex-col justify-between ${feature.className}`}
          >
            {feature.hasGlow && (
              <div className="absolute top-0 right-0 w-64 h-64 bg-brand/20 blur-[80px] rounded-full -z-10 group-hover:bg-brand/30 transition-colors" />
            )}

            <div className="relative z-10 h-full flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform shadow-[0_0_15px_rgba(255,255,255,0.05)]">
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
