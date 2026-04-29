import { useEffect, useRef, useState } from 'react';

const colorMap = {
  blue: {
    card: 'from-blue-500/10 via-blue-600/5 to-transparent border-blue-500/15 hover:border-blue-500/30',
    icon: 'bg-blue-500/15 text-blue-400 shadow-blue-500/10',
    value: 'from-blue-400 to-blue-300',
    glow: 'hover:shadow-blue-500/10',
    dot: 'bg-blue-400',
  },
  green: {
    card: 'from-emerald-500/10 via-emerald-600/5 to-transparent border-emerald-500/15 hover:border-emerald-500/30',
    icon: 'bg-emerald-500/15 text-emerald-400 shadow-emerald-500/10',
    value: 'from-emerald-400 to-emerald-300',
    glow: 'hover:shadow-emerald-500/10',
    dot: 'bg-emerald-400',
  },
  purple: {
    card: 'from-purple-500/10 via-purple-600/5 to-transparent border-purple-500/15 hover:border-purple-500/30',
    icon: 'bg-purple-500/15 text-purple-400 shadow-purple-500/10',
    value: 'from-purple-400 to-purple-300',
    glow: 'hover:shadow-purple-500/10',
    dot: 'bg-purple-400',
  },
  orange: {
    card: 'from-orange-500/10 via-orange-600/5 to-transparent border-orange-500/15 hover:border-orange-500/30',
    icon: 'bg-orange-500/15 text-orange-400 shadow-orange-500/10',
    value: 'from-orange-400 to-orange-300',
    glow: 'hover:shadow-orange-500/10',
    dot: 'bg-orange-400',
  },
  red: {
    card: 'from-red-500/10 via-red-600/5 to-transparent border-red-500/15 hover:border-red-500/30',
    icon: 'bg-red-500/15 text-red-400 shadow-red-500/10',
    value: 'from-red-400 to-red-300',
    glow: 'hover:shadow-red-500/10',
    dot: 'bg-red-400',
  },
  cyan: {
    card: 'from-cyan-500/10 via-cyan-600/5 to-transparent border-cyan-500/15 hover:border-cyan-500/30',
    icon: 'bg-cyan-500/15 text-cyan-400 shadow-cyan-500/10',
    value: 'from-cyan-400 to-cyan-300',
    glow: 'hover:shadow-cyan-500/10',
    dot: 'bg-cyan-400',
  },
};

function AnimatedNumber({ value }) {
  const [display, setDisplay] = useState(0);
  const ref = useRef(null);

  useEffect(() => {
    const num = typeof value === 'number' ? value : parseInt(String(value).replace(/[^0-9]/g, ''), 10);
    if (isNaN(num) || num === 0) { setDisplay(num || 0); return; }

    let start = 0;
    const duration = 1200;
    const startTime = performance.now();

    function step(now) {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = Math.floor(eased * num);
      setDisplay(current);
      if (progress < 1) ref.current = requestAnimationFrame(step);
    }
    ref.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(ref.current);
  }, [value]);

  // If value is string with prefix (like "Rs. 1234"), keep prefix
  if (typeof value === 'string') {
    const match = value.match(/^([^0-9]*)([\d,]+)(.*)$/);
    if (match) {
      return <>{match[1]}{typeof display === 'number' ? display.toLocaleString() : display}{match[3]}</>;
    }
  }
  return <>{typeof display === 'number' ? display.toLocaleString() : display}</>;
}

export default function StatCard({ icon: Icon, label, value, color = 'blue', subtitle }) {
  const c = colorMap[color] || colorMap.blue;

  let displayedValue = value;
  if (label === 'Revenue' && typeof value === 'number') {
    displayedValue = `Rs. ${value.toLocaleString()}`;
  } else if (typeof value === 'number') {
    displayedValue = value.toLocaleString();
  }

  return (
    <div className={`animate-fade-in-up group relative bg-gradient-to-br ${c.card} border rounded-2xl p-5 transition-all duration-500 hover:translate-y-[-3px] hover:shadow-2xl ${c.glow} overflow-hidden`}>
      {/* Shimmer overlay */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-700 animate-shimmer pointer-events-none" />

      <div className="relative flex flex-col items-center">
        <div className="space-y-2 text-center">
          <div className="flex items-center gap-2">
            <div className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
            <p className="text-slate-400 text-xs font-semibold tracking-wide uppercase">{label}</p>
          </div>
          <p className={`text-3xl font-extrabold bg-gradient-to-r ${c.value} bg-clip-text text-transparent`}>
            <AnimatedNumber value={displayedValue} />
          </p>
          {subtitle && (
            <p className="text-slate-500 text-[11px] font-medium">{subtitle}</p>
          )}
        </div>
        <div className={`w-12 h-12 rounded-2xl ${c.icon} shadow-lg flex items-center justify-center transition-transform duration-500 group-hover:scale-110 group-hover:rotate-3`}>
          <Icon size={22} strokeWidth={1.8} />
        </div>
      </div>
    </div>
  );
}
