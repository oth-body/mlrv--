#!/usr/bin/env python3
"""Generate a small deterministic WAV fixture for play_loop~ testing.

Pure stdlib, no dependencies. Writes a mono 16-bit 44100Hz WAV whose
samples are a linear ramp from -peak to +peak -- deliberately not a sine
wave, so reading back any position gives a value you can predict by hand
(position i should read approximately -peak + 2*peak*i/(N-1)), letting a
test assert on exact sample content rather than just "is it non-silent."

Usage: python3 gen_test_wav.py <output.wav> <n_samples> [mode] [peak]

`mode` is "ramp" (default) or "const" (all samples = +peak, useful as a
flat reference signal that must not move). `peak` defaults to 16000.
Two-argument calls are unchanged -- the existing play_loop~ audio test
relies on the default ramp/16000 behavior.
"""
import struct
import sys
import wave


def main():
    if len(sys.argv) not in (3, 4, 5):
        print("usage: gen_test_wav.py <output.wav> <n_samples> [ramp|const] [peak]",
              file=sys.stderr)
        sys.exit(1)

    out_path = sys.argv[1]
    n = int(sys.argv[2])
    mode = sys.argv[3] if len(sys.argv) >= 4 else "ramp"
    peak = int(sys.argv[4]) if len(sys.argv) >= 5 else 16000

    if mode not in ("ramp", "const"):
        print(f"mode must be 'ramp' or 'const', got '{mode}'", file=sys.stderr)
        sys.exit(1)

    with wave.open(out_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        frames = bytearray()
        for i in range(n):
            if mode == "const":
                v = peak
            else:
                v = round(-peak + 2 * peak * i / (n - 1)) if n > 1 else 0
            frames += struct.pack("<h", v)
        w.writeframes(bytes(frames))

    print(f"wrote {out_path}: {n} samples, mode={mode} peak={peak}, "
          "44100Hz mono 16-bit")


if __name__ == "__main__":
    main()
