import { useAppStore } from '../lib/store';

export const ActionCard = () => {
  const stats = useAppStore(state => state.stats);
  const showToast = useAppStore(state => state.showToast);

  const handleCopyLatest = async () => {
    const lastTranscript = stats?.recentTranscripts?.[0]?.text;
    if (lastTranscript) {
      await navigator.clipboard.writeText(lastTranscript);
      showToast('Latest dictation copied ✓');
    } else {
      showToast('Nothing to copy yet');
    }
  };

  return (
    <div className="bg-[#131317]/80 flex items-center justify-between backdrop-blur-md rounded-2xl p-6 border border-white/[0.08] hover:border-white/10 transition-colors shadow-lg group">
      <div className="flex-1 pr-4">
        <h3 className="text-xl font-display font-semibold mb-1">
          Voice dictation in any app
        </h3>
        <p className="text-white/50 text-[15px] leading-snug">
          Trigger, speak, and keep momentum while stacking XP and streak points.
        </p>
      </div>
      <button
        onClick={handleCopyLatest}
        className="bg-pink-500 hover:bg-pink-400 text-white font-bold tracking-wide py-3 px-5 rounded-[1.25rem] text-sm shadow-[0_4px_16px_rgba(236,72,153,0.3)] hover:shadow-[0_4px_20px_rgba(236,72,153,0.5)] transition-all shrink-0 focus-visible:ring-2 focus-visible:ring-pink-300 focus-visible:outline-none active:scale-95"
      >
        Copy<br/>latest
      </button>
    </div>
  );
};
