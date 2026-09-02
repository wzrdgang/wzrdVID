# WZRD.VID EULA Architecture

This document keeps one substantive AMPYX legal core across distribution
channels. It is an engineering plan, not legal advice or evidence of App Store
approval.

## Authoritative Core

The repository-root `LICENSE` is the authoritative WZRD.VID Freeware License.
`NOTICE.md` records current ownership and branding facts,
`docs/LICENSE_FAQ.md` explains the same policy in plain language, and
`docs/LICENSE_HISTORY.md` preserves prior grants.

No second public EULA with different substantive rights is maintained. Private
release engineering checks qualified copies against the same policy anchors.

## Direct Distribution

Future qualified direct-download app bundles copy the authoritative files into
`WZRD.VID.app/Contents/Resources/Legal/` as:

- `WZRDVID_FREEWARE_LICENSE.txt`;
- `WZRDVID_NOTICE.txt`; and
- `LICENSE_HISTORY.md`.

The same directory retains all Phase L2D third-party notices, exact license
texts, source provenance, SPDX data, and Qt replacement materials. The root
license applies only to AMPYX-owned portions; third-party terms control their
components.

The official public repository presents `LICENSE`, `NOTICE.md`, the FAQ, and
license history directly. Its automatic main-branch archives contain the public
documentation and site tree, not the desktop application or current proprietary
desktop development source. Any copy that includes or expressly references the
new license is governed prospectively by it.

## Mac App Store Distribution

Before any Mac App Store submission, use the root `LICENSE` as the substantive
source for an App Store custom EULA or other Apple-supported presentation. Any
channel-specific formatting must preserve, without contradiction:

- no-charge personal, professional, and commercial use;
- paid client work and monetized user output;
- no AMPYX ownership claim over user media or output;
- restrictions on resale, repackaging, unauthorized redistribution, modified
  distribution, and reuse of AMPYX-owned code in another software product;
- all historical grants;
- all third-party rights and broader third-party-license permissions; and
- applicable LGPL inspection, debugging, modification, replacement, relinking,
  reverse-engineering, and redistribution rights.

The complete bundled Legal directory must remain in the App Store build. Apple
terms must not be represented as replacing third-party licenses or historical
WZRD.VID grants.

**COUNSEL REVIEW:** confirm warranty and liability language, governing law,
territory selection, Apple custom-EULA configuration, enforceability of
redistribution/repackaging restrictions, and compatibility with then-current
App Store terms before submission.

No App Store submission, agreement configuration, signing change, or publication
is performed by this architecture document.

## Application Surface

The current desktop and Lite applications have no existing About, Help, or legal
viewer suitable for adding this text without new product work. The direct local
path is `Contents/Resources/Legal/`. A later distribution phase may add a factual
link or viewer, but it must consume the same authoritative files rather than
introduce different terms.

## Consistency Matrix

| Policy | Required current state |
| --- | --- |
| Owner | AMPYX LLC |
| Proprietary | Yes |
| Freeware | Yes |
| Personal use | Yes |
| Professional use | Yes |
| Commercial use | Yes |
| Monetized output | Yes |
| AMPYX claims user output | No |
| Resale of WZRD.VID | Restricted |
| Redistribution | Restricted |
| Modified redistribution | Restricted |
| Third-party rights preserved | Yes |
| LGPL rights preserved | Yes |
| Historical rights preserved | Yes |
| Open-source claim | No |
| AMPYX proprietary-source disclosure promise | No |

Private release engineering enforces this matrix against qualified copies. The
public repository preserves the controlling documents and historical record.
