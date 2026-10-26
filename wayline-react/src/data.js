// SAMPLE DATA (prototype only). A real build would load places from a search service.
export const PLACES = [
  { id: 'harbour', name: 'Harbour Station', sub: 'Train station' },
  { id: 'campus', name: 'University Gate', sub: 'Campus entrance' },
  { id: 'market', name: 'Central Market', sub: 'Market' },
  { id: 'northgate', name: 'Northgate Mall', sub: 'Shopping' },
  { id: 'clinic', name: 'Eastfield Clinic', sub: 'Health centre' },
  { id: 'airport', name: 'Airport Road Terminal', sub: 'Bus terminal' },
];

export const DEFAULT_RECENTS = ['harbour', 'campus', 'market'];

// Returns the suggestion rows for what the user has typed so far.
export function buildOptions(query, recentIds) {
  const q = query.trim().toLowerCase();
  if (!q) {
    return recentIds
      .map((id) => PLACES.find((p) => p.id === id))
      .filter(Boolean)
      .map((place) => ({ place, sub: `Recent · ${place.sub}`, recent: true }));
  }
  const hits = PLACES.filter((p) => p.name.toLowerCase().includes(q))
    .slice(0, 5)
    .map((place) => ({ place, sub: place.sub }));
  if (hits.length) return hits;
  return [{ place: { id: 'custom', name: query.trim() }, sub: 'Use what you typed. The map stays illustrative.' }];
}
