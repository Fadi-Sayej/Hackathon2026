/**
 * ADR-036 §2: the web build reads the store's settings from configs/store.yaml, the same
 * file the engine reads, and defaults nothing.
 *
 * The build takes only the tab title from it. The store id stays the deployment's own
 * VITE_STORE_ID, because Preview's is `preview-sandbox` on purpose (deployment.md): a preview
 * of any branch must never write the owner's state. check:firebase compares Production's
 * with the settings instead.
 */
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { readStoreSettings, siteTitlePlugin } from '../store_settings.mjs'

const VALID = [
  'id: store-a',
  'name: Store A',
  'site_title: "SmartShelf AI — Store A"',
  'location: {lat: 32.1, lon: 34.9}',
  'format: urban_minimarket',
  'pos: {export: store-a-inventory.csv}',
  'sales: {monthly_dir: a, daily_dir: b}',
  'market: {radius_km: 5}',
  'firebase: {project_id: store-a-project}',
].join('\n')

function write(text) {
  const dir = mkdtempSync(join(tmpdir(), 'store-'))
  const path = join(dir, 'store.yaml')
  writeFileSync(path, text)
  return path
}

describe('readStoreSettings', () => {
  it('reads the id and the tab title', () => {
    expect(readStoreSettings(write(VALID)))
      .toEqual({ id: 'store-a', siteTitle: 'SmartShelf AI — Store A', firebaseProjectId: 'store-a-project' })
  })

  it.each([['id', 'id'], ['site_title', 'site_title'], ['firebase', 'firebase.project_id']])(
    'stops and names %s when it is missing', (line, key) => {
    const text = VALID.split('\n').filter((l) => !l.startsWith(`${line}:`)).join('\n')
    expect(() => readStoreSettings(write(text))).toThrow(key)
  })

  it('stops and names the file when there is none', () => {
    expect(() => readStoreSettings('/nowhere/store.yaml')).toThrow('/nowhere/store.yaml')
  })

  it('reads this copy\'s committed settings', () => {
    expect(readStoreSettings().siteTitle).toBeTruthy()
  })
})

describe('the tab title', () => {
  it('replaces the placeholder with the store\'s title, escaped', () => {
    const plugin = siteTitlePlugin(write(VALID.replace('Store A"', 'Store <A> & co"')))
    const html = plugin.transformIndexHtml('<title>%SITE_TITLE%</title>')
    expect(html).toBe('<title>SmartShelf AI — Store &lt;A&gt; &amp; co</title>')
  })

  it('leaves no placeholder in index.html\'s title after the build', () => {
    const source = readFileSync(new URL('../../index.html', import.meta.url), 'utf8')
    expect(source).toContain('<title>%SITE_TITLE%</title>')
    expect(siteTitlePlugin().transformIndexHtml(source)).not.toContain('%SITE_TITLE%')
  })
})
