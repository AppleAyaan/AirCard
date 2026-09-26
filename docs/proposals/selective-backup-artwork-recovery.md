# Proposal: recover Wallet artwork from a selective backup

Related: [issue #58](https://github.com/Mak5er/AirCard/issues/58),
[PR #43](https://github.com/Mak5er/AirCard/pull/43), and
[PR #57](https://github.com/Mak5er/AirCard/pull/57).

Status: proposal based on a local extraction experiment; no application behavior
changes in this PR.

## Motivation

A saved original is the best source for a Restore Original action. The existing
restore PRs address saving artwork before applying a skin. A complementary route
is useful when the iPhone artwork has already been overwritten: a local iPhone
backup can contain an Apple Watch Wallet mirror that still has usable artwork.

We propose importing only the relevant artwork from that backup, previewing it,
and applying it to a user-selected card through AirCard's existing artwork writer.
This is artwork recovery, not a full device backup restore or payment-card restore.

## What our local experiment established

Our local scripts worked with a filtered backup containing Watch Wallet mirror
files. They queried `Manifest.db`, resolved stored file IDs to backup payloads,
and extracted `cardBackgroundCombined@2x.png` from paths matching:

```text
Library/DeviceRegistry/<watch-id>/NanoPasses/PaymentCards/<card-id>.pkpass/cardBackgroundCombined@2x.png
```

The extracted images were used to recover original visual marks for custom card
artwork. A read-only check while preparing this proposal found 12 matching
manifest rows and 12 available payloads with PNG signatures. That count verifies
local extraction availability; it is not a compatibility matrix or proof that
every image is an unmodified issuer original.

This establishes a useful recovery source. It does **not** establish an end-to-end
Restore Original feature, equivalence between Watch and iPhone assets, or support
for every iOS/watchOS version. The local scripts and backup contain personal card
identifiers and are not included here.

## Selective acquisition versus selective import

Keep these two operations explicit:

- **Selective acquisition:** create a backup containing the relevant Watch Wallet
  mirror subtree using a backup implementation that supports filtering. Our local
  workflow produced such a filtered backup, but a supported acquisition command,
  dependency, and version matrix still need to be documented before integration.
- **Selective import:** read only matching artwork from an existing backup.
  This can be implemented independently of filtered backup creation and is the
  proposed first milestone. Filtering an import does not make the original backup
  operation selective.

For an accessible, unencrypted backup manifest, the extraction lookup is:

```sql
SELECT fileID, domain, relativePath
FROM Files
WHERE relativePath LIKE
  'Library/DeviceRegistry/%/NanoPasses/PaymentCards/%.pkpass/cardBackgroundCombined@2x.png';
```

In the observed backup layout, a payload lives at
`<backup-directory>/<first-two-fileID-characters>/<fileID>`. Open the database
read-only and never modify the source backup. An implementation should validate
the domain, exact path structure, file ID format, containment, and decoded image
before accepting a candidate; the SQL pattern alone is not validation. Encrypted
backups need a supported unlock/decryption path or an explicit unsupported result.

## Proposed user flow

1. Prefer a verified original saved for this device and card. Preserve that
   original across subsequent skin changes and failed restores.
2. If no saved original exists, offer **Recover Artwork from Backup…**. Let the
   user choose a backup and inspect available Watch mirror images.
3. Show a preview and source details, including the backup date when available.
   Require the user to select the destination card. Do not assume Watch pass IDs
   match iPhone pass IDs, or silently select the newest backup as authoritative.
4. Describe imported images as recovered artwork until their provenance can be
   verified. If only a Watch `@2x` image exists, explain that it may differ in
   resolution or composition from the original iPhone artwork.
5. Before applying, preserve the current destination assets for rollback. Apply
   through the existing writer, regenerate supported output formats as needed,
   and invalidate the Wallet caches. Report asset-write and cache-refresh results
   separately; retain recovery files if either step fails.

An image recovered from a Watch is a source for reapplying artwork, not a
byte-for-byte restoration of all iPhone pass assets. Exact restoration requires
the original asset set, including any logos that customization changed and a
record of files that were absent. Never copy a whole Watch pass onto the iPhone.

## Limits and validation before shipping

This recovery route requires a suitable backup containing the Watch mirror.
It cannot recover artwork that is missing or already customized in every available
source. Issuer updates, reissued cards, multiple watches, and old backups can all
make a candidate inappropriate for the selected card.

The importer should first be tested with synthetic manifests covering missing
payloads, malformed paths, duplicate candidates, invalid images, and unsupported
encrypted backups. Device validation must then cover matching the destination,
previewing and applying recovered artwork, cache refresh, and rollback after a
partial failure. Record the tested iOS/watchOS versions and backup tooling.

Ship the read-only importer and preview first, then connect it to the restore
workflow after those checks. This proposal addresses the restoration portion of
#58; card selection UX, image editing, and image resource links remain separate.
