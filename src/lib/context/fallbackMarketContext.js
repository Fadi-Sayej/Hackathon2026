import { marketContext } from '../../data/marketContext.js'

export const fallbackMarketContext = {
  ...marketContext,
  contextSource: 'mock',
  sourceLabel: 'mock',
  sourceSummary: 'Static mock context for local-first demo reliability.',
  signalSources: {
    weather: 'mock',
    holiday: 'mock',
    event: 'mock',
  },
}
