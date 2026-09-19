# .pd file builders

`pdgen.py` is a minimal `.pd` file generator: define objects with symbolic
Python references, connect them by reference, and it computes the numeric
`#X connect` indices for you. It exists specifically to make CLAUDE.md
gotcha #7 (manually counting object indices in a saved `.pd` file, and
getting it wrong when a new object is inserted anywhere but the end)
structurally impossible instead of merely documented against — that bug
class hit this port at least four separate times before this tool existed.

`build_mixer.py` and `build_test_mixer.py` are the generators for
`mlrv-pd/abstractions/mixer.pd` and `mlrv-pd/tests/test_mixer.pd`
respectively. `build_pong.py` generates `mlrv-pd/patchers/pong.pd`
(the 8x8 grid Pong game, ~190 objects -- hand-tracking indices at that
size is exactly the failure mode this tooling exists to prevent) and
`build_test_pong.py` generates its deterministic test patch
`mlrv-pd/tests/test_pong.pd`. `build_glow.py` / `build_test_glow.py` do the
same for the tilt light-toy (`mlrv-pd/patchers/glow.pd`, `run_glow_test.sh`),
and `build_tiltvis.py` / `build_test_tiltvis.py` for the gyroscope
visualizer (`mlrv-pd/patchers/tiltvis.pd`, `run_tiltvis_test.sh`). Run them from this directory:

```sh
cd mlrv-pd/tests/builders
python3 build_mixer.py
python3 build_test_mixer.py
```

They overwrite their target files unconditionally. If you want to add a
similar builder for a future abstraction or test patch, `pdgen.py`'s
`Patch` class (`obj`/`msg`/`text`/`connect`/`timeline`) is the whole API —
see either existing builder for the pattern, or `CLAUDE.md` gotcha #7 for
why this exists at all.

Not every `.pd` file in this repo was built this way — most of the
earlier, smaller abstractions were still hand-written directly (and
carefully re-verified per gotcha #7's discipline). Use a builder when a
file's object count makes manual index-tracking genuinely risky (roughly:
more than ~15-20 objects), not as a blanket rule.
