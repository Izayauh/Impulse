import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { GlassCard } from './GlassCard';
import { useAppStore } from '../lib/store';

export const ProgressChart = () => {
  const rawData = useAppStore(state => state.stats?.last7Days || []);
  const data = rawData.length ? rawData.map(d => ({ name: d.day, points: d.words })) : [
    { name: 'Mon', points: 0 },
    { name: 'Tue', points: 0 },
    { name: 'Wed', points: 0 },
    { name: 'Thu', points: 0 },
    { name: 'Fri', points: 0 },
    { name: 'Sat', points: 0 },
    { name: 'Sun', points: 0 },
  ];

  return (
    <GlassCard className="flex-[2] h-[350px] flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-lg font-display font-bold">Weekly Progress</h3>
          <p className="text-sm text-white/50">Words spoken this week</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-pink-500" />
          <span className="text-xs font-medium text-white/70">Words</span>
        </div>
      </div>

      <div className="flex-1 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="colorPoints" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ec4899" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#ec4899" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorPointsArea" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#ec4899" />
                <stop offset="50%" stopColor="#f43f5e" />
                <stop offset="100%" stopColor="#f97316" />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="name"
              axisLine={false}
              tickLine={false}
              tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 12 }}
              dy={10}
            />
            <YAxis hide />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(20,20,25,0.9)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '12px',
                color: '#fff'
              }}
              itemStyle={{ color: '#ec4899' }}
            />
            <Area
              type="monotone"
              dataKey="points"
              stroke="url(#colorPointsArea)"
              strokeWidth={4}
              fillOpacity={1}
              fill="url(#colorPoints)"
              activeDot={{ r: 8, fill: '#f9a8d4', stroke: '#be185d', strokeWidth: 3 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </GlassCard>
  );
};
