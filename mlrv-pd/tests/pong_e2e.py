#!/usr/bin/env python3
"""Pong end-to-end fixture: fake serialosc daemon + fake grid device that,
after the handshake, sends scripted key presses AND captures LED output.

Unlike fake_serialosc.py (handshake-only fixture shared by other suites),
this one keeps listening on the fake device port after the handshake and
logs every incoming OSC message -- proving the full loop
key -> pong -> grid -> serialosc -> device carries real LED triples.

Stdlib only. Logs one line per wire event to stdout (flush=True).
"""
import socket
import struct
import sys
import threading
import time

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from fake_serialosc import (  # noqa: E402
    DAEMON_PORT, DEVICE_PORT, DEVICE_ID, DEVICE_TYPE, PREFIX,
    osc_msg, osc_decode, int_of, log,
)

KEYS = ((0, 3, 1), (0, 3, 0), (7, 4, 1), (7, 4, 0))
CAPTURE_SECS = 5.0


def daemon(app_keys_done):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", DAEMON_PORT))
    while not app_keys_done.is_set():
        s.settimeout(0.5)
        try:
            data, peer = s.recvfrom(65536)
        except socket.timeout:
            continue
        try:
            addr, args = osc_decode(data)
        except Exception as e:  # noqa: BLE001
            log("DAEMON", f"undecodable from {peer}: {e}")
            continue
        if addr in ("/serialosc/list", "/serialosc/notify"):
            host = args[0][1]
            port = int_of(args[1])
            log("DAEMON", f"{addr} host={host} port={port}")
            reply = osc_msg("/serialosc/device", "ssi",
                            DEVICE_ID, DEVICE_TYPE, DEVICE_PORT)
            s.sendto(reply, (host, port))


def device(app_keys_done):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", DEVICE_PORT))
    app_port, prefix = None, None
    s.settimeout(0.5)
    while app_port is None or prefix is None:
        try:
            data, peer = s.recvfrom(65536)
        except socket.timeout:
            continue
        try:
            addr, args = osc_decode(data)
        except Exception as e:  # noqa: BLE001
            log("DEVICE", f"undecodable from {peer}: {e}")
            continue
        if addr == "/sys/port":
            app_port = int_of(args[0])
            log("DEVICE", f"/sys/port {app_port}")
        elif addr == "/sys/prefix":
            prefix = args[0][1]
            log("DEVICE", f"/sys/prefix {prefix}")
        else:
            log("DEVICE", f"ignored {addr}")
    for x, y, state in KEYS:
        key = osc_msg(f"{prefix}/grid/key", "iii", x, y, state)
        s.sendto(key, ("127.0.0.1", app_port))
        log("DEVICE", f"sent {prefix}/grid/key {x} {y} {state} -> {app_port}")
        time.sleep(0.15)
    # capture LED output until the deadline
    deadline = time.time() + CAPTURE_SECS
    while time.time() < deadline:
        s.settimeout(max(0.1, deadline - time.time()))
        try:
            data, peer = s.recvfrom(65536)
        except socket.timeout:
            break
        try:
            addr, args = osc_decode(data)
        except Exception as e:  # noqa: BLE001
            log("DEVICE", f"undecodable from {peer}: {e}")
            continue
        vals = " ".join(str(v) for _, v in args)
        log("DEVICE", f"got {addr} {vals}")
    app_keys_done.set()


def main():
    done = threading.Event()
    threading.Thread(target=daemon, args=(done,), daemon=True).start()
    threading.Thread(target=device, args=(done,), daemon=True).start()
    log("FAKE", f"up: daemon on {DAEMON_PORT}, device on {DEVICE_PORT}")
    done.wait(timeout=CAPTURE_SECS + 10)


if __name__ == "__main__":
    main()
