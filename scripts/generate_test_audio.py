import argparse
import math
import struct
import wave
from pathlib import Path


def generate_long_test_audio(output_path: Path, duration_min: int, sample_rate: int) -> dict:
    duration_sec = duration_min * 60
    amplitude = 12000
    chunk_sec = 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate a deterministic speech-like waveform with pauses for segmentation tests.
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)

        total_chunks = duration_sec // chunk_sec
        for c in range(total_chunks):
            freq = 180 + (c % 9) * 28
            frames = bytearray()
            for i in range(sample_rate * chunk_sec):
                t = i / sample_rate
                if c % 7 == 6 and i < sample_rate // 7:
                    sample = 0
                else:
                    carrier = math.sin(2 * math.pi * freq * t)
                    harmonic = 0.35 * math.sin(2 * math.pi * (freq * 2.2) * t)
                    envelope = 0.55 + 0.45 * math.sin(2 * math.pi * 2.8 * t)
                    sample = int(amplitude * envelope * (carrier + harmonic) / 1.35)
                frames += struct.pack("<h", max(-32768, min(32767, sample)))
            wf.writeframes(frames)

    return {
        "output_path": str(output_path),
        "duration_sec": duration_sec,
        "sample_rate": sample_rate,
        "size_bytes": output_path.stat().st_size,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate long test audio into test_audio directory")
    parser.add_argument("--output", default="test_audio/long_meeting_test_20min.wav", help="Output wav path")
    parser.add_argument("--duration-min", type=int, default=20, help="Audio duration in minutes")
    parser.add_argument("--sample-rate", type=int, default=16000, help="Sample rate")
    args = parser.parse_args()

    result = generate_long_test_audio(Path(args.output), args.duration_min, args.sample_rate)
    print(result)


if __name__ == "__main__":
    main()
