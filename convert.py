import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SRC = Path(os.environ["SRC"]).expanduser()
OUT = Path(os.environ["OUT"]).expanduser()
OUT.mkdir(parents=True, exist_ok=True)

TMP_DIR = SRC / ".tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(TMP_DIR)

CHUNK_SIZE = 4 * 1024 * 1024  # 4 MiB


def concat_files(paths: list[Path], output: Path) -> None:
    """Concatenate files without loading them into RAM."""
    with output.open("wb") as out:
        for path in paths:
            with path.open("rb") as src:
                shutil.copyfileobj(src, out, CHUNK_SIZE)


def stream_type(path: Path) -> str | None:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0", str(path),
        ],
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    return value or None


def natural_key(path: Path) -> tuple:
    name = path.name
    digits = "".join(ch if ch.isdigit() else " " for ch in name).split()
    return (name, [int(x) for x in digits])


def convert_recording(folder: Path) -> bool:
    mpd = folder / "session.mpd"
    if not mpd.exists():
        return False

    name = folder.name
    destination = OUT / f"{name}.mp4"

    if destination.exists():
        print(f"Skipping existing: {name}")
        return True

    inits = sorted(folder.glob("*init*.m4s"))
    if not inits:
        print(f"No init segment: {name}")
        return False

    video = None
    audio = None

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)

        for init in inits:
            stream_id = init.name.removeprefix("init").removesuffix(".m4s")

            chunks = sorted(
                [
                    p for p in folder.glob(f"*{stream_id}*.m4s")
                    if "init" not in p.name
                ],
                key=natural_key,
            )

            if not chunks:
                print(f"No fragments for stream {stream_id}: {name}")
                continue

            rebuilt = tmpdir / f"stream{stream_id}.mp4"
            concat_files([init, *chunks], rebuilt)

            if stream_type(rebuilt) == "video":
                video = rebuilt
            else:
                audio = rebuilt

        if video is None:
            print(f"No video stream found: {name}")
            return False

        command = ["nice", "-n", "19", "ffmpeg", "-nostdin", "-n",
                   "-threads", "1"]

        if audio is not None:
            command += ["-i", str(video), "-i", str(audio),
                        "-map", "0:v:0", "-map", "1:a:0?"]
        else:
            command += ["-i", str(video), "-map", "0:v:0"]

        command += [
            "-c", "copy",
            "-movflags", "+faststart",
            str(destination),
        ]

        result = subprocess.run(command)
        if result.returncode != 0:
            print(f"FFmpeg failed: {name}")
            destination.unlink(missing_ok=True)
            return False

    print(f"Converted: {name}")
    return True


def main() -> None:
    folders = sorted(
        (p.parent for p in SRC.rglob("session.mpd")),
        key=lambda p: p.name,
    )

    print(f"Found {len(folders)} recordings")

    for folder in folders:
        try:
            convert_recording(folder)
        except Exception as exc:
            print(f"Error converting {folder.name}: {exc}")


if __name__ == "__main__":
    main()