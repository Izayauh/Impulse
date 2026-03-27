import { motion } from 'motion/react';
import { BookOpen, Volume2 } from 'lucide-react';

export const DictionaryPage = () => {
  const words = [
    { term: 'Transcription', pronunciation: '/trænˈskrɪp.ʃən/', definition: 'The process of converting speech to written text', count: 342 },
    { term: 'Dictation', pronunciation: '/dɪkˈteɪ.ʃən/', definition: 'The action of saying words aloud to be typed or written down', count: 189 },
    { term: 'Voice Activity Detection', pronunciation: '/vɔɪs ækˈtɪv.ɪ.ti/', definition: 'Algorithm that detects the presence or absence of human speech', count: 56 },
    { term: 'Whisper', pronunciation: '/ˈwɪs.pɚ/', definition: 'An OpenAI speech recognition model for accurate transcription', count: 445 },
    { term: 'Latency', pronunciation: '/ˈleɪ.tən.si/', definition: 'The delay between speaking and seeing the transcribed text', count: 23 },
    { term: 'Pipeline', pronunciation: '/ˈpaɪp.laɪn/', definition: 'A series of processing stages for audio data', count: 67 },
    { term: 'Inference', pronunciation: '/ˈɪn.fɚ.əns/', definition: 'The process of running a trained model to generate predictions', count: 91 },
    { term: 'VRAM', pronunciation: '/viː.ræm/', definition: 'Video Random Access Memory used by GPU for model computation', count: 34 },
    { term: 'Hotkey', pronunciation: '/ˈhɒt.kiː/', definition: 'A keyboard shortcut that triggers voice dictation', count: 78 },
    { term: 'Chunk', pronunciation: '/tʃʌŋk/', definition: 'A segment of audio processed as a single unit', count: 112 },
    { term: 'Tokenizer', pronunciation: '/ˈtoʊ.kən.aɪ.zɚ/', definition: 'Converts text into numerical tokens for model processing', count: 15 },
    { term: 'Beam Search', pronunciation: '/biːm sɜːrtʃ/', definition: 'A decoding algorithm that explores multiple hypotheses', count: 8 },
  ];

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
        <p className="text-white/50 text-[15px]">Words and terms from your voice sessions</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {words.map((word, i) => (
          <motion.div
            key={word.term}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04, duration: 0.3 }}
            className="group bg-[#121216]/80 backdrop-blur-md rounded-2xl p-5 border border-white/[0.08] hover:border-pink-500/20 transition-all shadow-lg"
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-pink-400/70" />
                <h3 className="font-semibold text-white text-lg">{word.term}</h3>
              </div>
              <span className="text-xs text-white/30 font-medium">{word.count}×</span>
            </div>
            <p className="text-xs text-pink-300/60 font-mono mb-2 flex items-center gap-1.5">
              <Volume2 className="w-3 h-3" />
              {word.pronunciation}
            </p>
            <p className="text-white/60 text-sm leading-relaxed group-hover:text-white/80 transition-colors">
              {word.definition}
            </p>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
};
