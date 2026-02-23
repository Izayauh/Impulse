import React from 'react';
import { cn } from '../lib/utils';

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  hoverable?: boolean;
  key?: React.Key;
}

export const GlassCard = ({ children, className, hoverable = true, ...props }: GlassCardProps) => {
  return (
    <div 
      className={cn(
        "glass-card rounded-3xl p-6",
        hoverable && "hover:border-white/20 hover:shadow-pink-500/5",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};
