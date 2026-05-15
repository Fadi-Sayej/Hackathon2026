import { formatCurrency } from './formatters.js'

/**
 * Inline competitor signal pill rendered next to a product row.
 * Visually subtle — designed to live beside a price without dominating.
 */
export function CompetitorBadge({ competitor }) {
  if (!competitor || competitor.nearbyCompetitors === 0) return null

  if (competitor.isCompetitorOOS) {
    return (
      <span className="competitor-badge competitor-badge-opportunity" title="Nearby competitor is out of stock">
        Competitor OOS
      </span>
    )
  }

  if (competitor.priceProtectionAlert) {
    return (
      <span className="competitor-badge competitor-badge-warning" title="A competitor is >15% cheaper">
        Vs. Market: +{formatCurrency(competitor.priceDelta)}
      </span>
    )
  }

  if (competitor.isPriceLeader && competitor.priceDelta !== null) {
    return (
      <span className="competitor-badge competitor-badge-leader" title="We are the cheapest within 1 km">
        Vs. Market: −{formatCurrency(Math.abs(competitor.priceDelta))}
      </span>
    )
  }

  if (competitor.isPriceSensitive && competitor.priceDelta !== null) {
    return (
      <span className="competitor-badge competitor-badge-sensitive" title="A competitor is cheaper">
        Vs. Market: +{formatCurrency(competitor.priceDelta)}
      </span>
    )
  }

  return null
}
