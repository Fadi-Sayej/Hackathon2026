/**
 * Human text for a validation issue, in the reader's language.
 *
 * WHY THIS LIVES HERE AND NOT IN validation.js
 *   The adapters are a pure data layer: they run in Node during the build, in
 *   tests, and in the browser, and none of those contexts have a React i18n
 *   context to read. So `createIssue()` keeps its English `message` as the
 *   record of what went wrong, and the UI — the only place a language exists —
 *   translates by the stable `code` at render time.
 *
 * Any code without a key falls back to the English message rather than showing
 * a raw key, so a new issue type degrades to English instead of to gibberish.
 */
export function translateIssue(issue, t) {
  if (!issue) return ''
  const key = `val.${issue.code}`
  const translated = t(key, { field: issue.field ?? '' })
  return translated === key ? (issue.message ?? '') : translated
}
