// ── Date utility helpers ───────────────────────────────────────────────────

/**
 * Returns a human-readable "X ago" string for a given date.
 * Intentionally minimal — no external dependency needed.
 */
export function formatDistanceToNow(date: Date): string {
  const diffMs  = Date.now() - date.getTime();
  const diffSec = Math.round(diffMs / 1000);

  if (diffSec < 10)  return 'just now';
  if (diffSec < 60)  return `${diffSec}s ago`;
  if (diffSec < 3600) {
    const m = Math.floor(diffSec / 60);
    return `${m} min${m === 1 ? '' : 's'} ago`;
  }
  const h = Math.floor(diffSec / 3600);
  return `${h} hr${h === 1 ? '' : 's'} ago`;
}
