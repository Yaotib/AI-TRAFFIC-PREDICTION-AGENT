// ── TrafficBadge — small colored pill for traffic level ───────────────────
import type { TrafficLevel } from '../lib/types';

const CONFIG: Record<TrafficLevel, { label: string; className: string }> = {
  light:    { label: 'Light traffic',    className: 'bg-emerald-100 text-emerald-700' },
  moderate: { label: 'Moderate traffic', className: 'bg-amber-100 text-amber-700'    },
  heavy:    { label: 'Heavy traffic',    className: 'bg-red-100 text-red-700'        },
};

interface TrafficBadgeProps {
  level: TrafficLevel;
  className?: string;
}

export function TrafficBadge({ level, className = '' }: TrafficBadgeProps) {
  const { label, className: base } = CONFIG[level];
  return (
    <span
      className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded-full ${base} ${className}`}
    >
      {label}
    </span>
  );
}
