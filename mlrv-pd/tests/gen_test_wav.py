#!/usr/bin/env python3
"""Generate a small deterministic WAV fixture for play_loop~ testing.

Pure stdlib, no dependencies. Writes a mono 16-bit 44100Hz WAV whose
samples are a linear ramp from -16000 to +16000 -- deliberately not a
sine wave, so reading back any position gives a value you can predict
by hand (position i should read approximately -16000 + 32000*i/(N-1)),
letting a test assert on exact sample content rather than just
"is it non-silent."

Usage: python3 gen_test_wav.py <output.wav> <n_samples>
"""
import struct
import sys
import wave


def main():
    if len(sys.argv) != 3:
        print("usage: gen_test_wav.py <output.wav> <n_samples>", file=sys.stderr)
        sys.exit(1)

    out_path = sys.argv[1]
    n = int(sys.argv[2])

    with wave.open(out_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        frames = bytearray()
        for i in range(n):
            v = round(-16000 + 32000 * i / (n - 1)) if n > 1 else 0
            frames += struct.pack("<h", v)
        w.writeframes(bytes(frames))

    print(f"wrote {out_path}: {n} samples, ramp -16000..16000, 44100Hz mono 16-bit")


if __name__ == "__main__":
    main()
