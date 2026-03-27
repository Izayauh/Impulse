import { motion } from 'motion/react';
import { FileText, Copy } from 'lucide-react';
import { useAppStore } from '../../lib/store';

export const SnippetsPage = () => {
  const showToast = useAppStore(state => state.showToast);

  const snippets = [
    { id: 1, title: 'Project Kickoff Notes', text: 'We need to focus on the core architecture first, then build out the UI components iteratively...', words: 234, date: 'Today' },
    { id: 2, title: 'API Design Discussion', text: 'The REST endpoints should follow resource-based naming conventions with proper HTTP verbs...', words: 156, date: 'Yesterday' },
    { id: 3, title: 'Bug Report Template', text: 'Steps to reproduce: 1. Open the dashboard 2. Click on settings 3. Toggle command mode...', words: 89, date: '2 days ago' },
  ];

  const handleCopy = async (text: string) => {
    await navigator.clipboard.writeText(text);
    showToast('Snippet copied ✓');
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="pb-8"
    >
      <header className="mb-8">
        <h1 className="text-3xl font-display font-semibold mb-2">Snippets</h1>
        <p className="text-white/50 text-[15px]">Your saved voice dictation snippets</p>
      </header>

      <div className="space-y-4">
        {snippets.map((snippet, i) => (
          <motion.div
            key={snippet.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06, duration: 0.3 }}
            className="group bg-[#121216]/80 backdrop-blur-md rounded-2xl p-6 border border-white/[0.08] hover:border-pink-500/20 transition-all shadow-lg"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-pink-500/10 flex items-center justify-center border border-pink-500/20">
                  <FileText className="w-5 h-5 text-pink-400" />
                </div>
                <div>
                  <h3 className="font-medium text-white">{snippet.title}</h3>
                  <span className="text-xs text-white/40">{snippet.date} · {snippet.words} words</span>
                </div>
              </div>
              <button
                onClick={() => handleCopy(snippet.text)}
                className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white/60 text-sm font-medium hover:bg-white/10 hover:text-white transition-all focus-visible:ring-2 focus-visible:ring-pink-500/50 focus-visible:outline-none active:scale-95 flex items-center gap-1.5"
              >
                <Copy className="w-3.5 h-3.5" />
                Copy
              </button>
            </div>
            <p className="text-white/70 text-[15px] leading-relaxed line-clamp-2 group-hover:text-white/90 transition-colors">
              {snippet.text}
            </p>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
};
