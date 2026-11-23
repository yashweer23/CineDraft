import source from '../../config/game-design.json';

export interface PlannedTier {
  id: string;
  name: string;
  totalBudgetUsd: number;
  description: string;
}

export interface PlannedRules {
  rulesVersion: string;
  implementationStatus: string;
  currency: string;
  reservePercent: number;
  offerSize: number;
  offerRerolls: number;
  finalRecasts: number;
  notableWorksPerCard: number;
  uniquePeopleRequired: number;
  slotOrder: string[];
  tiers: PlannedTier[];
}

// This metadata is a design preview, not an authoritative game-rules service.
export const design: PlannedRules = source;
export function allocation(totalBudgetUsd: number) {
  if (!Number.isSafeInteger(totalBudgetUsd) || totalBudgetUsd < 0) {
    throw new Error('Budgets must be non-negative integer USD.');
  }
  const reserveUsd = Math.floor(totalBudgetUsd * design.reservePercent / 100);
  return { reserveUsd, hiringUsd: totalBudgetUsd - reserveUsd };
}
export const money = (usd: number) => new Intl.NumberFormat('en-US', {
  style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 2,
}).format(usd);
