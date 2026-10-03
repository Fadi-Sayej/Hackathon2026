/**
 * store_settings.mjs — the web side's reader of configs/store.yaml (ADR-036).
 *
 * src/common/store.py validates the whole file for the engine. The build and the Firebase
 * check need two values from it, and read them here with the same rule: nothing defaults,
 * and a missing key stops with the key's name.
 *
 * The web build takes only the tab title. The store id stays the deployment's own
 * VITE_STORE_ID: Preview's is `preview-sandbox` on purpose (docs/operations/deployment.md),
 * so a preview of any branch can never write the owner's state. `npm run check:firebase`
 * compares Production's id with this file's.
 */
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { parse } from 'yaml'

export const STORE_SETTINGS_PATH = fileURLToPath(new URL('../configs/store.yaml', import.meta.url))

function text(raw, dotted, path) {
  const value = dotted.split('.').reduce((node, part) => node?.[part], raw)
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(`${path}: \`${dotted}\` is missing. Every store setting is required (ADR-036); none is defaulted.`)
  }
  return value.trim()
}

export function readStoreSettings(path = STORE_SETTINGS_PATH) {
  let raw
  try {
    raw = parse(readFileSync(path, 'utf8'))
  } catch (error) {
    if (error.code === 'ENOENT') {
      throw new Error(`${path} does not exist. It states which store this copy serves (ADR-036).`)
    }
    throw error
  }
  return {
    id: text(raw, 'id', path),
    siteTitle: text(raw, 'site_title', path),
    firebaseProjectId: text(raw, 'firebase.project_id', path),
    siteAddress: text(raw, 'site.address', path),
  }
}

const escapeHtml = (value) => value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

/** A Vite plugin: index.html's `%SITE_TITLE%` becomes the store's tab title. */
export function siteTitlePlugin(path = STORE_SETTINGS_PATH) {
  return {
    name: 'smartshelf-site-title',
    transformIndexHtml(html) {
      return html.replaceAll('%SITE_TITLE%', escapeHtml(readStoreSettings(path).siteTitle))
    },
  }
}
