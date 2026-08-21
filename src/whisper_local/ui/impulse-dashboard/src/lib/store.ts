import { create } from 'zustand';

// Type definitions based on Python AppApi.get_stats() return shape
export interface AppStats {
    userName: string;
    xp: number;
    totalXp: number;
    xpToNextLevel: number;
    level: number;
    rank: string;
    nextRank: string;
    today: number;
    thisWeek: number;
    thisMonth: number;
    avgWpm: number;
    bestWpm: number;
    totalWords: number;
    totalSessions: number;
    totalTime: string;
    dayStreak: number;
    weekStreak: number;
    recentTranscripts: Array<{ text: string; fullText?: string; words: number; time: string }>;
    last7Days: Array<{ day: string; words: number }>;
    records: any;
}

export interface Achievement {
    id: number;
    key?: string;
    category: string;
    name: string;
    description: string;
    icon: string;
    rarity: string;
    xp: number;
    unlocked: boolean;
    progress?: number;
}

export type PageId = 'home' | 'snippets' | 'dictionary' | 'achievements' | 'challenges';

export interface AppSettings {
    model: string;
    vadSensitivity: number;
    silenceTimeout: number;
    commandMode: boolean;
    autoCopy: boolean;
}

export interface Snippet {
    id: number;
    trigger: string;
    replacement: string;
}

interface ToastState {
    message: string;
    visible: boolean;
}

interface AppState {
    stats: AppStats | null;
    achievements: Achievement[];
    snippets: Snippet[];
    dictionary: string[];
    isReady: boolean;
    activePage: PageId;
    settings: AppSettings;
    modelLoading: string | null;
    modelLoaded: string | null;
    modelLoadError: string | null;
    toast: ToastState;
    setActivePage: (page: PageId) => void;
    updateSettings: (partial: Partial<AppSettings>) => void;
    setModelMode: (model: string) => Promise<void>;
    showToast: (message: string) => void;
    copyToClipboard: (text: string) => Promise<boolean>;
    addSnippet: (trigger: string, replacement: string) => Promise<void>;
    deleteSnippet: (id: number) => Promise<void>;
    addDictionaryWord: (word: string) => Promise<void>;
    initBridge: () => void;
    loadDevData: () => void;
    fetchUserData: () => Promise<void>;
}

/**
 * Detect whether we're running inside a pywebview window.
 * The bridge object is injected by pywebview after the window loads,
 * so we may need to poll for it briefly.
 */
const getPyWebViewApi = (): any | null => {
    try {
        return (window as any).pywebview?.api ?? null;
    } catch {
        return null;
    }
};

const getModelBridge = (api: any): any | null => {
    return api?.set_model_mode ? api : (api?.transcription?.set_model_mode ? api.transcription : null);
};

export const useAppStore = create<AppState>((set, get) => ({
    stats: null,
    achievements: [],
    snippets: [],
    dictionary: [],
    isReady: false,
    activePage: 'home',
    settings: {
        model: 'turbo',
        vadSensitivity: 65,
        silenceTimeout: 700,
        commandMode: true,
        autoCopy: true,
    },
    modelLoading: null,
    modelLoaded: null,
    modelLoadError: null,
    toast: { message: '', visible: false },

    setActivePage: (page) => set({ activePage: page }),

    updateSettings: (partial) => {
        if (typeof partial.model === 'string') {
            get().setModelMode('turbo');
            return;
        }
        set((state) => ({
            settings: { ...state.settings, ...partial }
        }));

        // Push settings changes to Python backend if bridge is available
        const api = getPyWebViewApi();
        if (api) {
            for (const [key, value] of Object.entries(partial)) {
                try {
                    const modelBridge = getModelBridge(api);
                    if (key === 'model' && typeof value === 'string' && modelBridge) {
                        modelBridge.set_model_mode(value).then((payload: any) => {
                            if (payload?.mode) {
                                set((state) => ({
                                    settings: { ...state.settings, model: payload.mode }
                                }));
                            }
                        }).catch((e: unknown) => {
                            console.warn('Failed to sync model mode:', e);
                        });
                    } else if (api.update_user_setting) {
                        api.update_user_setting(key, value);
                    }
                } catch (e) {
                    console.warn(`Failed to sync setting ${key}:`, e);
                }
            }
        }
    },

    setModelMode: async (_model) => {
        const model = 'turbo';
        set((state) => ({
            settings: { ...state.settings, model },
            modelLoading: model,
            modelLoadError: null,
        }));

        const api = getPyWebViewApi();
        const modelBridge = api ? getModelBridge(api) : null;
        try {
            if (modelBridge?.load_model) {
                const queued = await modelBridge.load_model(model);
                if (queued?.status === 'error') {
                    throw new Error(queued.message || 'Model load failed');
                }
                if (modelBridge.get_loading_status) {
                    for (let i = 0; i < 240; i++) {
                        const status = await modelBridge.get_loading_status();
                        if (!status?.isLoading) break;
                        await new Promise(resolve => setTimeout(resolve, 250));
                    }
                }
                if (modelBridge.get_model_mode) {
                    const payload = await modelBridge.get_model_mode();
                    if (payload?.mode) {
                        set((state) => ({ settings: { ...state.settings, model: payload.mode } }));
                    }
                }
            } else if (modelBridge?.set_model_mode) {
                const payload = await modelBridge.set_model_mode(model);
                if (payload?.mode) {
                    set((state) => ({ settings: { ...state.settings, model: payload.mode } }));
                }
            }
            set({ modelLoaded: 'turbo', modelLoadError: null });
            get().showToast('Turbo model loaded');
        } catch (e) {
            const message = e instanceof Error ? e.message : 'Model load failed';
            set({ modelLoadError: message });
            get().showToast(message);
        } finally {
            set((state) => ({
                modelLoading: state.modelLoading === model ? null : state.modelLoading,
            }));
        }
    },

    showToast: (message) => {
        set({ toast: { message, visible: true } });
        setTimeout(() => {
            set({ toast: { message: '', visible: false } });
        }, 2000);
    },

    /**
     * Copy text to clipboard — uses pywebview bridge when available
     * (navigator.clipboard requires HTTPS or localhost, which pywebview
     * file:// URLs don't satisfy). Falls back to navigator.clipboard
     * for dev/browser mode.
     */
    copyToClipboard: async (text: string): Promise<boolean> => {
        const api = getPyWebViewApi();
        if (api?.copy_text) {
            try {
                const result = await api.copy_text(text);
                return !!result;
            } catch (e) {
                console.warn('Bridge copy_text failed, trying navigator.clipboard', e);
            }
        }
        // Fallback for dev mode / browser
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (e) {
            console.warn('navigator.clipboard failed', e);
            return false;
        }
    },

    loadDevData: () => {
        set({
            isReady: true,
            stats: {
                userName: 'User',
                xp: 2300,
                totalXp: 2300,
                xpToNextLevel: 3500,
                level: 9,
                rank: 'Word Warrior',
                nextRank: 'Voice Virtuoso',
                today: 823,
                thisWeek: 10430,
                thisMonth: 28490,
                avgWpm: 142,
                bestWpm: 187,
                totalWords: 54620,
                totalSessions: 441,
                totalTime: '47h 23m',
                dayStreak: 8,
                weekStreak: 2,
                recentTranscripts: [
                    { text: "Let's make this really interactive and fun...", words: 18, time: '03:33 PM' },
                    { text: 'The achievement system should feel rewarding', words: 12, time: '03:27 PM' },
                    { text: 'Please fix the syntax error for the audio pipeline', words: 10, time: '03:25 PM' }
                ],
                last7Days: [
                    { day: 'Sun', words: 737 },
                    { day: 'Mon', words: 5460 },
                    { day: 'Tue', words: 90 },
                    { day: 'Wed', words: 4177 },
                    { day: 'Thu', words: 12 },
                    { day: 'Fri', words: 1853 },
                    { day: 'Sat', words: 923 }
                ],
                records: {
                    mostWordsDay: { value: 5460, date: '2026-01-12' },
                    fastestWpm: { value: 187, date: '2026-01-16' },
                    longestSession: { value: '2h 14m', date: '2026-01-12' },
                    longestStreak: { value: 14, date: '2026-01-31' }
                }
            },
            achievements: [
                { id: 1, key: 'daily_100', category: 'milestones', name: 'Centurion', description: '100 words in a day', icon: '100', rarity: 'common', xp: 25, unlocked: true },
                { id: 2, key: 'daily_500', category: 'milestones', name: 'Chatterbox', description: '500 words in a day', icon: '500', rarity: 'common', xp: 40, unlocked: true },
                { id: 3, key: 'total_1k', category: 'milestones', name: 'Starter Stack', description: '1,000 total words', icon: '1K', rarity: 'common', xp: 25, unlocked: true },
                { id: 7, key: 'speed_150', category: 'speed', name: 'Speed Demon', description: 'Reach 150 WPM', icon: '150', rarity: 'epic', xp: 200, unlocked: false, progress: 95 }
            ],
            snippets: [
                { id: 1, trigger: 'omw', replacement: 'On my way!' },
                { id: 2, trigger: 'brb', replacement: 'Be right back' },
                { id: 3, trigger: 'sgtm', replacement: 'Sounds good to me' },
            ],
            dictionary: [
                "Whisper", "VRAM", "Tokenization", "Inference"
            ]
        });
    },

    fetchUserData: async () => {
        const api = getPyWebViewApi();
        if (api) {
            try {
                if (api.get_snippets) {
                    const snips = await api.get_snippets();
                    set({ snippets: snips || [] });
                }
                if (api.get_vocabulary) {
                    const vocab = await api.get_vocabulary();
                    set({ dictionary: vocab || [] });
                }
            } catch (e) {
                console.warn('Failed to load user data from bridge', e);
            }
        }
    },

    addSnippet: async (trigger: string, replacement: string) => {
        const api = getPyWebViewApi();
        if (api?.add_snippet) {
            try {
                await api.add_snippet(trigger, replacement);
                await get().fetchUserData();
                get().showToast('Snippet added ✓');
            } catch (e) {
                console.error(e);
            }
        } else {
            // Dev mode fallback
            set(state => ({
                snippets: [{ id: Date.now(), trigger, replacement }, ...state.snippets]
            }));
            get().showToast('Snippet added (Dev) ✓');
        }
    },

    deleteSnippet: async (id: number) => {
        const api = getPyWebViewApi();
        if (api?.delete_snippet) {
            try {
                await api.delete_snippet(id);
                await get().fetchUserData();
                get().showToast('Snippet removed ✓');
            } catch (e) {
                console.error(e);
            }
        } else {
            // Dev mode fallback
            set(state => ({
                snippets: state.snippets.filter(s => s.id !== id)
            }));
            get().showToast('Snippet removed (Dev) ✓');
        }
    },

    addDictionaryWord: async (word: string) => {
        const api = getPyWebViewApi();
        if (api?.add_vocabulary_word) {
            try {
                await api.add_vocabulary_word(word);
                await get().fetchUserData();
                get().showToast('Word added to Dictionary ✓');
            } catch (e) {
                console.error(e);
            }
        } else {
            // Dev mode fallback
            if (!get().dictionary.includes(word)) {
                set(state => ({
                    dictionary: [...state.dictionary, word]
                }));
            }
            get().showToast('Word added (Dev) ✓');
        }
    },

    initBridge: () => {
        /**
         * Initialization strategy:
         * 1. Wait for pywebview.api to become available (up to 3s)
         * 2. Once available, poll get_stats() every second for live data
         * 3. Also pull initial settings from the Python backend
         * 4. If pywebview never appears, fall back to loadDevData()
         */
        let attempts = 0;
        const MAX_WAIT_ATTEMPTS = 30; // 30 × 100ms = 3s

        const startPolling = () => {
            const poll = async () => {
                try {
                    const api = getPyWebViewApi();
                    if (api) {
                        const newStats = await api.get_stats();
                        if (newStats) {
                            // Python API doesn't send userName, inject a default
                            if (!newStats.userName) {
                                newStats.userName = 'User';
                            }
                            set({ stats: newStats, isReady: true });
                        }
                    }
                } catch (e) {
                    console.warn('PyWebView bridge poll error', e);
                }
                setTimeout(poll, 1000);
            };
            poll();
        };

        const loadSettingsFromBridge = async () => {
            try {
                const api = getPyWebViewApi();
                if (api?.get_user_settings) {
                    const result = await api.get_user_settings();
                    const settings = result?.settings || result;
                    if (settings) {
                        set((state) => ({
                            settings: {
                                ...state.settings,
                                commandMode: settings.command_mode ?? settings.commandMode ?? state.settings.commandMode,
                                autoCopy: settings.auto_copy ?? settings.autoCopy ?? state.settings.autoCopy,
                            }
                        }));
                    }
                }
                const modelBridge = getModelBridge(api);
                if (modelBridge?.get_model_mode) {
                    const modelPayload = await modelBridge.get_model_mode();
                    if (modelPayload?.mode) {
                        set((state) => ({
                            settings: { ...state.settings, model: modelPayload.mode }
                        }));
                    }
                }
            } catch (e) {
                console.warn('Failed to load settings from bridge', e);
            }
        };

        const checkReady = () => {
            const api = getPyWebViewApi();
            if (api) {
                console.log('[Impulse] pywebview bridge connected');
                startPolling();
                loadSettingsFromBridge();
                get().fetchUserData();
            } else {
                attempts++;
                if (attempts >= MAX_WAIT_ATTEMPTS) {
                    console.log('[Impulse] No pywebview found, using dev data');
                    get().loadDevData();
                } else {
                    setTimeout(checkReady, 100);
                }
            }
        };

        checkReady();
    }
}));
