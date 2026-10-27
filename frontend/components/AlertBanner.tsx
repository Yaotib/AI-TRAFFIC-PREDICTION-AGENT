// ── AlertBanner — traffic alert card ──────────────────────────────────────
import { AlertTriangle, Info, AlertOctagon } from 'lucide-react';
import { useRouteStore } from '../lib/store';
import type { TrafficAlert } from '../lib/types';

const SEVERITY_CONFIG = {
  info:     { Icon: Info,         bg: 'bg-blue-50',   border: 'border-blue-200',   text: 'text-blue-700',   icon: 'text-blue-500'   },
  warning:  { Icon: AlertTriangle, bg: 'bg-amber-50',  border: 'border-amber-200',  text: 'text-amber-800',  icon: 'text-amber-500'  },
  critical: { Icon: AlertOctagon,  bg: 'bg-red-50',    border: 'border-red-200',    text: 'text-red-800',    icon: 'text-red-500'    },
};

function AlertCard({ alert }: { alert: TrafficAlert }) {
  const { Icon, bg, border, text, icon } = SEVERITY_CONFIG[alert.severity];
  return (
    <div
      id={`alert-${alert.id}`}
      className={`rounded-xl border p-3 flex gap-3 ${bg} ${border} animate-slide-up`}
    >
      <Icon size={16} className={`flex-none mt-0.5 ${icon}`} />
      <div>
        <p className={`text-xs font-bold ${text}`}>{alert.title}</p>
        <p className={`text-xs mt-0.5 ${text} opacity-80`}>{alert.body}</p>
      </div>
    </div>
  );
}

export function AlertBanner() {
  const alerts = useRouteStore((s) => s.alerts);
  if (!alerts.length) return null;

  return (
    <div className="px-3 mb-3 flex flex-col gap-2">
      {alerts.map((a) => (
        <AlertCard key={a.id} alert={a} />
      ))}
    </div>
  );
}
