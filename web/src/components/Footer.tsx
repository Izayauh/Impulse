import { Brain, Download, Github, ShieldCheck } from 'lucide-react';
import { CHANGELOG_URL, GITHUB_REPO_URL, PRIVACY_URL, RELEASE_PAGE_URL } from '@/src/lib/site';

export function Footer() {
  return (
    <footer className="py-20 px-6 border-t border-white/5">
      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-12">
        <div className="col-span-1 md:col-span-2">
          <div className="flex items-center gap-2 mb-6">
            <div className="w-8 h-8 bg-brand rounded-lg flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <span className="font-display font-bold text-xl tracking-tight">Impulse</span>
          </div>
          <p className="text-white/40 max-w-sm mb-8 leading-relaxed">
            Dictation that runs entirely on your computer.
            Hold a key, talk, and it types. Pay once, keep it.
          </p>
          <div className="flex gap-4">
            <a href={GITHUB_REPO_URL} target="_blank" rel="noreferrer" aria-label="GitHub repository" className="text-white/40 hover:text-brand transition-colors"><Github className="w-5 h-5" /></a>
            <a href={RELEASE_PAGE_URL} target="_blank" rel="noreferrer" aria-label="Download Impulse beta" className="text-white/40 hover:text-brand transition-colors"><Download className="w-5 h-5" /></a>
            <a href={PRIVACY_URL} target="_blank" rel="noreferrer" aria-label="Privacy policy" className="text-white/40 hover:text-brand transition-colors"><ShieldCheck className="w-5 h-5" /></a>
          </div>
        </div>
        
        <div>
          <h4 className="font-bold mb-6 uppercase tracking-widest text-xs text-white/40">Product</h4>
          <ul className="space-y-4 text-sm text-white/60">
            <li><a href={RELEASE_PAGE_URL} target="_blank" rel="noreferrer" className="hover:text-brand transition-colors">Download</a></li>
            <li><a href="#features" className="hover:text-brand transition-colors">Features</a></li>
            <li><a href="#beta" className="hover:text-brand transition-colors">Beta</a></li>
            <li><a href={CHANGELOG_URL} target="_blank" rel="noreferrer" className="hover:text-brand transition-colors">Changelog</a></li>
          </ul>
        </div>

        <div>
          <h4 className="font-bold mb-6 uppercase tracking-widest text-xs text-white/40">Company</h4>
          <ul className="space-y-4 text-sm text-white/60">
            <li><a href={GITHUB_REPO_URL} target="_blank" rel="noreferrer" className="hover:text-brand transition-colors">GitHub</a></li>
            <li><a href={PRIVACY_URL} target="_blank" rel="noreferrer" className="hover:text-brand transition-colors">Privacy</a></li>
            <li><a href="mailto:beta@impulsedictation.com" className="hover:text-brand transition-colors">Contact</a></li>
          </ul>
        </div>
      </div>
      
      <div className="max-w-7xl mx-auto mt-20 pt-8 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-white/20 font-medium uppercase tracking-widest">
        <span>© 2026 Isaiah Washington. All rights reserved.</span>
        <span>Designed, built, and shipped by one person.</span>
      </div>
    </footer>
  );
}
