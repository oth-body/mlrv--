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
    MASTER = p.obj(600, 200, "master")

    # --- control/LED chain ---
    p.connect(SERIALOSC, 1, MAPPING, 0)     # grid_key (x y state) -> mapping inlet0
    p.connect(FILE_POLY, 1, MAPPING, 1)     # info (loaded.../voice...) -> mapping inlet1
    p.connect(MAPPING, 0, FILE_POLY, 0)     # commands (play.../stopall) -> file_poly inlet0
    p.connect(MAPPING, 1, GRID, 0)          # LED (x y level) -> grid inlet0
    p.connect(GRID, 0, SERIALOSC, 1)        # grid outlet -> serialosc LED-control inlet1

    # master.pd's internal [receive~ fxin] has no matching [send~] until
    # mixer.pd (or an effect) is wired in -- silences the harmless but noisy
    # "no matching send" load-time error with an explicit silent placeholder.
    FXIN_STUB = p.obj(600, 320, "sig~ 0")
    FXIN_SEND = p.obj(600, 360, "send~ fxin")
    p.connect(FXIN_STUB, 0, FXIN_SEND, 0)

    return {
        "SERIALOSC": SERIALOSC,
        "GRID": GRID,
        "FILE_POLY": FILE_POLY,
        "MAPPING": MAPPING,
        "MASTER": MASTER,
    }
