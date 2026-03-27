import { useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Sidebar } from './components/Sidebar';
import { WelcomeCard } from './components/WelcomeCard';
import { ActionCard } from './components/ActionCard';
import { VelocityCard } from './components/VelocityCard';
import { LiveFeedCard } from './components/LiveFeedCard';
import { SettingsModal } from './components/SettingsModal';
import { SnippetsPage } from './components/pages/SnippetsPage';
import { DictionaryPage } from './components/pages/DictionaryPage';
import { AchievementsPage } from './components/pages/AchievementsPage';
import { ChallengesPage } from './components/pages/ChallengesPage';
import { Toast } from './components/Toast';
import { useAppStore } from './lib/store';
import { useState } from 'react';

export default function App() {
  const initBridge = useAppStore(state => state.initBridge);
  const activePage = useAppStore(state => state.activePage);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  useEffect(() => {
    initBridge();
  }, [initBridge]);

  const renderPage = () => {
    switch (activePage) {
      case 'snippets':
        return <SnippetsPage key="snippets" />;
      case 'dictionary':
        return <DictionaryPage key="dictionary" />;
      case 'achievements':
        return <AchievementsPage key="achievements" />;
      case 'challenges':
        return <ChallengesPage key="challenges" />;
      case 'home':
      default:
        return <HomePage key="home" />;
    }
  };

  return (
    <div className="flex min-h-screen font-sans bg-[#0E0E12] text-white">
      <Sidebar onOpenSettings={() => setIsSettingsOpen(true)} />

      <main className="flex-1 ml-[280px] p-8 max-w-[1400px] mx-auto w-full relative">
        <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
        <Toast />

        {/* Ambient background blobs */}
        <div className="fixed top-20 right-20 w-[500px] h-[500px] bg-pink-500/[0.04] blur-[120px] rounded-full pointer-events-none" />
        <div className="fixed bottom-20 left-[400px] w-[400px] h-[400px] bg-purple-500/[0.03] blur-[100px] rounded-full pointer-events-none" />

        <AnimatePresence mode="wait">
          {renderPage()}
        </AnimatePresence>
      </main>
    </div>
  );
}

function HomePage() {
  const stats = useAppStore(state => state.stats);
  const showToast = useAppStore(state => state.showToast);

  const handleCopyLast = async () => {
    const lastTranscript = stats?.recentTranscripts?.[0]?.text;
    if (lastTranscript) {
      await useAppStore.getState().copyToClipboard(lastTranscript);
      showToast('Copied to clipboard ✓');
    } else {
      showToast('Nothing to copy');
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
    >
      {/* Top bar */}
      <header className="mb-6 flex justify-between items-center">
        <button
          onClick={handleCopyLast}
          className="px-4 py-1.5 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 transition-colors text-sm font-medium text-white/80 focus-visible:ring-2 focus-visible:ring-pink-500/50 focus-visible:outline-none active:scale-95"
        >
          Copy Last
        </button>
      </header>

      <div className="flex flex-col lg:flex-row gap-6 items-start h-[calc(100vh-120px)]">
        {/* Left Column */}
        <div className="w-full lg:w-[420px] shrink-0 flex flex-col gap-6">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          >
            <WelcomeCard />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          >
            <ActionCard />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          >
            <VelocityCard />
          </motion.div>
        </div>

        {/* Right Column */}
        <motion.div
          className="flex-1 min-w-0 h-full"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        >
          <LiveFeedCard />
        </motion.div>
      </div>
    </motion.div>
  );
}
