# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository overview

This repo is `oth-body/mlrv--`, a fork of `trentgill/mlrv2` — a Max/MSP live-sampling instrument for monome grid controllers, refactored by Trent Gill/Michael Felix from Brian Crabtree's original `mlr`. It contains two independent things:

- **`mlrv2/`** — the original Max/MSP patches. Fork history is byte-identical to upstream (confirmed via `git describe --tags HEAD` and a full `git log` diff against `trentgill/mlrv2`); treat this directory as a frozen reference, not something to edit.
- **`mlrv-pd/`** — a from-scratch Pure Data reimplementation of `mlrv2`'s behavior, started 2026-09-17. This is the active-development directory.

Neither this fork nor upstream carries a `LICENSE` file — see `mlrv-pd/NOTICE` for the provenance/licensing situation before adding one or redistributing anything.

## `mlrv2/` — original Max/MSP (reference only, not conventional source)

`.maxpat` files are JSON-serialized visual dataflow patches, not text source in any meaningful sense — reading them gives you object names, comments, and creation args, but not the actual wiring/control-flow (that requires opening them in Max itself). There is no build, lint, or test tooling for this directory, and none is possible without a licensed Max/MSP install. `code/serialosc.js` is the one real piece of code in this directory (monome device discovery over OSC) and is the reference for `mlrv-pd/patchers/serialosc.pd`'s reimplementation.

Known gap in the original: `gridcell.maxpat`/`metapattern.maxpat` use `xrecord~`/`xgroove~` from Thomas Grill's third-party **xsample** external, not stock Max — `mixer.maxpat` itself contains the comment `"xsample external not found"`, meaning the original may already run degraded on a current Max install.

## `mlrv-pd/` — Pure Data port (active work)

Requires Pure Data (`pd`, tested against 0.56.5). No GUI is needed for validation — everything below runs headless.

### Validating a `.pd` file

Pd abstractions only resolve their creation-argument substitutions (`$1`, `$2`, ...) when instantiated as an object inside a parent patch — opening a `.pd` file directly with `-open` will always throw spurious `argument number out of range` errors for any abstraction file with unresolved `$N` references. **Always validate through a wrapper/test patch that instantiates the file as an object with real arguments**, not by opening the file directly. The existing harnesses in `mlrv-pd/tests/` are the pattern to follow for new ones:

```sh
pd -nogui -stderr -path mlrv-pd/abstractions mlrv-pd/tests/test_play_loop.pd
pd -nogui -stderr -path mlrv-pd/patchers    mlrv-pd/tests/test_serialosc.pd
```

Clean (no output) means no load or runtime errors. `pd -nogui` does not exit on its own once loaded — wrap with `timeout N` when scripting.

### Non-obvious Pd behaviors that will bite you again in this codebase

1. **`$N` substitution requires backslash-escaping in the saved file (`\$1`, not `$1`), and means different things by box type.** A bare, unescaped `$N` anywhere in a `.pd` file fails immediately with `argument number out of range`, regardless of context. An escaped `\$N` in an **object** box resolves once, at instantiation, to the abstraction's real creation argument. An escaped `\$N` in a **message** box instead refers to the Nth atom of whatever message triggers that box *at runtime* — not the abstraction's creation argument at all. To get an abstraction's creation argument into a message box, route it through an object first (e.g. `[float \$1]`, banged) so the message box's `\$N` captures it as a genuine runtime atom. (Reference: Pd's own bundled `/usr/lib/pd/doc/2.control.examples/dollarsign2.pd`.)
2. **`oscformat` treats a symbol-leading message as a method call, not data**, unless the message is prefixed with the literal `list` selector (e.g. `list localhost 8000`, not `localhost 8000`). Symbol-leading messages without `set`/`format` selectors will otherwise error with `no method for '<symbol>'`.
3. **`oscparse` splits an OSC address into separate atoms on `/` and prefixes the whole output with the literal selector `list`** — it does not hand back `/serialosc/device` as one symbol. `/serialosc/device m0000-0000 grid 40921` arrives as `list serialosc device m0000-0000 grid 40921`. `[route /serialosc/device]` will never match this; you need a chain that strips one segment at a time: `[route list]` → `[route serialosc monome]` → `[route device add remove]` (and similarly `[route grid]` → `[route key]` for a 3-segment address like `/monome/grid/key`). This is the "nested routing" pattern demonstrated in Pd's own `/usr/lib/pd/doc/5.reference/osc-format-parse-help.pd`.
4. **`[trigger]`/`[t]` outlets fire right-to-left**, and this determines real execution order, not just output order. When an action depends on state set up by an earlier step (e.g. a `netsend` needs `connect host port` delivered before any data is sent to it), the step that must run *first* has to be wired to the **higher-numbered (rightmost) outlet** of the `t`. Getting this backwards doesn't error — it silently sends data to an unconnected socket, which just vanishes. This also applies to a single outlet fanned out to multiple destinations without an explicit `trigger`; don't assume an order there without checking — restructure through an explicit `t` instead of relying on it.
5. **`;` and `,` inside comment/message text must be backslash-escaped (`\;`, `\,`) in the saved file**, same as `$`. An unescaped `;` silently ends the current `#X` line and starts Pd trying to parse whatever follows as a brand-new object — producing a baffling `error: <next-word>: no such object` that has nothing to do with the actual bug. If you hit that error and didn't add an object by that name, check your most recently edited comment for a stray punctuation mark first.
6. **`netreceive`'s listening port is a creation-time argument only — it cannot be rebound at runtime.** Sending it a float post-creation doesn't change its port; Pd reads an unlabeled float there as an implicit `send` call (push data to a connected TCP client), which errors `'send' only works for TCP` in UDP mode. If a port needs computing (e.g. from another creation arg), do the arithmetic before the object is instantiated, or just require the literal final port as the creation arg directly — don't try to compute-then-rebind after the fact.
7. **Connection indices in a `.pd` file are positional, not stable identifiers — inserting a new `#X obj`/`#X msg`/`#X text` line anywhere except the very end silently renumbers every object after it, breaking every existing `#X connect` line that references those higher indices with no error at save time.** This has caused real regressions twice in this port (Turn 7's `[t b]` fix, Turn 8's tilt outlet) — both times the file still "looked right" on a quick glance and only failed on the next `pd -nogui` load, or worse, loaded but wired the wrong objects together silently. **When adding a new object to an existing `.pd` file: always append it after the last existing `#X` line, never insert it between existing objects**, even if that makes the visual layout (`x y` coordinates) less tidy — coordinates are cosmetic, position-in-file is load-bearing. After any edit, re-derive the full index map by actually re-reading the file (don't trust a remembered count from before the edit) before writing new `#X connect` lines, and always reload in `pd -nogui` immediately after to catch a miscount before it compounds.

### Protocol decisions specific to this port

- **No `monome-device` external dependency.** `serialosc.pd` talks to the `serialosc` daemon directly over UDP (`netsend`/`netreceive` with `-u -b`, `oscformat`/`oscparse`) against the wire protocol `mlrv2/code/serialosc.js` documents: daemon on `127.0.0.1:12002`, `/serialosc/list` + `/serialosc/notify` to discover/subscribe, `/serialosc/device` replies give each device's own OSC port, and `/sys/port` + `/sys/prefix` sent to that device's port complete the handshake.
- **No `port + 12288` offset scheme.** The original `serialosc.js` computes its listen port as `arguments[0] + 12288`, purely as its own internal bookkeeping convention — the `serialosc` daemon itself doesn't require or care about this offset. This port drops it: `serialosc.pd`'s port creation argument is the literal port to bind and advertise, full stop (see gotcha 6 above for why the offset can't be replicated faithfully in Pd anyway).
- **`play_loop~.pd`** is the shared loop-playback abstraction every sample voice reuses: `phasor~` (0–1 ramp) → scaled into `[loopStart, loopEnd)` via control-rate arithmetic → `tabread4~`. Its single control inlet takes either `bang` (retrigger from loop start) or a 3-element list `rate loopEndSamples loopStartSamples` for an atomic parameter update — this relies on Pd's `unpack` firing right-to-left, which is why the list argument order matters and isn't arbitrary. Known limitation, undocumented workaround: `tabread4~`'s 4-point interpolation window can read ~2 samples outside the loop bounds at the seam (no crossfade).

### Testing against a fake serialosc daemon

`mlrv-pd/tests/fake_serialosc.py` is a stdlib-only Python fixture that stands in for the real `serialosc` daemon + a grid device (real `serialosc` isn't packaged for this machine's distro and isn't installed). `mlrv-pd/tests/run_handshake_e2e.sh` runs it against `serialosc.pd` and asserts on both sides' logs — this is the actual regression test for anything touching `serialosc.pd`'s network behavior, not just a clean `pd -nogui` load. Run it after any change to that file:

```sh
mlrv-pd/tests/run_handshake_e2e.sh   # exit 0 and 7/7 PASS lines means it's still correct
```

Trust this script's actual exit code, not any "verified" claim written in a comment inside `serialosc.pd` — an earlier version of that file shipped with a confidently-worded but false verification claim (the script it referenced had a path bug and had never actually been run successfully). If you update `serialosc.pd`'s behavior, update and rerun this script in the same change, not after.

### Current implementation state

`play_loop~.pd`, `serialosc.pd` (discovery + handshake + grid-key routing + LED output), and `grid.pd` (thin `x y level` LED-display translator) exist. `serialosc.pd` is confirmed against **real hardware, bidirectionally, under sustained load**: a physically connected monome 64 grid (serial `m64-0865`) — specifically a **greyscale/varibright grid with a tilt sensor**, confirmed by reading `serialosc`'s own source, not assumed — round-tripped a full 64-key sweep of real key presses (`grid_key: x y state` out outlet 1) into real LED output (`x y level` into inlet 1) through the real `serialosc` daemon, with the LEDs visually confirmed lighting up following the presses. It also passes the software-only `run_handshake_e2e.sh` suite against the fake daemon fixture. `grid.pd`'s passthrough behavior is verified in isolation and by composition (see `mlrv-pd/tests/grid_echo_test.pd`), not by a fresh live key-press session — see the handoff log for why that's a reasonable judgment call here. `play_loop~.pd` is only verified against an all-zero test array — no real audio content tested yet. `/serialosc/add`/`/serialosc/remove` now correctly re-trigger a rescan without crashing (fixed a real bug where their payload — confirmed to carry the same id/type/port triple as `/serialosc/device` — was fed directly into a `[float]` object expecting a bare bang). The tilt sensor is wired up and confirmed live: enabled as part of the handshake (`/monome/tilt/set 0 1`), events come out a new outlet 2 as `sensor x y z`, confirmed as a continuous real-time stream while the user physically tilted the grid, not just a one-shot event. `serialosc.pd` now covers every capability this specific device has (key input, greyscale LED output, tilt input), all confirmed on real hardware. Sample loading, mixer, and effects are not started. `play_loop~.pd` is still the one piece only verified against silent/fake data — no real audio content tested yet.

**Real `serialosc` daemon, if you need it running again:** built at `~/repos/serialosc/build` (not part of this repo — a sibling checkout) via the `cmake` path from its own README (builds `liblo`/`libmonome`/`libuv` from bundled submodules, no system packages needed, no sudo needed to build). Running it needs either `sudo` (the device node `/dev/ttyUSB0` is `root:uucp`, and this user isn't in `uucp` yet) or a proper `sudo usermod -aG uucp <user>` + fresh login: `sudo ~/repos/serialosc/build/bin/serialoscd`, then confirm with `ss -uln | grep 12002`.

## Git conventions for this repo

`upstream` remote points at `trentgill/mlrv2`. `origin` is the public fork. It was a byte-identical mirror of upstream until 2026-09-17, when the `mlrv-pd/` work was pushed to `origin` with the user's explicit confirmation — this fork's first-ever independent history. Pushing is no longer a first-time event, but it's still a public fork under the user's name; confirm before pushing anything you weren't explicitly asked to push.

## Where the full running history lives

Progress on the `mlrv-pd/` port is tracked turn-by-turn outside this repo, in the user's Obsidian vault (`mlrv-pd Handoff Log.md`), which is the authoritative source for "what's actually done vs. planned" — more current than any summary here.
