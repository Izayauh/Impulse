import { Brain, Twitter, Github, Linkedin } from 'lucide-react';

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
            The premium dictation layer for modern professionals. 
            Built for speed, privacy, and the flow state.
          </p>
          <div className="flex gap-4">
            <a href="#" className="text-white/40 hover:text-brand transition-colors"><Twitter className="w-5 h-5" /></a>
            <a href="#" className="text-white/40 hover:text-brand transition-colors"><Github className="w-5 h-5" /></a>
            <a href="#" className="text-white/40 hover:text-brand transition-colors"><Linkedin className="w-5 h-5" /></a>
          </div>
        </div>
        
        <div>
          <h4 className="font-bold mb-6 uppercase tracking-widest text-xs text-white/40">Product</h4>
          <ul className="space-y-4 text-sm text-white/60">
            <li><a href="#" className="hover:text-brand transition-colors">Download</a></li>
            <li><a href="#" className="hover:text-brand transition-colors">Features</a></li>
            <li><a href="#" className="hover:text-brand transition-colors">Pricing</a></li>
            <li><a href="#" className="hover:text-brand transition-colors">Changelog</a></li>
          </ul>
        </div>

        <div>
          <h4 className="font-bold mb-6 uppercase tracking-widest text-xs text-white/40">Company</h4>
          <ul className="space-y-4 text-sm text-white/60">
            <li><a href="#" className="hover:text-brand transition-colors">About</a></li>
            <li><a href="#" className="hover:text-brand transition-colors">Privacy</a></li>
            <li><a href="#" className="hover:text-brand transition-colors">Terms</a></li>
            <li><a href="#" className="hover:text-brand transition-colors">Contact</a></li>
          </ul>
        </div>
      </div>
      
      <div className="max-w-7xl mx-auto mt-20 pt-8 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-white/20 font-medium uppercase tracking-widest">
        <span>© 2024 Impulse AI Inc. All rights reserved.</span>
        <span>Designed with passion for the creative mind.</span>
      </div>
    </footer>
  );
}
