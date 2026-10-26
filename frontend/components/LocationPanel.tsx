// ── LocationPanel — origin/destination input panel ─────────────────────────
import { Pencil, ArrowUpDown } from 'lucide-react';
import { useRouteStore } from '../lib/store';

export function LocationPanel() {
  const origin      = useRouteStore((s) => s.origin);
  const destination = useRouteStore((s) => s.destination);
  const setOrigin   = useRouteStore((s) => s.setOrigin);
  const setDest     = useRouteStore((s) => s.setDestination);

  return (
    <div className="px-4 pt-4 pb-3">
      {/* Origin row */}
      <div className="flex items-center gap-3 group">
        <div className="flex-none w-5 flex items-center justify-center">
          <div className="w-3 h-3 rounded-full border-2 border-gray-800 bg-white" />
        </div>
        <div className="flex-1 min-w-0">
          <input
            id="origin-input"
            type="text"
            value={origin}
            onChange={(e) => setOrigin(e.target.value)}
            className="w-full text-sm font-medium text-gray-800 bg-transparent outline-none placeholder:text-gray-400 truncate"
            placeholder="Your current location"
          />
        </div>
        <button
          aria-label="Edit origin"
          className="flex-none opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-gray-600"
        >
          <Pencil size={14} />
        </button>
      </div>

      {/* Connector line + swap */}
      <div className="flex items-center gap-3 my-1">
        <div className="flex-none w-5 flex items-center justify-center">
          <div className="w-px h-7 bg-gray-200" />
        </div>
        <div className="flex-1" />
        <button
          aria-label="Swap origin and destination"
          onClick={() => {
            setOrigin(destination);
            setDest(origin);
          }}
          className="flex-none text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full p-1 transition-colors"
        >
          <ArrowUpDown size={14} />
        </button>
      </div>

      {/* Destination row */}
      <div className="flex items-center gap-3 group">
        <div className="flex-none w-5 flex items-center justify-center">
          <div className="w-3 h-3 rounded-md bg-gray-800" />
        </div>
        <div className="flex-1 min-w-0">
          <input
            id="destination-input"
            type="text"
            value={destination}
            onChange={(e) => setDest(e.target.value)}
            className="w-full text-sm font-medium text-gray-800 bg-transparent outline-none placeholder:text-gray-400 truncate"
            placeholder="Destination"
          />
        </div>
        <button
          aria-label="Edit destination"
          className="flex-none opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-gray-600"
        >
          <Pencil size={14} />
        </button>
      </div>
    </div>
  );
}
