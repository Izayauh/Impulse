import { TrendingUp } from 'lucide-react';
import { useAppStore } from '../lib/store';
import { useMemo } from 'react';
import { LineChart, Line, XAxis, Tooltip, ResponsiveContainer } from 'recharts';

export const VelocityCard = () => {
  const stats = useAppStore(state => state.stats);

  const data = useMemo(() => {
    const days = stats?.last7Days || [
      { day: 'Sat', words: 424 },
      { day: 'Sun', words: 300 },
      { day: 'Mon', words: 450 },
      { day: 'Tue', words: 320 },
      { day: 'Wed', words: 350 },
      { day: 'Thu', words: 400 },
      { day: 'Fri', words: 2178 },
    ];
    return days.map(d => ({
      day: d.day,
      value: d.words,
    }));
  }, [stats]);

  return (
    <div className="bg-[#131317]/80 backdrop-blur-md rounded-2xl p-6 border border-white/[0.08] hover:border-white/10 transition-colors shadow-lg grow min-h-[240px]">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h3 className="text-xl font-display font-semibold mb-1">Velocity</h3>
          <p className="text-white/50 text-[15px]">Words transcribed last 7 days</p>
        </div>
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-100/10 text-blue-200">
          <TrendingUp className="w-4 h-4" />
        </div>
      </div>

      <div className="h-44 w-full -ml-4 mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <XAxis 
              dataKey="day" 
              axisLine={false} 
              tickLine={false} 
              tick={{ fill: '#ffffff50', fontSize: 12, fontWeight: 600 }}
              dy={10}
            />
            <Tooltip 
              cursor={{ stroke: '#ec489930', strokeWidth: 2, strokeDasharray: '4 4' }}
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  return (
                    <div className="bg-[#1e1e24] shadow-xl rounded-lg p-3 border border-pink-500/20">
                      <p className="text-white/60 text-xs font-semibold mb-1">{payload[0].payload.day}</p>
                      <p className="text-white text-lg font-bold tabular-nums">
                        {payload[0].value?.toLocaleString()} <span className="text-pink-400 text-sm font-medium">words</span>
                      </p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Line 
              type="monotone" 
              dataKey="value" 
              stroke="#ec4899" 
              strokeWidth={3}
              dot={{ fill: '#0E0E12', stroke: '#ec4899', strokeWidth: 2, r: 4 }}
              activeDot={{ fill: '#2dd4bf', stroke: '#0E0E12', strokeWidth: 3, r: 6 }}
              animationDuration={1500}
              animationEasing="ease-out"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
