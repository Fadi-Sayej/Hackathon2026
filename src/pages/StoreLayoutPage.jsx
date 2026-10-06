import { unavailableReason } from '../lib/i18n/unavailableReason.js'
import { useI18n } from '../lib/i18n/index.js'
import { dirProps } from '../lib/utils/rtl.js'
import { namesFrom, ruleText, useDates } from './shelfCommon.js'
import { Names } from './ShelfNames.jsx'
import { ReaderWaiting } from './ReaderWaiting.jsx'
import { ShelfPhotos } from './ShelfPhotos.jsx'

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

function Fixture({ name, fixture, withoutWidth, withoutPicture, unplanned, nameOf, counting }) {
  const { t } = useI18n()
  const { date } = useDates()
  return (
    <article className="entry-card layout__fixture" data-fixture={name} {...dirProps()}>
      <header className="layout__head">
        <h3 className="entry-card__name"><bdi>{name}</bdi></h3>
        {fixture.chilled ? <span className="layout__tag">{t('layout.chilled')}</span> : null}
      </header>
      <p className="reorder__line">{t('layout.departments')} <Names barcodes={fixture.departments} nameOf={(d) => d} /></p>
      <p className="layout__dated">{t('layout.stated', { date: date(fixture.stated_on) })}</p>
      <ol className="layout__shelves">
        {fixture.shelves.map((s) => (
          <li key={s.shelf} className="layout__shelf" data-eye-level={s.shelf === fixture.eye_level_shelf || undefined}>
            <span className="layout__shelf-name">{t('layout.shelf', { n: s.shelf })}</span>
            <span className="layout__shelf-length"><bdi>{t('layout.length', { cm: s.length_cm })}</bdi></span>
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
      {/* D-33, F12-S1 FR-217: the pictures the team has still to crop from his photos. */}
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

export function StoreLayoutPage({ artefact, catalogue, photos = null }) {
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
        {photos ? <ShelfPhotos units={[]} {...photos} /> : null}
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
      {photos ? <ShelfPhotos units={capability.fixture_order || Object.keys(capability.fixtures || {})} {...photos} /> : null}
      <p className="reorder__line">{t('layout.shelfOrder')}</p>
      {(capability.fixture_order || Object.keys(capability.fixtures || {})).map((name) => [name, capability.fixtures[name]]).map(([name, fixture]) => (
        <Fixture key={name} name={name} fixture={fixture} withoutWidth={capability.without_width?.[name] || []}
          withoutPicture={capability.without_picture?.[name] || []}
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
