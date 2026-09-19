# mlrv-pd frontends

Draft companion web surfaces for the Pure Data port in this repo. None of
these are wired to the Pd patch — they're mock-ups of what an `mlrv-pd`
frontend could look like, built from the abstractions and patchers in
`../abstractions/` and `../patchers/`.

The Pd instrument itself remains grid-only by design. These pages explore
what useful browser-side surfaces would look like alongside it.

---

## What's here

| Page | What it is |
| --- | --- |
| `index.html` | Landing page. Links the three explorations. |
| `patch-graph.html` | The Pd source as a navigable web graph. Parse any `.pd` file in the repo, click objects to inspect, click connections to highlight their path. |
| `virtual-grid.html` | Clickable 8×8 LED grid in the browser. Same mapping rules as the hardware (`y=7` trigger row, `slot = x`, `(7,0)` = stopall). |
| `sample-loader.html` | Drag-drop WAVs into slots 0–7. Emits the exact `play` / `stopall` messages `file_poly.pd` expects. |

Shared assets live in `assets/` (one CSS file, one JS helper file, one
self-contained `.pd` parser).

Screenshots of the rendered pages are in `screenshots/`.

---

## Running it

The site is plain static HTML. Any HTTP server will serve it — there is no
build step, no bundler, no dependencies to install.

### One-liner (recommended)

```sh
cd mlrv-pd && python3 -m http.server 8765 --bind 127.0.0.1
```

Then open <http://127.0.0.1:8765/frontends/index.html>.

### Open directly (file:// mode)

The four pages can also be opened directly in a browser without any
server. Just double-click `frontends/index.html` (or `xdg-open` it from
the command line).

The catch was that `patch-graph.html` originally used `fetch()` to read
the `.pd` source files at load time, and browsers refuse `fetch()` from
`file://` URLs for security reasons. That's fixed now — the nine main
`.pd` files are inlined into `assets/embedded-pd.js`. When the page can't
fetch, it falls back to the embedded copy and shows a small
**"file:// mode — using embedded source"** badge in the corner.

Trade-offs of file:// mode:

- All three other pages work identically (virtual grid, sample loader,
  landing).
- Patch graph works for the 9 bundled `.pd` files only. If you add a new
  file and want to view it, either re-run `assets/embed-pd.sh` to
  rebuild `embedded-pd.js`, or serve the site over HTTP.

---

## How each page works

### `patch-graph.html`

Renders any `.pd` file in the repo as an SVG graph.

**Top of the page** — file selector. Defaults to `patchers/serialosc.pd`
(the most complex one). Pick another file from the dropdown; the graph
re-renders.

**Hover** an object — its label highlights.

**Click an object** — the object gets an orange outline, every connection
touching it gets highlighted, and the right sidebar shows:

- the object class
- its position in the file
- its creation arguments
- a one-line description of what the class does

**Click a connection** — both endpoints highlight and the sidebar describes
the wiring.

**Tables list** — every `table NAME N` declaration in the patch (sample
buffers, length tables, etc.) shows up here. Useful for seeing at a glance
which names a patch exposes for its `soundfiler` lookups.

#### What the parser handles

The parser is in `assets/pd-parser.js`. It reads the vanilla Pd syntax the
files in this repo already use:

- `#N canvas` — viewport size
- `#X obj X Y CLASSNAME ARGS...` — object boxes
- `#X msg X Y CONTENT;` — message boxes (terminator `;` stripped)
- `#X text X Y CONTENT` — free-floating comments (rendered as plain text,
  not as boxes)
- `#X connect FROM_OBJ FROM_OUT TO_OBJ TO_IN` — wire indices, file-order
  (this is the load-bearing detail CLAUDE.md warns about — index 7)
- Trailing `;` on object lines (the in-line Pd comment syntax) is stripped
  from class names and args

Files that use non-vanilla features (abstractions referenced by relative
path with `$N` defaults baked in, subpatches with `pd NAME` headers,
`#X restore`, etc.) will parse but may render their subpatch contents
as a flat list rather than nested. None of the current 9 files in this
repo need that.

#### What it doesn't do

- No inlet/outlet count auto-detection — the parser has a hard-coded table
  per known class. Unknown classes default to 1 in / 1 out, which is fine
  for most abstractions but will mis-render `unpack f f f` as a single-out
  box. Add your class to `socketCount()` in `assets/pd-parser.js` to fix.
- No zoom/pan. Big patches (e.g. `file_poly.pd` with 83 objects) overflow
  the canvas — scroll horizontally to see the rest. Future improvement.
- No subpatch nesting.
- No execution animation / signal tracing.

### `virtual-grid.html`

8×8 clickable grid. Clicking a cell dispatches the same `x y state`
tuple `mapping.pd` expects from the real `serialosc` daemon.

**Trigger row is y=7.** Click `(x, 7)` to play slot `x`. Click `(0, 7)`
to stopall. Everything else is a no-op (matches the current mapping
rules; deferred features are listed in the sidebar cheat sheet).

**Slot status indicator** — slots 0 and 1 are preloaded by default
(matching `mlrv.pd`'s `loadbang`). The remaining slots show as empty —
clicking their trigger cell logs "slot N empty — ignored" instead of
playing.

**Active voices counter** — shows 0..4. Pd's `file_poly.pd` uses round-robin
voice allocation; the browser mirrors that (voice 0 is stolen when all 4
are busy).

**Event stream** (right sidebar) — every key event and the resulting Pd
message it would emit, color-coded by type (`key`, `play`, `stop`, `osc`,
`led`). Useful for seeing what traffic the real instrument generates.

#### What it doesn't do

- No audio. There's no Web Audio playback wired to the play action —
  the "play" buttons only simulate the message protocol. If you want to
  actually hear samples, use the real Pd instrument.
- No varibright LED animation. Cells snap between levels, no fade.
- No tilt sensor — `serialosc.pd` arms tilt sensor 0 in its handshake,
  but the browser grid has no equivalent.

### `sample-loader.html`

Drag-and-drop WAV (or AIFF/OGG/FLAC) files into slots 0–7.

**Drop on the main dropzone** — fills the next-empty slot.
**Drop on a specific slot card** — targets that slot (replacing whatever's
loaded).
**Click `browse`** — same as the main dropzone, opens a file picker.

Once a slot is loaded, its card shows the filename and frame count. The
**play** button emits `play <slot> 1 0 <frames>` — exactly what
`file_poly.pd` accepts. The **stop** button frees that slot's voice.
**All slots' play buttons are disabled until something is loaded** —
matches the real instrument, which errors silently on a `play <empty>`.

**Outgoing Pd messages** (right sidebar) — every message the loader would
send to `file_poly`, with the slot index, frames, and resolved voice
number. Format matches what you'd see in the Pd console with `print` on
the inlet.

**Master bus** — fake VU meter that climbs when a voice is playing. This
is purely cosmetic — it doesn't reflect actual audio level. The real
master's `env~` meter would feed this in a wired-up version.

#### What it doesn't do

- No actual audio output. Playback is simulated.
- No write-back to disk. The `load <slot> <path>` message requires
  `file_poly.pd` to do a `soundfiler read` on a real path — for the
  browser, the file is decoded in-memory via `AudioContext.decodeAudioData`
  but the bytes are never given to Pd. To actually load WAVs into the Pd
  side, drop them in `samples/` and edit `mlrv.pd`'s loadbang section.
- No drag-reorder between slots. Drop replaces; clear with stop + manual
  re-drop.

---

## Design notes

### Visual direction

Hardware-feel for grid surfaces (dark, LED-emissive — levels 0..15 map to
an orange-luminance ramp), modern dev-tool polish for everything else
(restrained palette, monospace numerics, single accent).

The accent is the monome brand orange `#ff5500`. It's used semantically
(slot loaded, active voice, selection state) rather than decoratively.
The dark grid surface uses an orange-tinted black (`--led-1` etc.) rather
than pure black so unlit LEDs still read as "warm" cells rather than
dead space.

### Surface archetypes

Each page commits to one surface archetype (per `claude-design`'s
surface-first rule):

- **patch-graph.html** — Monitor surface. Density and glanceability
  beat a hero. No marketing framing, no call-to-action.
- **virtual-grid.html** — Operate surface. The grid is the action.
  Cheat sheet on the right, event stream below.
- **sample-loader.html** — Operate surface (same register). The slot
  grid is the action, the message log is the feedback.

### Files that informed the mocks

- `../CLAUDE.md` — for current port state (8 verified components, mixer
  not yet wired, tilt sensor deferred)
- `../patchers/mapping.pd` — confirmed `y=7, slot=x, (7,0)=stopall`
- `../patchers/file_poly.pd` — confirmed 8 slots × 4 voices, round-robin
- `../abstractions/master.pd` — confirmed tanh soft-clip, RMS meter in dB
  full-scale 100 (the fake meter in the sample loader uses the same range)
- `../mlrv.pd` — confirmed the loadbang seed (`load 0 demo-tone-0.wav`,
  `load 1 demo-tone-1.wav`) which is what the browser mocks mirror

### What's deferred

Things that would be next iterations on these mocks, in rough priority:

- Real Pd ↔ browser bridge. The most direct path is a small Python
  service using `liblo` to relay OSC between `serialosc.pd`'s existing
  outlets and a WebSocket to the browser. With that, the virtual grid
  becomes a real second surface for the running instrument.
- Web Audio playback in the sample loader. Decoded buffers are already
  in memory; an `AudioBufferSourceNode` per voice with the right
  `playbackRate` gives the same `rate` parameter the Pd side uses.
- Pattern sequencing UI — `CLAUDE.md` mentions this as "not started"
  on the Pd side. A pattern grid is a natural browser surface for it.
- Tilt sensor visualization — `serialosc.pd` exposes `outlet 2` for
  tilt, but nothing reads it yet on the Pd side. The browser grid
  could show tilt as a glowing dot over the cells.
- Drag-and-drop reorder for slots.
- Light/dark theme variants. The current palette is dark-only by
  intent — the monome hardware is dark, so the whole site is dark.

---

## File map

```
frontends/
├── index.html              landing
├── patch-graph.html        Pd source visualizer
├── virtual-grid.html       8×8 clickable grid
├── sample-loader.html      drag-drop WAV → slot
├── assets/
│   ├── site.css            shared CSS (tokens, components, grid hardware palette)
│   ├── site.js             shared JS (grid builder, log helper, Pd-object describer)
│   └── pd-parser.js        .pd file parser + SVG renderer
├── screenshots/            Cap screenshots of the rendered pages
│   ├── 01-landing.png
│   ├── 02-patch-graph.png
│   ├── 03-virtual-grid.png
│   ├── 04-sample-loader.png
│   ├── 05-virtual-grid-active.png
│   └── 06-patch-graph-inspect.png
└── README.md               this file
```

No build artifacts, no `node_modules`, no generated files. Delete
`screenshots/` and the rest still runs.
