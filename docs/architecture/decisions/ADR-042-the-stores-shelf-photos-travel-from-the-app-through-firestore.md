---
ID: ADR-042
Title: The store's shelf photos travel from the app through Firestore, and the nightly collects and reads them
Status: Accepted
Owner: smartshelf-architect
Date: 2026-10-06
Parent: [System Design](../system-design.md) §19
Related Specs: F12-S1 (FR-218 v0.11, FR-224 … FR-227, AC-212 … AC-214, NFR-080, OQ-1212)
Updated: 2026-10-08 (Task 8.13: photos that waited are read on a later night, confirmed by the owner: "keep"; each reading adds to the earlier ones)
Inputs: [D-13, D-23, D-34, D-37, ADR-029, ADR-032, ADR-036, ADR-039, ADR-041, firestore.rules, .github/workflows/collect-daily.yml, docs/reviews/F12-photo-upload-mockups.md]
---

# ADR-042 — The shelf photos travel from the app through Firestore

**Status:** Accepted (2026-10-06, by the repository owner: "approved", to "You can say 'approve
all', or name what to change", asked of the screen, its wording, option A or B, the nightly's
reading, and two older sentences; recorded as all five as drawn, with B, the recommended option).
With the screen ([mockups](../../reviews/F12-photo-upload-mockups.md)) and F12-S1 v0.11, OQ-1212.
It amends ADR-041 Decisions 1 and 2.

## Context

D-37 (2026-10-06): the app gets an upload screen for the store's shelf photos, so they reach the
shelf reader without anyone moving files. D-37 left two things open: the screen, and how a photo
travels from the owner's phone to `data/internal/shelf_photos/`, where the reader looks (ADR-041
Decision 1).

The app already signs the owner in and writes the owner's state to Firestore, under
`stores/<store>/`, and the rules already let the owner write there and the team only read
(ADR-029). The nightly already holds the service account that reads Firestore, and already
commits the store's files to the private repository.

A phone photo is 2 to 6 MB. A Firestore document holds at most 1 MiB.

Cloud Storage for Firebase, the usual place for files, needs the Blaze plan: since 2026-02-03 a
project on the free Spark plan has no access to any bucket, its `appspot.com` default included
([Firebase, "Default bucket and billing requirements"](https://firebase.google.com/docs/storage/faqs-storage-changes-announced-sept-2024)).
Blaze keeps a free allowance, but it needs a billing account and a card. Which plan this project
is on cannot be read from here.

## Decision

1. **The screen** (D-37). It sits on Store layout, under the page's opening. One photo per
   shelving unit:
   - the owner names the unit, either from the units the layout file records or by typing a
     name, because the first photos come before the layout does;
   - the owner takes or chooses a photo, sees it, and presses Send;
   - the screen says when the photo is sent, and lists what has been sent, with each photo's
     state: sent, collected, or read.

   A team account sees the screen disabled, as it sees every control (ADR-029). On a deployment
   with no Firebase project, where nothing could be sent, the screen is not shown.
2. **The carrier is Firestore** (option B). A photo is written under the store's own subtree,
   which the deployed rules already govern, so no new rule and no new service is needed:
   - `stores/<store>/shelfPhotos/<photo>/parts/<n>` holds the photo's bytes, at most 900,000
     bytes a part;
   - `stores/<store>/shelfPhotos/<photo>` holds the photo's manifest: the unit's name, when it
     was sent, its size, its number of parts and its SHA-256 digest;
   - the parts are written first and the manifest last, so a manifest means the whole photo is
     there;
   - a photo's id is fixed when it is chosen, so pressing Send again rewrites the same documents
     and never makes a second copy.
3. **The photo as taken.** A JPEG is sent byte for byte, so the reader measures the camera's own
   pixels. Anything else, or a JPEG over 12 MB, is redrawn once as a JPEG at quality 0.92, with
   its longest side at most 4,096 px. That is about 0.5 mm a pixel across a 2 m unit. Sending
   starts only when the phone is online.
4. **The nightly collects** (option B). Before the engine runs, a step with the service account:
   - reads every manifest, and joins its parts;
   - checks the joined bytes against the manifest's size and digest;
   - writes each photo that passes to
     `data/internal/shelf_photos/<the night's UTC date>/<the unit's name>/<photo>.jpg`, and commits
     it with the night's other store files;
   - deletes a photo's documents only after that commit is pushed.

   A photo that fails its check stays where it is and is named in the run's summary. Parts with
   no manifest after two days are an abandoned send, and are deleted. The unit's name is used as
   the folder's name, with only `/`, `\`, control characters and leading dots removed, so it
   meets the layout file's unit of the same name (ADR-041 Decision 1).
5. **The nightly reads what it collected.** *Amends ADR-041 Decision 2.* When the nightly has
   collected photos and the model key is set, it runs the reader on that night's folder before
   the engine runs, so the same night's artefact uses the readings. It works within
   the reader's request ceiling (60) and time budget (600 s), and commits the readings. With no
   new photo, it asks nothing. With no key, the photos wait in their folder, and
   `npm run read:shelves` still reads any folder on demand.

   *Built in Task 8.13 (2026-10-08), and confirmed by the repository owner the same day ("keep", to 'Say "keep it", or "only tonight's"'):* a photo that waited, for the key, the
   layout file, or a request that failed, is read on a later night, once, within the same
   bounds (`read_shelves.py --unread`). As approved, a photo sent before its unit was recorded
   would wait for a command, and the owner cannot run one. Each reading adds to the earlier
   ones: a unit read whole replaces what was read of it before, and a width that two photos
   disagree on is unknown (F12-S1 FR-221). The key is not set today, so nothing is asked until
   it is.
6. **What the page shows.** The artefact lists each collected photo: the unit, the night it was
   collected, and the night it was read, if it was. No photo is published, only these dates
   (ADR-041 Decision 1). The screen adds the photos still waiting in Firestore, which the
   owner's account can read.
7. **Photos sent by hand still count.** *Amends ADR-041 Decision 1.* A photo committed to the
   folder by hand is read the same way. The upload is the way in, not the only way.

## Options

### A. Cloud Storage for Firebase
The usual home for files, with no 1 MiB limit and no splitting. It needs:
- the Blaze plan: a billing account and a card;
- a second rules file and its deployment, beside `firestore.rules`;
- the Storage SDK in the app, which is not in the bundle today.

The nightly would collect from the bucket instead, with the same service account. Everything else
above is the same.

### B. Firestore as the carrier (recommended, and chosen)
It works on the project as it is: the free plan, the deployed rules, the SDK the app already
loads, and the service account the nightly already holds. Its costs:
- about 60 lines on each side to split and join a photo;
- writes and reads within the free allowance, which allows 20,000 writes a day and 1 GiB
  stored. A store of 15 units sends about 15 photos in about 100 writes, deleted the same night.

Firestore is not meant to hold files. Here a photo stays in it for less than a day.

## Rejected options

### The reader on demand only
ADR-041 Decision 2 as it stands. The photos would arrive without anyone moving files, but nothing
would read them until someone ran a command, and the owner cannot run one. D-37 asks that the
photos *reach the reader*.

### The photos kept in Firestore or Storage for good
The store's copy of its data is the private repository (ADR-036). A second home for the photos
would be a second place to secure and to delete from.

### Shrinking every photo in the phone
Smaller photos send faster, but the reader measures edges to ±5 mm on the full-resolution photo
(ADR-041 Decision 5). Only a photo too large to send is redrawn.

## Consequences

**We accept:**
- the team's accounts can read a photo during the hours it waits in Firestore. The rules let the
  team read the store's subtree, and the team already holds the repository the photo goes to;
- the nightly starts at 00:00 UTC, which is 03:00 in Israel in summer and 02:00 in winter. A
  photo sent just after it starts waits a day;
- Preview deployments use the store `preview-sandbox`, which the rules do not name, so a photo
  sent from a Preview says it did not send.

**We gain:** the owner photographs a unit and presses Send, and the next morning its pictures and
current facings are on Store layout and Shelf plan, with no one moving a file. Its widths are
recorded the same night and used once the acceptance run passes (ADR-041 Decision 9).

**We will know it was wrong if:** photos stop arriving whole (the digest check names them), or the
store's photos outgrow the free allowance. Then option A is the next step.

## Reversibility

High. The screen hands its photo to one function, and only that function and the nightly's
collect step know where the photo travels. Moving to option A changes those two.

## Binds

| F# | How this constrains it |
|---|---|
| F12 | The shelf photos come in through the app (F12-S1 FR-224 … FR-227), and the nightly collects and reads them (FR-218 v0.11) |
| Every other feature | Unaffected |
