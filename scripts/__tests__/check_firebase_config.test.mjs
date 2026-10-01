/**
 * ADR-036: `npm run check:firebase` checks the store id against configs/store.yaml.
 *
 * It used to fall back to 'yomyom-kafr-qasim' when VITE_STORE_ID was unset, and compared the
 * rules with that fallback, so any copy "matched" YomYom's rules. Now the rules must pin the
 * settings' id, and Production's VITE_STORE_ID must be it.
 */
import { spawnSync } from 'node:child_process'
import { mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { readStoreSettings } from '../store_settings.mjs'

const ROOT = fileURLToPath(new URL('../..', import.meta.url))
const KEYS = [
  'VITE_FIREBASE_API_KEY=AIzaTestTestTestTestTestTestTestTestTes',
  `VITE_FIREBASE_PROJECT_ID=${readStoreSettings().firebaseProjectId}`,
  'VITE_FIREBASE_APP_ID=1:123456:web:abcdef',
]

function run(lines) {
  const dir = mkdtempSync(join(tmpdir(), 'env-'))
  const path = join(dir, '.env')
  writeFileSync(path, lines.join('\n'))
  const result = spawnSync(process.execPath, ['scripts/check_firebase_config.mjs', '--env', path],
    { cwd: ROOT, encoding: 'utf8' })
  return { code: result.status, out: result.stdout + result.stderr }
}

describe('check:firebase and the store id', () => {
  const { id } = readStoreSettings()

  it('passes when VITE_STORE_ID is the settings id', () => {
    const { code, out } = run([...KEYS, `VITE_STORE_ID=${id}`])
    expect(out).toContain(`"${id}"`)
    expect(code).toBe(0)
  })

  it('fails when VITE_STORE_ID names another store', () => {
    const { code, out } = run([...KEYS, 'VITE_STORE_ID=another-store'])
    expect(out).toContain('configs/store.yaml')
    expect(code).toBe(1)
  })

  it('fails when VITE_STORE_ID is unset, with no fallback to any store', () => {
    const { code, out } = run(KEYS)
    expect(out).toContain('VITE_STORE_ID — missing')
    expect(code).toBe(1)
  })
})

describe('check:firebase and the project', () => {
  const { id } = readStoreSettings()

  it('fails when the web config names another Firebase project', () => {
    const lines = [...KEYS.filter((l) => !l.startsWith('VITE_FIREBASE_PROJECT_ID')),
      'VITE_FIREBASE_PROJECT_ID=another-project', `VITE_STORE_ID=${id}`]
    const { code, out } = run(lines)
    expect(out).toContain('PROJECT MISMATCH')
    expect(code).toBe(1)
  })
})
