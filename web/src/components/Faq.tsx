import { motion } from 'motion/react';
import { CONTACT_EMAIL, GITHUB_REPO_URL } from '@/src/lib/site';

const faqs = [
  {
    q: 'Does it really work offline?',
    a: 'Yes. A speech model ships inside the installer, so after setup nothing requires a connection. The demo video on this page is filmed with airplane mode on.',
  },
  {
    q: 'What do I need to run it?',
    a: 'A 64-bit Windows 10 or 11 PC. The installer is about 400MB because the model comes with it. A GPU helps but is not required; Impulse checks what your hardware can do and picks the right model on its own.',
  },
  {
    q: 'Is my audio or text ever uploaded?',
    a: 'No. Transcription happens on your CPU or GPU. The app makes exactly two kinds of network request: validating your licence key, and anonymous usage counts if you opt in. The source is public, so you can verify that claim instead of taking it on faith.',
  },
  {
    q: 'Why is it a one-time purchase?',
    a: 'Subscription dictation apps pay for cloud servers with your monthly fee. Impulse uses your computer, so the ongoing cost they charge for does not exist here.',
  },
  {
    q: 'What if it does not work on my machine?',
    a: `Full refund. Email ${CONTACT_EMAIL} and it gets sorted. Hardware varies, and you should not pay for software that does not run for you.`,
  },
  {
    q: 'Is it open source?',
    a: 'Source-available. You can read every line on GitHub to verify what it does, which matters for an app that hears your voice. Redistribution and resale are not permitted.',
  },
];

export function Faq() {
  return (
    <section id="faq" className="py-32 px-6 max-w-4xl mx-auto">
      <h2 className="font-display text-4xl md:text-5xl font-bold mb-16 text-center">
        Fair questions
      </h2>
      <div className="space-y-4">
        {faqs.map((f, i) => (
          <motion.details
            key={i}
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.05 }}
            className="group glass rounded-2xl border-white/5 open:border-brand/20"
          >
            <summary className="cursor-pointer list-none px-8 py-6 font-bold text-lg flex items-center justify-between gap-4">
              {f.q}
              <span className="text-brand text-2xl leading-none transition-transform group-open:rotate-45">+</span>
            </summary>
            <p className="px-8 pb-8 text-white/60 leading-relaxed">{f.a}</p>
          </motion.details>
        ))}
      </div>
      <p className="text-center text-white/40 mt-12 text-sm">
        Something else?{' '}
        <a href={`mailto:${CONTACT_EMAIL}`} className="text-white/70 underline underline-offset-2">
          {CONTACT_EMAIL}
        </a>{' '}
        &middot;{' '}
        <a href={GITHUB_REPO_URL} target="_blank" rel="noreferrer" className="text-white/70 underline underline-offset-2">
          open an issue
        </a>
      </p>
    </section>
  );
}
