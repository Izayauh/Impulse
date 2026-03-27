import React, { useState } from 'react';
import { motion } from 'motion/react';
import { FileText, Copy, Trash2, Plus } from 'lucide-react';
import { useAppStore } from '../../lib/store';

export const SnippetsPage = () => {
  const snippets = useAppStore(state => state.snippets);
  const deleteSnippet = useAppStore(state => state.deleteSnippet);
  const addSnippet = useAppStore(state => state.addSnippet);
  const showToast = useAppStore(state => state.showToast);
  const copyToClipboard = useAppStore(state => state.copyToClipboard);

  const [newTrigger, setNewTrigger] = useState('');
  const [newReplacement, setNewReplacement] = useState('');

  const handleCopy = async (text: string) => {
    await copyToClipboard(text);
    showToast('Snippet replacement copied ✓');
  };

  const handleAddSnippet = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newTrigger.trim() && newReplacement.trim()) {
      await addSnippet(newTrigger.trim(), newReplacement.trim());
      setNewTrigger('');
      setNewReplacement('');
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="pb-8"
    >
      <header className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-display font-semibold mb-2">Snippets</h1>
          <p className="text-white/50 text-[15px]">Automate your workflow with custom voice shortcuts</p>
        </div>
      </header>

      <form onSubmit={handleAddSnippet} className="mb-8 p-4 bg-[#121216]/80 rounded-2xl border border-white/5 flex flex-col md:flex-row gap-4 items-end shadow-lg">
        <div className="flex-1 w-full">
          <label className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-2 block">If I say...</label>
          <input 
            type="text" 
            value={newTrigger}
            onChange={(e) => setNewTrigger(e.target.value)}
            placeholder="e.g. omw"
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-white/20 focus:outline-none focus:ring-2 focus:ring-pink-500/50"
          />
        </div>
        <div className="flex-[2] w-full">
          <label className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-2 block">Type this...</label>
          <input 
            type="text" 
            value={newReplacement}
            onChange={(e) => setNewReplacement(e.target.value)}
            placeholder="e.g. On my way!"
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-white/20 focus:outline-none focus:ring-2 focus:ring-pink-500/50"
          />
        </div>
        <button 
          type="submit"
          disabled={!newTrigger.trim() || !newReplacement.trim()}
          className="w-full md:w-auto px-6 py-2.5 rounded-xl bg-pink-500 hover:bg-pink-400 disabled:opacity-50 disabled:hover:bg-pink-500 text-white font-medium transition-colors shadow-[0_4px_16px_rgba(236,72,153,0.3)] hover:shadow-[0_4px_20px_rgba(236,72,153,0.5)] flex items-center justify-center gap-2"
        >
          <Plus className="w-4 h-4" /> Add
        </button>
      </form>

      <div className="space-y-4">
        {snippets.length === 0 ? (
          <div className="text-center py-12 text-white/40">No snippets configured yet. Add one above!</div>
        ) : (
          snippets.map((snippet, i) => (
            <motion.div
              key={snippet.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04, duration: 0.3 }}
              className="group bg-[#121216]/80 backdrop-blur-md rounded-2xl p-6 border border-white/[0.08] hover:border-pink-500/20 transition-all shadow-lg"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-pink-500/10 flex items-center justify-center border border-pink-500/20 shrink-0">
                    <FileText className="w-5 h-5 text-pink-400" />
                  </div>
                  <div>
                    <span className="text-xs text-pink-400/80 font-mono mb-1 block">Trigger</span>
                    <h3 className="font-semibold text-white text-lg">"{snippet.trigger}"</h3>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleCopy(snippet.replacement)}
                    className="p-2 rounded-lg bg-white/5 border border-white/10 text-white/60 hover:bg-white/10 hover:text-white transition-all focus-visible:ring-2 focus-visible:ring-pink-500/50 focus-visible:outline-none active:scale-95"
                    aria-label="Copy replacement"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => deleteSnippet(snippet.id)}
                    className="p-2 rounded-lg bg-white/5 border border-white/10 text-white/60 hover:bg-red-500/20 hover:text-red-400 hover:border-red-500/30 transition-all focus-visible:ring-2 focus-visible:ring-red-500/50 focus-visible:outline-none active:scale-95"
                    aria-label="Delete snippet"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              <div className="mt-4 pl-14">
                <span className="text-xs text-emerald-400/80 font-mono mb-1 block">Replacement</span>
                <p className="text-white/80 text-[15px] leading-relaxed transition-colors">
                  {snippet.replacement}
                </p>
              </div>
            </motion.div>
          ))
        )}
      </div>
    </motion.div>
  );
};
