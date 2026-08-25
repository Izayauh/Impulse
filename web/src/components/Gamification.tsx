import { motion } from 'motion/react';
import { Flame, Trophy, Star, Zap } from 'lucide-react';

export function Gamification() {
  return (
    <section id="gamification" className="py-32 px-6 bg-surface-muted/50">
      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">
        <div>
          <h2 className="font-display text-4xl md:text-6xl font-bold mb-8 leading-tight">
            The fun part is <br />
            <span className="text-brand">completely unnecessary.</span>
          </h2>
          <p className="text-white/60 text-lg mb-10 leading-relaxed">
            Impulse counts every word you speak and turns it into streaks,
            daily records, and achievements. It has no practical purpose.
            It just makes you want to dictate again tomorrow, which turns
            out to be the whole game.
          </p>
          
          <div className="space-y-6">
            {[
              { icon: Flame, text: "14 Day Dictation Streak", color: "text-orange-500" },
              { icon: Trophy, text: "Personal Best: 5,460 Words in a Day", color: "text-yellow-500" },
              { icon: Star, text: "14 Achievements to Find", color: "text-brand" },
            ].map((item, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="flex items-center gap-4 glass rounded-2xl p-4 border-white/5"
              >
                <div className={`w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center ${item.color}`}>
                  <item.icon className="w-5 h-5" />
                </div>
                <span className="font-semibold">{item.text}</span>
              </motion.div>
            ))}
          </div>
        </div>

        <div className="relative">
          <div className="glass rounded-[40px] p-8 aspect-square flex flex-col items-center justify-center text-center relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-brand/10 to-blue-500/10 -z-10" />
            
            <motion.div
              animate={{ 
                scale: [1, 1.05, 1],
                rotate: [0, 5, -5, 0]
              }}
              transition={{ duration: 4, repeat: Infinity }}
              className="w-48 h-48 rounded-full border-4 border-brand/20 flex items-center justify-center mb-8 relative"
            >
              <div className="absolute inset-0 border-4 border-brand rounded-full border-t-transparent animate-spin" style={{ animationDuration: '3s' }} />
              <div className="text-center">
                <span className="block text-5xl font-display font-bold">842</span>
                <span className="text-white/40 uppercase tracking-widest text-xs font-bold">Words Today</span>
              </div>
            </motion.div>

            <h3 className="text-2xl font-bold mb-2">Level 24 Achieved</h3>
            <p className="text-white/60 mb-8">1,864 words spoken today.</p>
            
            <div className="w-full bg-white/5 rounded-full h-3 overflow-hidden mb-4">
              <motion.div 
                initial={{ width: 0 }}
                whileInView={{ width: "75%" }}
                viewport={{ once: true }}
                className="h-full bg-brand glow-pink" 
              />
            </div>
            <div className="flex justify-between w-full text-xs font-bold text-white/40 uppercase tracking-wider">
              <span>Level 24</span>
              <span>250 XP to Level 25</span>
            </div>
          </div>
          
          {/* Floating Badges */}
          <motion.div
            animate={{ y: [0, -10, 0] }}
            transition={{ duration: 3, repeat: Infinity }}
            className="absolute -top-6 -right-6 glass p-4 rounded-2xl shadow-2xl border-white/10"
          >
            <Zap className="w-6 h-6 text-brand" />
          </motion.div>
          
          <motion.div
            animate={{ y: [0, 10, 0] }}
            transition={{ duration: 4, repeat: Infinity, delay: 0.5 }}
            className="absolute -bottom-6 -left-6 glass p-4 rounded-2xl shadow-2xl border-white/10"
          >
            <Star className="w-6 h-6 text-yellow-500" />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
