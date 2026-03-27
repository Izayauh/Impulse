import React, { useState } from 'react';
import { motion } from 'motion/react';
import { BookOpen, Plus, Sparkles } from 'lucide-react';
import { useAppStore } from '../../lib/store';

export const DictionaryPage = () => {
  const dictionary = useAppStore(state => state.dictionary);
  const addDictionaryWord = useAppStore(state => state.addDictionaryWord);
  
  const [newWord, setNewWord] = useState('');

  const handleAddWord = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newWord.trim()) {
      await addDictionaryWord(newWord.trim());
      setNewWord('');
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
      <header className="mb-8">
        <h1 className="text-3xl font-display font-semibold mb-2">Dictionary</h1>
        <p className="text-white/50 text-[15px]">Custom vocabulary words that Whisper will prioritize</p>
      </header>

      <form onSubmit={handleAddWord} className="mb-8 p-4 bg-[#121216]/80 rounded-2xl border border-white/5 flex gap-4 items-end shadow-lg">
        <div className="flex-1">
          <label className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-2 block">New Vocabulary Word</label>
          <input 
            type="text" 
            value={newWord}
            onChange={(e) => setNewWord(e.target.value)}
            placeholder="e.g. AcmeCorp"
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-white/20 focus:outline-none focus:ring-2 focus:ring-pink-500/50"
          />
        </div>
        <button 
          type="submit"
          disabled={!newWord.trim()}
          className="px-6 py-2.5 rounded-xl bg-pink-500 hover:bg-pink-400 disabled:opacity-50 disabled:hover:bg-pink-500 text-white font-medium transition-colors shadow-[0_4px_16px_rgba(236,72,153,0.3)] hover:shadow-[0_4px_20px_rgba(236,72,153,0.5)] flex items-center gap-2"
        >
          <Plus className="w-4 h-4" /> Add
        </button>
      </form>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {dictionary.length === 0 ? (
          <div className="col-span-full text-center py-12 text-white/40">No custom vocabulary added yet.</div>
        ) : (
          dictionary.map((word, i) => (
            <motion.div
              key={word + i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04, duration: 0.3 }}
              className="group bg-[#121216]/80 backdrop-blur-md rounded-2xl p-5 border border-white/[0.08] hover:border-pink-500/20 transition-all shadow-lg flex items-center justify-between"
            >
              <div className="flex items-center gap-3 overflow-hidden">
                <BookOpen className="w-5 h-5 text-pink-400/70 shrink-0" />
                <h3 className="font-semibold text-white text-lg truncate">{word}</h3>
              </div>
              <Sparkles className="w-4 h-4 text-emerald-400/0 group-hover:text-emerald-400/70 transition-colors shrink-0" />
            </motion.div>
          ))
        )}
      </div>
    </motion.div>
  );
};
