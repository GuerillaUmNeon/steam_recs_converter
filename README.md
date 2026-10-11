# steam_recs_converter

Converts locally saved Steam recording sessions from fragmented DASH files (`session.mpd`, `init*.m4s`, and numbered `.m4s` chunks) into a single playable `.mp4` file.

## Requirements

- Python 3.10+
- FFmpeg and FFprobe available on your `PATH`
- A `.env` file in the repository root

## Setup

1. Install FFmpeg.

   ```bash
   # macOS
   brew install ffmpeg

   # Debian/Ubuntu
   sudo apt install ffmpeg
   ```

2. Install the Python dependency:

   ```bash
   pip install python-dotenv
   ```

3. Create a `.env` file next to `convert.py`:

   ```env
   SRC=/path/to/recordings
   OUT=/path/to/converted-videos
   ```

   - `SRC`: folder containing recording session folders.
   - `OUT`: folder where converted `.mp4` files will be written. It is created automatically if missing.

## Usage

```bash
python convert.py
```

The script scans `SRC` recursively for `session.mpd` files and converts each matching recording to:

```text
OUT/<recording-folder-name>.mp4
```

## How it works

- Finds every folder containing a `session.mpd`.
- Reassembles each DASH stream by concatenating its `init.m4s` and numbered media segments in natural order.
- Detects which rebuilt stream is video and which is audio using FFprobe.
- Remuxes the streams into MP4 with FFmpeg using stream copy, so it does not re-encode video.
- Uses `+faststart` so the resulting MP4 can begin playback before it is fully downloaded or copied.
- Skips recordings whose destination MP4 already exists.
- Uses temporary files inside `SRC/.tmp`.

## Notes

- Conversion is lossless because FFmpeg copies the existing audio and video streams rather than transcoding them.
- Recordings without video, an init segment, or usable fragments are skipped and reported in the console.
- FFmpeg is run with low CPU priority (`nice -n 19`) and one thread.
- If FFmpeg fails, any partially created destination file is removed.