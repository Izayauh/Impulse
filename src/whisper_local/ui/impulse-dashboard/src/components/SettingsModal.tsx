import { X, Volume2, Cpu, Database, Key, Layout, Shield, FileKey } from 'lucide-react';
import { useState } from 'react';
import { cn } from '../lib/utils';
import { useAppStore } from '../lib/store';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const tabs = [
  { id: 'general', label: 'General', icon: Layout },
  { id: 'audio', label: 'Audio', icon: Volume2 },
  { id: 'models', label: 'Models', icon: Cpu },
  { id: 'data', label: 'Data', icon: Database },
  { id: 'license', label: 'License', icon: FileKey },
];

export const SettingsModal = ({ isOpen, onClose }: SettingsModalProps) => {
  const settings = useAppStore(state => state.settings);
  const updateSettings = useAppStore(state => state.updateSettings);
  const [localTab, setLocalTab] = useState('general');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />
      
      {/* Modal Content */}
      <div className="relative w-[800px] h-[600px] bg-[#131317]/95 backdrop-blur-2xl border border-white/10 rounded-2xl shadow-2xl flex overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        
        {/* Left Nav */}
        <aside className="w-56 bg-[#0E0E12] border-r border-white/[0.08] flex flex-col p-4 relative z-10">
          <div className="mb-8 px-2 mt-2">
            <h2 className="text-xl font-display font-semibold text-white tracking-wide">Settings</h2>
          </div>
          
          <nav className="flex-1 space-y-1">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setLocalTab(tab.id)}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 text-sm font-medium focus-visible:ring-2 focus-visible:ring-pink-500/50 focus-visible:outline-none",
                  localTab === tab.id
                    ? "bg-pink-500/10 text-pink-300 border border-pink-500/20 shadow-inner"
                    : "text-white/50 hover:text-white hover:bg-white/5 border border-transparent"
                )}
              >
                <tab.icon className={cn("w-4 h-4", localTab === tab.id ? "text-pink-400" : "opacity-70")} />
                {tab.label}
              </button>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <div className="flex-1 flex flex-col relative z-20">
          <div className="absolute top-4 right-4 z-30">
            <button 
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/10 text-white/50 hover:text-white transition-colors focus-visible:ring-2 focus-visible:ring-pink-500/50 focus-visible:outline-none"
              aria-label="Close settings"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-10 custom-scrollbar">
            {localTab === 'general' && (
              <div className="space-y-8 animate-in fade-in slide-in-from-right-4 duration-300">
                <div>
                  <h3 className="text-2xl font-display font-semibold mb-6">General Settings</h3>
                  
                  <div className="space-y-6">
                    <div className="flex items-center justify-between p-4 rounded-xl border border-white/[0.08] bg-white/[0.02]">
                      <div>
                        <h4 className="font-medium text-white">Record Shortcut</h4>
                        <p className="text-sm text-white/50 mt-1">Press and hold this combo to start dictation.</p>
                      </div>
                      <button className="px-4 py-2 rounded-lg bg-pink-500/20 text-pink-300 border border-pink-500/30 hover:bg-pink-500/30 transition-colors font-medium text-sm focus-visible:ring-2 focus-visible:ring-pink-500/50 focus-visible:outline-none">
                        Ctrl + Space
                      </button>
                    </div>

                    <div className="flex items-center justify-between p-4 rounded-xl border border-white/[0.08] bg-white/[0.02]">
                      <div>
                        <h4 className="font-medium text-white">Command Mode</h4>
                        <p className="text-sm text-white/50 mt-1">Edit and interact with voice commands.</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          className="sr-only peer"
                          checked={settings.commandMode}
                          onChange={(e) => updateSettings({ commandMode: e.target.checked })}
                          id="commandMode"
                        />
                        <div className="w-11 h-6 bg-white/10 peer-focus-visible:ring-2 peer-focus-visible:ring-pink-500/50 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-pink-500"></div>
                      </label>
                    </div>

                    <div className="flex items-center justify-between p-4 rounded-xl border border-white/[0.08] bg-white/[0.02]">
                      <div>
                        <h4 className="font-medium text-white">Auto-copy Transcript</h4>
                        <p className="text-sm text-white/50 mt-1">Copy latest output automatically to your clipboard.</p>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          className="sr-only peer"
                          checked={settings.autoCopy}
                          onChange={(e) => updateSettings({ autoCopy: e.target.checked })}
                          id="autoCopy"
                        />
                        <div className="w-11 h-6 bg-white/10 peer-focus-visible:ring-2 peer-focus-visible:ring-pink-500/50 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-pink-500"></div>
                      </label>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {localTab === 'audio' && (
              <div className="space-y-8 animate-in fade-in slide-in-from-right-4 duration-300">
                <h3 className="text-2xl font-display font-semibold mb-6">Audio Input</h3>
                <div className="space-y-6">
                  <div className="p-4 rounded-xl border border-white/[0.08] bg-white/[0.02]">
                    <h4 className="font-medium text-white mb-4">VAD Sensitivity</h4>
                    <input
                      type="range"
                      min="1"
                      max="100"
                      value={settings.vadSensitivity}
                      onChange={(e) => updateSettings({ vadSensitivity: Number(e.target.value) })}
                      className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-pink-500"
                    />
                    <div className="flex justify-between text-xs text-white/50 mt-2">
                       <span>Low</span>
                       <span className="tabular-nums">Current: {settings.vadSensitivity}%</span>
                       <span>High</span>
                    </div>
                  </div>
                  
                  <div className="p-4 rounded-xl border border-white/[0.08] bg-white/[0.08]">
                    <h4 className="font-medium text-white mb-4">Silence Timeout</h4>
                    <input
                      type="range"
                      min="250"
                      max="2000"
                      step="50"
                      value={settings.silenceTimeout}
                      onChange={(e) => updateSettings({ silenceTimeout: Number(e.target.value) })}
                      className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-pink-500"
                    />
                    <div className="flex justify-between text-xs text-white/50 mt-2">
                       <span>250ms</span>
                       <span className="tabular-nums">Current: {settings.silenceTimeout}ms</span>
                       <span>2000ms</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            {localTab === 'models' && (
              <div className="space-y-8 animate-in fade-in slide-in-from-right-4 duration-300">
                <h3 className="text-2xl font-display font-semibold mb-6">Transcription Models</h3>
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { id: 'auto', title: 'Auto', desc: 'VRAM-aware selection' },
                    { id: 'base', title: 'Base', desc: 'Fastest turnaround.' },
                    { id: 'small', title: 'Small', desc: 'Higher accuracy.' },
                    { id: 'medium', title: 'Medium', desc: 'Best for complex dictations.' }
                  ].map(model => (
                    <button
                      key={model.id}
                      onClick={() => updateSettings({ model: model.id })}
                      className={cn(
                        "p-5 rounded-xl border cursor-pointer transition-all text-left focus-visible:ring-2 focus-visible:ring-pink-500/50 focus-visible:outline-none",
                        settings.model === model.id
                          ? "bg-pink-500/10 border-pink-500/30 shadow-[0_0_15px_rgba(236,72,153,0.15)]"
                          : "bg-white/[0.02] border-white/[0.08] hover:border-white/20"
                      )}
                    >
                      <h4 className="font-bold mb-1 text-white">{model.title}</h4>
                      <p className="text-sm text-white/50">{model.desc}</p>
                    </button>
                  ))}
                </div>
              </div>
            )}
            
            {localTab === 'data' && (
              <div className="space-y-8 animate-in fade-in slide-in-from-right-4 duration-300">
                <h3 className="text-2xl font-display font-semibold mb-6">Data & Privacy</h3>
                <div className="space-y-6">
                  <div className="p-5 rounded-xl border border-white/[0.08] bg-white/[0.02]">
                    <div className="flex items-center gap-3 mb-3">
                      <Shield className="w-5 h-5 text-emerald-400" />
                      <h4 className="font-medium text-white">Local Processing</h4>
                    </div>
                    <p className="text-sm text-white/50 leading-relaxed">
                      All voice data is processed locally on your machine. No audio is ever sent to external servers. Your transcriptions stay private.
                    </p>
                  </div>

                  <div className="p-5 rounded-xl border border-white/[0.08] bg-white/[0.02]">
                    <h4 className="font-medium text-white mb-3">Export Statistics</h4>
                    <p className="text-sm text-white/50 mb-4">Download your transcription history and statistics as a JSON file.</p>
                    <button className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-white/70 text-sm font-medium hover:bg-white/10 hover:text-white transition-all focus-visible:ring-2 focus-visible:ring-pink-500/50 focus-visible:outline-none">
                      Export Data
                    </button>
                  </div>

                  <div className="p-5 rounded-xl border border-red-500/10 bg-red-500/[0.02]">
                    <h4 className="font-medium text-red-300 mb-3">Reset All Data</h4>
                    <p className="text-sm text-white/50 mb-4">This will clear all transcription history, statistics, achievements, and reset your level to 1.</p>
                    <button className="px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm font-medium hover:bg-red-500/20 transition-all focus-visible:ring-2 focus-visible:ring-red-500/50 focus-visible:outline-none">
                      Reset Everything
                    </button>
                  </div>
                </div>
              </div>
            )}

            {localTab === 'license' && (
              <div className="space-y-8 animate-in fade-in slide-in-from-right-4 duration-300">
                <h3 className="text-2xl font-display font-semibold mb-6">License</h3>
                <div className="space-y-6">
                  <div className="p-5 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.03]">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <FileKey className="w-5 h-5 text-emerald-400" />
                        <h4 className="font-medium text-white">License Status</h4>
                      </div>
                      <span className="px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold border border-emerald-500/30">
                        ACTIVE
                      </span>
                    </div>
                    <p className="text-sm text-white/50">Your Impulse license is active and valid.</p>
                  </div>

                  <div className="p-5 rounded-xl border border-white/[0.08] bg-white/[0.02]">
                    <h4 className="font-medium text-white mb-3">License Key</h4>
                    <div className="flex items-center gap-3">
                      <code className="flex-1 px-4 py-2.5 rounded-lg bg-black/30 border border-white/5 text-white/60 text-sm font-mono tracking-wider">
                        IMPL-XXXX-XXXX-XXXX
                      </code>
                      <button className="px-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white/60 text-sm hover:bg-white/10 hover:text-white transition-all focus-visible:ring-2 focus-visible:ring-pink-500/50 focus-visible:outline-none">
                        Change
                      </button>
                    </div>
                  </div>

                  <div className="p-5 rounded-xl border border-white/[0.08] bg-white/[0.02]">
                    <h4 className="font-medium text-white mb-2">About Impulse</h4>
                    <p className="text-sm text-white/50">Version 1.0.0-beta · Built with Whisper AI</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};


