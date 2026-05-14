/**
 * @typedef {Object} Product
 * @property {string} id
 * @property {string} name
 * @property {string} category
 * @property {number} currentStock
 * @property {number} shelfQuantity
 * @property {number} shelfCapacity
 * @property {number} salesLast7Days
 * @property {number} salesLast30Days
 * @property {number} price
 * @property {number} cost
 * @property {string | undefined} expiryDate
 * @property {string | undefined} supplier
 * @property {number} leadTimeDays
 * @property {number | undefined} returnedUnits
 * @property {number | undefined} damagedUnits
 */

/**
 * @typedef {Object} NormalizationReport
 * @property {string} mode
 * @property {string} sourceLabel
 * @property {string | null} sourcePath
 * @property {number} sourceRowCount
 * @property {number} normalizedProductCount
 * @property {string | null} latestObservedDate
 * @property {string[]} generatedFields
 * @property {string[]} notes
 */

export {}
