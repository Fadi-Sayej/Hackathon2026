import { createComaxConnectorStub } from './comaxConnectorStub.js'
import { createCsvConnector } from './csvConnector.js'
import { createDemoDataConnector } from './demoDataConnector.js'
import { CONNECTOR_MODES, EXPECTED_POS_FIELDS } from './posConnectorInterface.js'

export { CONNECTOR_MODES, EXPECTED_POS_FIELDS }
export { createDemoDataConnector } from './demoDataConnector.js'
export { createCsvConnector, parseCsv } from './csvConnector.js'
export { createComaxConnectorStub } from './comaxConnectorStub.js'

export function createConnector(mode, options = {}) {
  switch (mode) {
    case CONNECTOR_MODES.DEMO:
      return createDemoDataConnector(options)
    case CONNECTOR_MODES.CSV:
      return createCsvConnector(options)
    case CONNECTOR_MODES.COMAX:
      return createComaxConnectorStub()
    default:
      return createDemoDataConnector(options)
  }
}

export const CONNECTOR_CATALOG = [
  {
    mode: CONNECTOR_MODES.DEMO,
    label: 'Demo Dataset',
    description: 'Bundled sample SKUs — always available offline.',
    available: true,
  },
  {
    mode: CONNECTOR_MODES.CSV,
    label: 'Upload CSV',
    description: 'Parse a local POS export. Runs through the standard adapter.',
    available: true,
  },
  {
    mode: CONNECTOR_MODES.COMAX,
    label: 'Comax POS Connector',
    description: 'Live POS sync — requires a backend proxy. Disabled in this build.',
    available: false,
  },
]
