#!/usr/bin/env python3
"""Minimal serialosc daemon + fake grid device, pure stdlib.

Headless end-to-end test fixture for mlrv-pd/patchers/serialosc.pd. Implements
just enough of the wire protocol (monome serialosc OSC reference) to exercise:
  - discovery: /serialosc/list + /serialosc/notify sent to the daemon on 12002
  - device reply: /serialosc/device <id> <type> <port> back to the app's port
  - handshake: /sys/port + /sys/prefix received at the fake device's port
  - grid round trip: /monome/grid/key events sent back to the app's port

Not a real monome/serialosc: no serial hardware, no add/remove lifecycle, no
/sys/info. It is faithful on the bytes that this port's serialosc.pd uses.

Run with no args; logs one line per wire event to stdout (flush=True).
"""

import socket
import struct
import sys
import threading

DAEMON_PORT = 12002          # where the serialosc daemon listens
DEVICE_PORT = 40921          # fake device "own" port, advertised in replies
DEVICE_ID = "m0000-0000"
DEVICE_TYPE = "grid"
PREFIX = "/monome"           # prefix we expect serialosc.pd to send

log_lock = threading.Lock()


def log(tag, msg):
    with log_lock:
        print(f"{tag} {msg}", flush=True)


def pad(s):
    # OSC strings are null-terminated and padded to a 4-byte boundary, with
    # at least one terminator byte even when len(s) is already a multiple of
    # 4 (that case needs a full extra 4 bytes, not zero -- Python's -n % 4
    # gives 0 there, which silently drops the terminator and misaligns
    # everything that follows).
    return s.encode() + b"\0" * (4 - len(s) % 4)


def osc_msg(addr, types, *args):
    """Encode an OSC message. types is a string like 'ssi'; args are the
    payload values (str -> string, int -> int32)."""
    out = pad(addr) + pad("," + types)
    for t, a in zip(types, args):
        if t == "s":
            out += pad(a)
        elif t == "i":
            out += struct.pack(">i", int(a))
        elif t == "f":
            out += struct.pack(">f", float(a))
        else:
            raise ValueError(f"unsupported type tag {t}")
    return out


def osc_decode(data):
    """Decode an OSC message. Returns (address, [(type, value), ...])."""
    def take_string(buf, off):
        end = buf.index(b"\0", off)
        return buf[off:end].decode(), (end + 4) & ~3
    addr, i = take_string(data, 0)
    types, i = take_string(data, i)
    args = []
    for t in types[1:]:  # skip leading ','
        if t == "s":
            v, i = take_string(data, i)
        elif t == "i":
            v = struct.unpack(">i", data[i:i + 4])[0]
            i += 4
        elif t == "f":
            v = struct.unpack(">f", data[i:i + 4])[0]
            i += 4
        else:
            raise ValueError(f"unsupported tag {t}")
        args.append((t, v))
    return addr, args


def int_of(v):
    """Accept OSC int or float for port numbers (Pd sends floats)."""
    return int(round(v[1]))


def daemon(ready):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", DAEMON_PORT))
    ready.set()
    while True:
        data, peer = s.recvfrom(65536)
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
        else:
            log("DAEMON", f"ignored {addr}")


def device(app_port, prefix):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", DEVICE_PORT))
    while app_port[0] is None or prefix[0] is None:
        data, peer = s.recvfrom(65536)
        try:
            addr, args = osc_decode(data)
        except Exception as e:  # noqa: BLE001
            log("DEVICE", f"undecodable from {peer}: {e}")
            continue
        if addr == "/sys/port":
            app_port[0] = int_of(args[0])
            log("DEVICE", f"/sys/port {app_port[0]}")
        elif addr == "/sys/prefix":
            prefix[0] = args[0][1]
            log("DEVICE", f"/sys/prefix {prefix[0]}")
        else:
            log("DEVICE", f"ignored {addr}")
    # Handshake complete: send grid key events back at the app's port.
    for x, y, state in ((2, 3, 1), (1, 0, 0)):
        key = osc_msg(f"{prefix[0]}/grid/key", "iii", x, y, state)
        s.sendto(key, ("127.0.0.1", app_port[0]))
        log("DEVICE", f"sent {prefix[0]}/grid/key {x} {y} {state} -> {app_port[0]}")


def main():
    ready = threading.Event()
    t = threading.Thread(target=daemon, args=(ready,), daemon=True)
    t.start()
    ready.wait()
    app_port = [None]
    prefix = [None]
    d = threading.Thread(target=device, args=(app_port, prefix), daemon=True)
    d.start()
    while not d.is_alive():
        pass
    log("FAKE", f"up: daemon on {DAEMON_PORT}, device {DEVICE_ID} {DEVICE_TYPE} on {DEVICE_PORT}")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    import time
    main()