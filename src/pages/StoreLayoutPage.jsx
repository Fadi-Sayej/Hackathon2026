import { unavailableReason } from '../lib/i18n/unavailableReason.js'
import { useI18n } from '../lib/i18n/index.js'
import { dirProps } from '../lib/utils/rtl.js'
import { namesFrom, ruleText, useDates } from './shelfCommon.js'
import { Names } from './ShelfNames.jsx'
import { ReaderWaiting } from './ReaderWaiting.jsx'
import { ShelfPhotos } from './ShelfPhotos.jsx'
import { ShelfUnits } from './ShelfUnits.jsx'

/**
 * Store layout: his shelf units as the team recorded them from his photographs (F12-S1 FR-190,
 * FR-191, FR-196). It renders `layout_facts` and computes nothing (ADR-001), and it looks the same
 * before and after daily sales arrive (D-30). Nothing on it changes anything (FR-195): the layout
 * file is the team's, and the browser never writes it (ADR-037).
 */

// What keeps a product off every plan for a reason of the layout itself. The rest of the
// population's reasons (no sale in the window, kept off by his rule) are the plan's, and Shelf
// plan lists them beside the fixture they concern.
const LAYOUT_REASONS = ['stock_unknown', 'rejected']

function Rejected({ rejected, nameOf }) {
  const { t } = useI18n()
  if (!rejected?.length) return null
  return (
    <section className="layout__missing" data-missing="rejected">
      <h3>{t('layout.rejected')}</h3>
      <ul>
        {rejected.map((r) => (
          <li key={`${r.kind}|${r.key}`}>
            <span>{t(`layout.rejected.kind.${r.kind}`)}{r.key ? ': ' : ''}{r.key ? <bdi>{r.kind === 'width' || r.kind === 'current' ? nameOf(r.key) : r.key}</bdi> : null}</span>
            {/* The loader's reason is written for the team, who correct the file (ADR-037). */}
            <span className="layout__team-note">{t('layout.rejected.teamNote')} <bdi dir="ltr" lang="en">{r.reason}</bdi></span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function Fixture({ name, fixture, withoutWidth, withoutHeight = [], withoutPicture, unplanned, nameOf, counting }) {
  const { t } = useI18n()
  const { date } = useDates()
  return (
    <article className="entry-card layout__fixture" data-fixture={name} {...dirProps()}>
      <header className="layout__head">
        <h3 className="entry-card__name"><bdi>{name}</bdi></h3>
        {fixture.chilled ? <span className="layout__tag">{t('layout.chilled')}</span> : null}
      </header>
      <p className="reorder__line">{t('layout.departments')} <Names barcodes={fixture.departments} nameOf={(d) => d} /></p>
      {/* D-38: a unit the owner entered in the app says so, not "recorded by the team". */}
      <p className="layout__dated">{t(fixture.recorded_by === 'app' ? 'layout.stated.app' : 'layout.stated', { date: date(fixture.stated_on) })}</p>
      <ol className="layout__shelves">
        {fixture.shelves.map((s) => (
          <li key={s.shelf} className="layout__shelf" data-eye-level={s.shelf === fixture.eye_level_shelf || undefined}>
            <span className="layout__shelf-name">{t('layout.shelf', { n: s.shelf })}</span>
            <span className="layout__shelf-length"><bdi>{t('layout.length', { cm: s.length_cm })}</bdi></span>
            {/* D-38: the height above the shelf, where the owner gave one. */}
            {'height_cm' in s ? (
              <span className="layout__shelf-length"><bdi>{s.height_cm ? t('layout.height', { cm: s.height_cm }) : t('layout.openAbove')}</bdi></span>
            ) : null}
            {s.shelf === fixture.eye_level_shelf ? <span className="layout__tag layout__tag--eye">{t('layout.eyeLevel')}</span> : null}
            <span className="layout__dated">{t('layout.measured', { date: date(s.measured_on) })}</span>
          </li>
        ))}
      </ol>
      {fixture.rules?.length ? (
        <div className="layout__rules">
          <h4>{t('layout.rules')}</h4>
          <ul>{fixture.rules.map((r, i) => <li key={i}>{ruleText(t, r, nameOf)}</li>)}</ul>
        </div>
      ) : null}
      {withoutWidth.length ? (
        <p className="reorder__needs" data-missing="width">
          <span className="reorder__needs-pill">{t('layout.noWidth', { n: withoutWidth.length })}</span>
          <Names barcodes={withoutWidth} nameOf={nameOf} />
          <span className="layout__counting">{counting}</span>
        </p>
      ) : (
        <p className="layout__dated">{t('layout.allMeasured')}</p>
      )}
      {withoutHeight.length ? (
        <p className="reorder__needs" data-missing="height">
          <span className="reorder__needs-pill">{t('layout.noHeight')}</span>
          <Names barcodes={withoutHeight} nameOf={nameOf} />
        </p>
      ) : null}
      {/* D-33, F12-S1 FR-217: the pictures not yet cut from the store's photos. */}
      {withoutPicture.length ? (
        <p className="reorder__needs" data-missing="picture">
          <span className="reorder__needs-pill">{t('layout.noPicture')}</span>
          <Names barcodes={withoutPicture} nameOf={nameOf} />
        </p>
      ) : (
        <p className="layout__dated">{t('layout.allPictured')}</p>
      )}
      {LAYOUT_REASONS.filter((r) => unplanned?.[r]?.length).map((r) => (
        <p key={r} className="reorder__needs" data-missing={r}>
          <span className="reorder__needs-pill">{t(`layout.unplanned.${r}`)}</span>
          <Names barcodes={unplanned[r]} nameOf={nameOf} />
        </p>
      ))}
    </article>
  )
}

/** The catalogue's departments, for the form's list: as the catalogue spells them (ADR-037). */
function departmentsOf(catalogue) {
  const products = catalogue?.products || []
  return [...new Set(products.map((p) => p.department).filter(Boolean))].sort((a, b) => a.localeCompare(b))
}

/** The units as recorded, in the file's order, as the form edits them. */
function unitsOf(capability) {
  return (capability.fixture_order || Object.keys(capability.fixtures || {})).map((name) => {
    const f = capability.fixtures[name]
    return {
      name, departments: [...f.departments], chilled: f.chilled, eye_level_shelf: f.eye_level_shelf ?? null,
      shelves: f.shelves.map((s) => ({ length_cm: s.length_cm, height_cm: s.height_cm ?? '' })),
    }
  })
}

export function StoreLayoutPage({ artefact, catalogue, photos = null, units = null }) {
  const { t } = useI18n()
  const { date } = useDates()
  const capability = artefact?.capabilities?.layout_facts
  const nameOf = namesFrom(catalogue)

  if (!capability || capability.status !== 'available') {
    // AC-172: the measurements have not been recorded; or every fixture was rejected, named.
    return (
      <section className="capability layout" data-capability={capability ? 'layout_facts' : undefined} {...dirProps()}>
        <h2 className="capability__unavailable reorder__waiting">{unavailableReason(t, capability?.unavailable_reason, 'layout_facts')}</h2>
        {capability?.unavailable_reason === 'layout_all_rejected'
          ? <Rejected rejected={capability.rejected} nameOf={nameOf} />
          : <p className="reorder__line">{t('layout.waiting.next')}</p>}
        {units ? <ShelfUnits units={[]} departments={departmentsOf(catalogue)} {...units} /> : null}
        {photos ? <ShelfPhotos units={[]} collected={capability?.photos || []} {...photos} /> : null}
      </section>
    )
  }

  const window = capability.evidence_window
  const counting = capability.without_width_counts === 'planned'
    ? t('layout.counting.planned', { first: date(window?.first_day), last: date(window?.last_day) })
    : t('layout.counting.catalogue')

  return (
    <section className="capability layout" data-capability="layout_facts" {...dirProps()}>
      <ReaderWaiting reader={capability.reader} />
      {units ? <ShelfUnits units={unitsOf(capability)} departments={departmentsOf(catalogue)} {...units} /> : null}
      {photos ? <ShelfPhotos units={capability.fixture_order || Object.keys(capability.fixtures || {})}
        collected={capability.photos || []} {...photos} /> : null}
      <p className="reorder__line">{t('layout.shelfOrder')}</p>
      {(capability.fixture_order || Object.keys(capability.fixtures || {})).map((name) => [name, capability.fixtures[name]]).map(([name, fixture]) => (
        <Fixture key={name} name={name} fixture={fixture} withoutWidth={capability.without_width?.[name] || []}
          withoutHeight={capability.without_height?.[name] || []} withoutPicture={capability.without_picture?.[name] || []}
          unplanned={capability.unplanned?.[name]} nameOf={nameOf} counting={counting} />
      ))}
      {capability.departments_on_no_fixture?.length ? (
        <p className="reorder__needs" data-missing="departments">
          <span className="reorder__needs-pill">{t('layout.noFixture')}</span>
          <Names barcodes={capability.departments_on_no_fixture} nameOf={(d) => d} />
        </p>
      ) : null}
      <Rejected rejected={capability.rejected} nameOf={nameOf} />
    </section>
  )
}
