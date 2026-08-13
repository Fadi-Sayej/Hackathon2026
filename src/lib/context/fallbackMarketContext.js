import { marketContext } from '../../data/marketContext.js'

export const fallbackMarketContext = {
  ...marketContext,
  contextSource: 'mock',
  sourceLabel: 'mock',
  // Rendered through `t('mc.contextNote')` when absent; this English string is
  // the last-resort value and is never shown while the panel has a translation.
  sourceSummary: null,
  signalSources: {
    weather: 'mock',
    holiday: 'mock',
    event: 'mock',
  },
}
