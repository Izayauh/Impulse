import { motion } from 'motion/react';
import { Code2, PlaneTakeoff, Wifi } from 'lucide-react';
import { GITHUB_REPO_URL, PRIVACY_URL } from '@/src/lib/site';

const proofs = [
  {
    icon: PlaneTakeoff,
    title: 'It works in airplane mode',
    body: "That's not a marketing line, it's the demo. Turn your network off and dictate. A cloud app physically cannot pass this test.",
  },
  {
    icon: Code2,
    title: "Don't trust us. Read the code.",
    body: 'The full source is public on GitHub. You can see exactly what the app does with your audio before you run it.',
    link: { href: GITHUB_REPO_URL, label: 'Read the source' },
  },
  {
    icon: Wifi,
    title: 'Two network calls, both visible',
    body: 'Licence validation, and anonymous usage counts if you opt in. No audio, no text, ever. The privacy policy lists every byte.',
    link: { href: PRIVACY_URL, label: 'Privacy policy' },
  },
];

export function Privacy() {
  return (
    <section id="privacy" className="py-32 px-6 bg-surface-muted/50">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-20 max-w-3xl mx-auto">
          <h2 className="font-display text-4xl md:text-6xl font-bold mb-6 leading-tight">
            Your voice never <br />
            <span className="text-brand">leaves your computer.</span>
          </h2>
          <p className="text-white/60 text-lg leading-relaxed">
            Cloud dictation apps upload your voice and answer the privacy question with compliance
            badges. Impulse answers it differently: there is nothing to certify, because nothing is sent.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {proofs.map((p, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="glass rounded-3xl p-8 border-white/5 flex flex-col"
            >
              <div className="w-12 h-12 rounded-2xl bg-brand/10 flex items-center justify-center mb-6">
                <p.icon className="w-6 h-6 text-brand" />
              </div>
              <h3 className="text-xl font-bold mb-3">{p.title}</h3>
              <p className="text-white/60 leading-relaxed flex-1">{p.body}</p>
              {p.link && (
                <a
                  href={p.link.href}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-6 text-brand font-semibold hover:underline underline-offset-4"
                >
                  {p.link.label} &rarr;
                </a>
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
