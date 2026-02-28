import { create } from 'zustand';

// Type definitions based on dashboard.html
export interface AppStats {
    userName: string;
    xp: number;
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
    recentTranscripts: Array<{ text: string; words: number; time: string }>;
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

interface AppState {
    stats: AppStats | null;
    achievements: Achievement[];
    isReady: boolean;
    initBridge: () => void;
    // Fallback dev stats if not in pywebview
    loadDevData: () => void;
}

export const useAppStore = create<AppState>((set) => ({
    stats: null,
    achievements: [],
    isReady: false,

    loadDevData: () => {
        set({
            isReady: true,
            stats: {
                userName: 'User',
                xp: 2300,
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
            ]
        });
    },

    initBridge: () => {
        // If pywebview is not defined, load dev data for the frontend designer
        if (typeof (window as any).pywebview === 'undefined') {
            console.log('No pywebview found, falling back to dev data');
            useAppStore.getState().loadDevData();
            return;
        }

        // Otherwise, poll stats and achievements
        const poll = async () => {
            try {
                const api = (window as any).pywebview.api;
                if (api) {
                    const newStats = await api.get_stats();
                    // Merge stats totals and chart data appropriately in a real implementation
                    // For now, assume get_stats returns the full struct if available
                    if (newStats) set({ stats: newStats, isReady: true });
                }
            } catch (e) {
                console.warn('PyWebView bridge error', e);
            }
            setTimeout(poll, 1000);
        };

        // Wait for pywebview to be ready
        const checkReady = () => {
            if ((window as any).pywebview) {
                poll();
            } else {
                setTimeout(checkReady, 100);
            }
        };
        checkReady();
    }
}));
