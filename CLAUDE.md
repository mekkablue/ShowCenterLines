# ShowCenterLines

A Glyphs reporter plug-in that draws a crosshair at the center of the current
selection in Edit View. All logic lives in one file:
`ShowCenterLines.glyphsReporter/Contents/Resources/plugin.py`.

Supported hosts: Glyphs 2, 3 and 4. There is no CI, no test suite and no build
step — the bundle *is* the deliverable.

## House style

Keep the plug-in small and direct. It is a few hundred lines that run inside
someone else's drawing loop, and it is read far more often than it is changed.

- **Tabs for indentation.** No trailing whitespace.
- **Fix the API call, don't wrap it.** Do not add `try`/`except` around Glyphs
  API calls, and never swallow exceptions in `background()` or another draw
  method. If something throws, the cause is almost always a wrong API for the
  running Glyphs version — find the right one. Defensive scaffolding hides the
  actual defect and is explicitly not wanted here.
- **Import Cocoa symbols from `Cocoa`,** not from `Foundation`. `NSColor` and
  `NSBezierPath` are AppKit; `Cocoa` is the umbrella that covers both halves.
- **Delete what you stop using.** Helpers left behind after a rewrite (an
  unused `transform()`, a now-dead import) get removed in review anyway.

## Version-dependent APIs

Branch on `Glyphs.versionNumber`. The cases that have actually bitten this
plug-in:

| What | Glyphs 4 | Glyphs 3 | Glyphs 2 |
| --- | --- | --- | --- |
| Italic angle of a layer | `layer.italicAngle` | `layer.italicAngle` | `layer.italicAngle()` |
| Guides on a layer | `layer.guides` | `layer.guides` | `layer.guideLines` |
| Show-guides default | `Glyphs.defaults["GSShowGuides"]` | `Glyphs.defaults["showGuides"]` | `Glyphs.defaults["showGuidelines"]` |
| Guide class | `GSGuide` | `GSGuide` | `GSGuideLine` |

Take the italic angle **from the layer, not from the master.** `layer.master`
is not always there, and the layer knows its own angle in every supported
version.

## Geometry

The center is the plain midpoint of `layer.selectionBounds` — on italic
masters too. Do not back-slant the selection to compute it; that was tried and
rejected. The italic angle affects only the *drawn vertical line*, which is
slanted through the center via `italicize(point, italicAngle=angle, pivotalY=y)`.

`layer.selectionBounds` returns infinity for some selections, hence the
`isinf(x) or isinf(y)` guard before drawing. That guard is the exception to the
"don't wrap it" rule: it is a documented return value, not an error.

## Releasing

In `ShowCenterLines.glyphsReporter/Contents/Info.plist`:

- bump `CFBundleVersion` (plain integer) on every user-visible change — this is
  what the Plugin Manager update feed compares
- bump `CFBundleShortVersionString` only for a real version change
- keep `productReleaseNotes` to a short phrase ("Streamlined code"), not a
  paragraph

Do **not** add a changelog section to `README.md`; the release notes field and
the git history are the changelog.

## Working in this repo

- Never run `python3 -m py_compile` (or anything that writes `__pycache__`)
  inside the bundle, and stage explicit paths rather than `git add -A`.
  `.gitignore` now covers `__pycache__/` and `*.pyc`, but the habit matters.
- The plug-in cannot be exercised outside Glyphs. Stub-module tests only prove
  the Python is self-consistent — they cannot confirm which Glyphs API is
  correct, and a diagnosis that has not been reproduced in the app is a guess.
  Say so plainly rather than building on it.
