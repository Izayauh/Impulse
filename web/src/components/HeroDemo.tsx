import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useInView, useReducedMotion } from 'motion/react';
import { Check, Loader2, PlaneTakeoff, WifiOff } from 'lucide-react';
import { cn } from '@/src/lib/utils';

/**
 * The hero demo. Not a video: a drawn loop of the whole product.
 *
 * hold the key -> the Impulse panel pops up -> you talk -> let go ->
 * filler words come out, punctuation goes in, the text lands where the cursor is.
 *
 * Every step shown here is shipped behaviour. The filler list mirrors
 * scrub_fillers() in the app; punctuation and capitalisation come from Whisper.
 */

type Phase = 'idle' | 'press' | 'record' | 'transcribe' | 'type' | 'done' | 'hold';

interface Scene {
  app: string;
  /** Raw speech. Tokens starting with ~ are fillers the app removes. */
  raw: string;
  clean: string;
  chrome: 'mail' | 'chat' | 'notes';
}

const SCENES: Scene[] = [
  {
    app: 'Mail',
    chrome: 'mail',
    raw: '~um can you tell the team the launch is ~uh slipping to Monday, we’re still waiting on legal to sign off on the new terms page',
    clean: 'Can you tell the team the launch is slipping to Monday? We’re still waiting on legal to sign off on the new terms page.',
  },
  {
    app: 'Chat',
    chrome: 'chat',
    raw: '~uh the hook is done, I’m gonna ~like bounce a rough mix tonight and send it over before the session tomorrow',
    clean: 'The hook is done. I’m gonna bounce a rough mix tonight and send it over before the session tomorrow.',
  },
  {
    app: 'Notes',
    chrome: 'notes',
    raw: '~okay ~so ~um second verse needs a lift ~you ~know maybe double the vocal and pull the 808 down two dB',
    clean: 'Second verse needs a lift. Maybe double the vocal and pull the 808 down two dB.',
  },
];

const RAW_WORD_MS = 150;
const CLEAN_WORD_MS = 45;

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function HeroDemo() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { amount: 0.3 });
  const reduced = useReducedMotion();

  const [scene, setScene] = useState(0);
  const [phase, setPhase] = useState<Phase>('idle');
  const [rawN, setRawN] = useState(0);
  const [cleanN, setCleanN] = useState(0);

  const current = SCENES[scene];
  const rawTokens = current.raw.split(' ');
  const cleanTokens = current.clean.split(' ');

  useEffect(() => {
    if (reduced) {
      setPhase('hold');
      setRawN(rawTokens.length);
      setCleanN(cleanTokens.length);
      return;
    }
    if (!inView) return;

    let cancelled = false;
    const step = async (ms: number) => {
      await sleep(ms);
      return !cancelled;
    };

    (async () => {
      const raw = SCENES[scene].raw.split(' ');
      const clean = SCENES[scene].clean.split(' ');

      setPhase('idle');
      setRawN(0);
      setCleanN(0);
      if (!(await step(1100))) return;

      setPhase('press');
      if (!(await step(420))) return;

      setPhase('record');
      for (let i = 1; i <= raw.length; i++) {
        if (!(await step(RAW_WORD_MS))) return;
        setRawN(i);
      }
      if (!(await step(500))) return;

      setPhase('transcribe');
      if (!(await step(650))) return;

      setPhase('type');
      for (let i = 1; i <= clean.length; i++) {
        if (!(await step(CLEAN_WORD_MS))) return;
        setCleanN(i);
      }

      setPhase('done');
      if (!(await step(900))) return;

      setPhase('hold');
      if (!(await step(1700))) return;

      setScene((s) => (s + 1) % SCENES.length);
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scene, inView, reduced]);

  const recording = phase === 'record';
  const pressed = phase === 'press' || phase === 'record';
  const hudVisible = phase === 'press' || phase === 'record' || phase === 'transcribe' || phase === 'type' || phase === 'done';
  const showRaw = phase === 'record' || phase === 'transcribe';

  return (
    <div
      ref={ref}
      className="relative w-full aspect-[4/5] sm:aspect-[16/10] overflow-hidden rounded-3xl border border-white/10 bg-[#0b0b0f] shadow-2xl shadow-brand/10"
      aria-label="Impulse in use: hold the hotkey, speak, release, and clean text is typed into the app you are in"
    >
      {/* Desktop backdrop */}
      <div className="absolute inset-0 -z-0">
        <div className="absolute -top-1/4 -left-1/4 w-2/3 h-2/3 bg-brand/15 blur-[120px] rounded-full" />
        <div className="absolute -bottom-1/3 -right-1/4 w-2/3 h-2/3 bg-blue-500/10 blur-[120px] rounded-full" />
        <div
          className="absolute inset-0 opacity-[0.35]"
          style={{
            backgroundImage: 'radial-gradient(rgba(255,255,255,0.08) 1px, transparent 1px)',
            backgroundSize: '22px 22px',
          }}
        />
      </div>

      {/* Status strip: the privacy proof lives here, always on */}
      <div className="absolute top-3 sm:top-4 left-3 sm:left-5 right-3 sm:right-5 flex items-center justify-between text-[10px] sm:text-xs z-10">
        <span className="glass-dark rounded-full px-3 py-1 text-white/70 font-medium">{current.app}</span>
        <div className="flex items-center gap-2">
          <span className="glass-dark rounded-full px-3 py-1 text-white/70 font-medium flex items-center gap-1.5">
            <PlaneTakeoff className="w-3 h-3 text-brand" />
            Airplane mode on
          </span>
          <span className="hidden sm:flex glass-dark rounded-full px-3 py-1 text-white/70 font-medium items-center gap-1.5">
            <WifiOff className="w-3 h-3 text-white/50" />
            0 bytes sent
          </span>
        </div>
      </div>

      {/* The app the user is in */}
      <div className="absolute inset-x-[5%] sm:inset-x-[12%] top-[12%] sm:top-[15%] bottom-[40%] sm:bottom-[27%]">
        {/* The frame stays mounted; only its contents crossfade between scenes */}
        <div className="h-full rounded-2xl bg-[#121216]/95 border border-white/10 shadow-2xl overflow-hidden flex flex-col">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={current.app}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="h-full flex flex-col"
            >
              <WindowChrome scene={current} />
              <div className="flex-1 px-4 sm:px-6 py-3 sm:py-4 text-[13px] sm:text-[15px] md:text-base leading-relaxed text-white/90 font-sans text-left">
                {cleanTokens.slice(0, cleanN).join(' ')}
                {cleanN > 0 && cleanN < cleanTokens.length ? ' ' : ''}
                <span className={cn('inline-block w-[2px] h-[1.1em] align-[-0.2em] bg-brand ml-px', phase === 'type' ? '' : 'caret')} />
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      {/* What you said, as you say it */}
      <div className="absolute left-[5%] right-[5%] sm:left-[12%] sm:right-[40%] bottom-[22%] sm:bottom-[17%] z-10 pointer-events-none text-left">
        <AnimatePresence>
          {showRaw && (
            <motion.p
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4, transition: { duration: 0.25 } }}
              className="text-[11px] sm:text-sm md:text-[15px] leading-snug text-white/60 font-medium"
            >
              <span className="text-white/30 mr-2 uppercase tracking-wider text-[9px] sm:text-[10px] font-bold">You said</span>
              {rawTokens.slice(0, rawN).map((t, i) => {
                const filler = t.startsWith('~');
                const word = filler ? t.slice(1) : t;
                return (
                  <span
                    key={i}
                    className={cn(
                      'transition-colors duration-300',
                      filler && (phase === 'transcribe' ? 'text-brand/40 line-through decoration-brand/60' : 'text-brand'),
                    )}
                  >
                    {word}{' '}
                  </span>
                );
              })}
            </motion.p>
          )}
        </AnimatePresence>
      </div>

      {/* Keycaps */}
      <div className="absolute left-[5%] sm:left-[12%] bottom-[5%] sm:bottom-[6%] z-10 flex items-end gap-2 sm:gap-3">
        <Keycap label="Ctrl" pressed={pressed} />
        <Keycap label="Win" pressed={pressed} />
        <span className="hidden sm:inline ml-2 mb-1 text-xs text-white/40 font-medium">
          {pressed ? 'hold and talk' : phase === 'transcribe' ? 'let go' : phase === 'type' || phase === 'done' || phase === 'hold' ? 'typed for you' : 'hold to talk'}
        </span>
      </div>

      {/* The Impulse panel, drawn from the real one */}
      <div className="absolute right-[5%] sm:right-[12%] bottom-[5%] sm:bottom-[6%] z-20">
        <AnimatePresence>
          {hudVisible && (
            <motion.div
              initial={{ opacity: 0, scale: 0.6, y: 16 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 10, transition: { duration: 0.25 } }}
              transition={{ type: 'spring', stiffness: 420, damping: 24 }}
              className="origin-bottom-right"
            >
              <Hud phase={phase} recording={recording} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function WindowChrome({ scene }: { scene: Scene }) {
  return (
    <div className="border-b border-white/5 text-left">
      <div className="flex items-center gap-1.5 px-4 pt-3 pb-2">
        <span className="w-2.5 h-2.5 rounded-full bg-white/10" />
        <span className="w-2.5 h-2.5 rounded-full bg-white/10" />
        <span className="w-2.5 h-2.5 rounded-full bg-white/10" />
      </div>
      {scene.chrome === 'mail' && (
        <div className="px-4 sm:px-6 pb-3 text-[11px] sm:text-sm text-white/50 space-y-1">
          <div><span className="text-white/30 w-14 inline-block">To</span>Marcus Chen</div>
          <div><span className="text-white/30 w-14 inline-block">Subject</span><span className="text-white/80">Launch timeline</span></div>
        </div>
      )}
      {scene.chrome === 'chat' && (
        <div className="px-4 sm:px-6 pb-3 text-[11px] sm:text-sm space-y-1.5">
          <div className="text-white/40 font-semibold"># production</div>
          <div className="flex gap-2 items-baseline">
            <span className="text-brand-light font-semibold">Dev</span>
            <span className="text-white/60">how&rsquo;s the hook coming?</span>
          </div>
        </div>
      )}
      {scene.chrome === 'notes' && (
        <div className="px-4 sm:px-6 pb-3 text-[11px] sm:text-sm text-white/50">
          <span className="text-white/80 font-semibold">Session notes</span>
          <span className="text-white/30"> &middot; Tuesday</span>
        </div>
      )}
    </div>
  );
}

function Keycap({ label, pressed }: { label: string; pressed: boolean }) {
  return (
    <span
      className={cn(
        'inline-flex items-center justify-center min-w-[42px] sm:min-w-[52px] px-2 h-8 sm:h-10 rounded-lg font-mono text-[11px] sm:text-sm font-bold select-none',
        'bg-[#1c1c22] border border-white/10 text-white/80 transition-all duration-150',
        pressed
          ? 'translate-y-[3px] border-b border-brand/60 text-white shadow-[0_0_18px_rgba(246,51,154,0.35)] bg-[#2a1520]'
          : 'border-b-4 border-b-black/60 shadow-lg',
      )}
    >
      {label}
    </span>
  );
}

function Hud({ phase, recording }: { phase: Phase; recording: boolean }) {
  const state =
    phase === 'transcribe'
      ? { label: 'TRANSCRIBING', accent: '#fb64b6', chip: 'rgba(246,51,154,0.12)', hint: 'Processing audio on this PC.' }
      : phase === 'type' || phase === 'done' || phase === 'hold'
        ? { label: 'DONE', accent: '#5CE394', chip: 'rgba(92,227,148,0.12)', hint: 'Pasted where your cursor was.' }
        : { label: 'RECORDING', accent: '#f6339a', chip: 'rgba(246,51,154,0.14)', hint: 'Keep the keys held while you talk.' };

  return (
    <div
      className="w-[196px] sm:w-[300px] rounded-2xl border px-3 sm:px-4 py-2.5 sm:py-3 bg-[#101218]/95 backdrop-blur-xl shadow-2xl text-left"
      style={{ borderColor: `${state.accent}55` }}
    >
      <div className="flex items-center justify-between gap-3">
        <span
          className="inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-[9px] sm:text-[10px] font-bold tracking-wider text-white"
          style={{ background: state.chip, border: `1px solid ${state.accent}88` }}
        >
          {phase === 'transcribe' ? (
            <Loader2 className="w-3 h-3 animate-spin" style={{ color: state.accent }} />
          ) : state.label === 'DONE' ? (
            <Check className="w-3 h-3" style={{ color: state.accent }} />
          ) : (
            <span className="relative flex w-2 h-2">
              <span className="absolute inline-flex h-full w-full rounded-full opacity-60 animate-ping" style={{ background: state.accent }} />
              <span className="relative inline-flex rounded-full h-2 w-2" style={{ background: state.accent }} />
            </span>
          )}
          {state.label}
        </span>
        <span className="font-mono text-[11px] sm:text-sm font-bold text-white">Ctrl+Win</span>
      </div>
      <div className="mt-2 flex items-center justify-end sm:justify-between gap-3">
        <span className="hidden sm:inline text-xs text-white/60 truncate">{state.hint}</span>
        <LevelBars active={recording} accent={state.accent} />
      </div>
    </div>
  );
}

const BAR_PHASES = [0.1, 0.5, 0.9, 0.3, 0.7, 0.2, 0.8, 0.4, 0.6, 0.0];

function LevelBars({ active, accent }: { active: boolean; accent: string }) {
  return (
    <span className="flex items-end gap-[3px] h-4 shrink-0" aria-hidden>
      {BAR_PHASES.map((p, i) => (
        <motion.span
          key={i}
          className="w-[3px] rounded-full"
          style={{ background: accent, height: 16, originY: 1 }}
          animate={active ? { scaleY: [0.25, 0.4 + p * 0.6, 0.3, 0.9 - p * 0.5, 0.25] } : { scaleY: 0.2 }}
          transition={active ? { duration: 1.1, repeat: Infinity, ease: 'easeInOut', delay: p * 0.3 } : { duration: 0.3 }}
        />
      ))}
    </span>
  );
}
