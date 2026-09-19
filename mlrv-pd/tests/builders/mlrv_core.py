"""Shared top-level wiring for mlrv.pd, used by both build_mlrv.py (the
production patch) and build_test_mlrv.py (its test harness). mlrv.pd
can't be instantiated as a sub-object the way an abstraction can (it's
the entry-point file, not something you'd write `[mlrv]` for), so a
test harness necessarily re-creates the same top-level wiring rather
than composing around a reusable object -- this module exists so that
wiring is written once and shared, not duplicated by hand in two
places that could silently drift apart.
"""


def build_core(p):
    """Instantiates the 8-component chain into patch p and wires it.
    Returns a dict of the key object indices callers need to attach
    fixtures, taps, or bootstrap messages to."""
    SERIALOSC = p.obj(20, 200, "serialosc 8000 /monome")
    GRID = p.obj(20, 260, "grid")
    FILE_POLY = p.obj(300, 200, "file_poly")
    MAPPING = p.obj(300, 320, "mapping")
    MIXER = p.obj(460, 200, "mixer")
    MASTER = p.obj(600, 200, "master")

    # --- control/LED chain ---
    p.connect(SERIALOSC, 1, MAPPING, 0)     # grid_key (x y state) -> mapping inlet0
    p.connect(FILE_POLY, 1, MAPPING, 1)     # info (loaded.../voice...) -> mapping inlet1
    p.connect(MAPPING, 0, FILE_POLY, 0)     # commands (play.../stopall) -> file_poly inlet0
    p.connect(MAPPING, 1, GRID, 0)          # LED (x y level) -> grid inlet0
    p.connect(GRID, 0, SERIALOSC, 1)        # grid outlet -> serialosc LED-control inlet1

    # --- audio chain: per-voice file_poly outlets 2-5 -> mixer inlets 0-3 -> master ---
    p.connect(FILE_POLY, 2, MIXER, 0)
    p.connect(FILE_POLY, 3, MIXER, 1)
    p.connect(FILE_POLY, 4, MIXER, 2)
    p.connect(FILE_POLY, 5, MIXER, 3)
    p.connect(MIXER, 0, MASTER, 0)          # mixer dry sum -> master

    # Effects between mixer's fxout (per-voice wet send) and master's
    # fxin (return, summed pre-limiter) -- replaces the old sig~0/
    # send~fxin silencer stub. Each effect's [receive~ fxout] reads
    # mixer's real send~ fxout (multiple receivers on one bus is safe);
    # each effect's real [outlet~] is summed here with an ordinary [+~]
    # before the ONE real [send~ fxin] -- NOT a second bus per effect,
    # since two effects each with their own internal send~ fxin would
    # collide exactly like gotcha #31 describes (see build_delay_fx.py's
    # docstring for the full reasoning behind this outlet~-and-sum
    # design, which replaced an earlier bus-per-effect draft).
    DELAY = p.obj(460, 320, "delay_fx~")
    REVERB = p.obj(600, 320, "reverb_fx~")
    FX_SUM = p.obj(460, 360, "+~")
    FX_SEND = p.obj(460, 400, "send~ fxin")
    p.connect(DELAY, 0, FX_SUM, 0)
    p.connect(REVERB, 0, FX_SUM, 1)
    p.connect(FX_SUM, 0, FX_SEND, 0)

    return {
        "SERIALOSC": SERIALOSC,
        "GRID": GRID,
        "FILE_POLY": FILE_POLY,
        "MAPPING": MAPPING,
        "MIXER": MIXER,
        "MASTER": MASTER,
        "DELAY": DELAY,
        "REVERB": REVERB,
    }
