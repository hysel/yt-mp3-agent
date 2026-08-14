# yt-mp3-agent

A Python command-line tool that downloads entire YouTube or YouTube Music channels — or individual playlists — as MP3 files, with embedded album art, artist tags, parallel downloads, and smart duplicate skipping. Includes an optional PowerShell launcher that checks all dependencies before running.

> 🤖 Built entirely through a conversation with [Claude.ai](https://claude.ai) by Anthropic — no code was written manually.

---

## Features

- 🎵 Downloads full YouTube and YouTube Music channels, or any playlist, as MP3
- 🖼️ Embeds video thumbnail as album art
- 🏷️ Sets channel name as the artist ID3 tag
- ⚡ Parallel multi-threaded downloads (default: 5 concurrent)
- ⏭️ Skips already-downloaded videos via an archive file
- 🚦 `--skip-existing` flag to auto-skip on-disk conflicts with no prompts — ideal for unattended/scheduled runs
- 🔁 Interactive overwrite/skip prompt when `--skip-existing` isn't used
- ⏱️ Optional duration filter — skip videos longer than X minutes
- 📋 Supports a text file with multiple channel or playlist URLs
- 📼 Normalizes `/watch?v=...&list=...` links into full playlist downloads automatically
- 📦 Auto-downloads `ffmpeg` on Windows if not installed
- 📊 Progress bars per file and overall
- 🪟 Optional PowerShell launcher (`Run-YtMp3Agent.ps1`) that verifies Python, pip packages, ffmpeg, and a JS runtime before running, and defaults to `channels.txt` + `--skip-existing` when run with no arguments

---

## Requirements

**Install Python dependencies:**

```
pip install -r requirements.txt
```

Or manually:

```
pip install -U "yt-dlp[default]" requests tqdm mutagen pillow
```

**ffmpeg:**

- Windows: auto-downloaded on first run
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt install ffmpeg`

**JavaScript runtime** (required by yt-dlp for YouTube):

- Recommended: [Deno](https://deno.com) — enabled by default
- Alternative: [Node.js 20+](https://nodejs.org)

**PO Token provider (recommended):**

YouTube increasingly requires a Proof-of-Origin token to authorize the actual media download, even when video info can still be fetched. If you see `HTTP Error 403: Forbidden` on specific videos, install a token provider:

```
pip install -U bgutil-ytdlp-pot-provider
git clone --single-branch --branch 1.3.1 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git ~/bgutil-ytdlp-pot-provider
cd ~/bgutil-ytdlp-pot-provider/server
npm install
npx tsc
```

yt-dlp auto-detects the provider once it's in this location — no extra flags needed. Verify it's active with:

```
yt-dlp -v "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 2>&1 | grep pot
```

---

## Usage

```
# Single channel or playlist
python yt-mp3-agent.py <url> <destination> [options]

# Multiple channels/playlists from a file
python yt-mp3-agent.py --url-file channels.txt <destination> [options]
```

### Windows: `Run-YtMp3Agent.ps1`

A PowerShell wrapper is included that checks Python, required pip packages, ffmpeg, and a JS runtime before running, and offers to install anything missing.

```powershell
# Run with your own arguments (forwarded as-is to the Python script)
.\Run-YtMp3Agent.ps1 <url> <destination> [options]

# Run with no arguments: uses channels.txt + --skip-existing automatically
.\Run-YtMp3Agent.ps1
```

The no-argument default reads `channels.txt` from the script's own folder and downloads into that same folder, skipping anything already downloaded with no prompts — useful for re-running periodically to pick up new uploads.

First-time setup on Windows may require:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
Unblock-File .\Run-YtMp3Agent.ps1
```

---

## Examples

```
# Download an entire channel
python yt-mp3-agent.py https://www.youtube.com/@mkbhd C:\Music

# YouTube Music channel
python yt-mp3-agent.py https://music.youtube.com/channel/UCxxxx C:\Music

# A specific playlist (watch?v=...&list=... links work too)
python yt-mp3-agent.py "https://www.youtube.com/playlist?list=PLxxxxxxxx" C:\Music

# 20 most recent videos, 320 kbps, 8 parallel threads
python yt-mp3-agent.py https://www.youtube.com/@lexfridman C:\Music -n 20 -q 320 -w 8

# Skip videos longer than 10 minutes
python yt-mp3-agent.py https://www.youtube.com/@mkbhd C:\Music --max-duration 10

# Multiple channels from a file, auto-skip existing files (no prompts)
python yt-mp3-agent.py --url-file channels.txt C:\Music --skip-existing
```

**`channels.txt` format:**

```
# Lines starting with # are ignored
https://www.youtube.com/@mkbhd
https://www.youtube.com/@lexfridman
https://music.youtube.com/channel/UCxxxx
https://www.youtube.com/playlist?list=PLxxxxxxxx
```

---

## Output Structure

```
<destination>/
└── <Channel or Playlist Name>/
    ├── Video Title.mp3
    ├── Another Video.mp3
    └── .archive.txt          (hidden — tracks downloaded video IDs)
```

For playlists without a single clear uploader (e.g. curated/multi-artist playlists), the folder is named after the playlist title instead of a channel name.

---

## Options

| Flag                 | Short | Description                                        | Default |
| -------------------- | ----- | --------------------------------------------------- | ------- |
| `--url-file FILE`    | `-f`  | Text file with one channel/playlist URL per line     | —       |
| `--workers N`        | `-w`  | Parallel download threads                            | `5`     |
| `--limit N`          | `-n`  | Max videos to download                               | all     |
| `--quality KBPS`     | `-q`  | MP3 bitrate: 128 / 192 / 256 / 320                    | `320`   |
| `--max-duration MIN` | `-d`  | Skip videos longer than N minutes                     | —       |
| `--skip-existing`    | `-y`  | Auto-skip files already on disk, no interactive prompt| off     |

Already-downloaded videos tracked in `.archive.txt` are always skipped regardless of `--skip-existing` — that flag only affects files present on disk but missing from the archive (e.g. downloaded outside this tool).

Workers above ~8–10 increase the risk of YouTube rate-limiting (`403` errors). If you hit 403s, lower `--workers` before troubleshooting further.

### Metadata Options

All metadata flags are optional and additive. The only automatic tags are **artist** (channel name) and **cover art** (thumbnail).

| Flag                       | Description                                                                   | Default |
| -------------------------- | ------------------------------------------------------------------------------ | ------- |
| `--genre GENRE`            | Set the genre ID3 tag                                                          | not set |
| `--album ALBUM`            | Set the album ID3 tag                                                          | not set |
| `--year`                   | Embed the upload year as the year tag                                          | off     |
| `--comment-url`            | Embed the YouTube video URL as the comment tag                                 | off     |
| `--track-numbers`          | Number tracks by position in the download queue                               | off     |
| `--strip-title`            | Clean YouTube noise from title tags: `(Official Video)`, `[HD]`, etc.         | off     |
| `--no-art`                 | Skip thumbnail embedding                                                       | off     |
| `--no-artist`              | Don't override the artist tag with the channel name                            | off     |
| `--description-as-comment` | Embed the video description as the comment tag (one extra API call per video)  | off     |

---

## Archive File

`.archive.txt` records the YouTube video ID of every completed download. On the next run, any ID already in this file is skipped automatically — even if you've renamed or moved the MP3.

- Delete a line → re-download that video next run
- Delete the file → treat everything as new (existing files on disk are then handled per `--skip-existing` / the interactive prompt)

---

## Playlist URLs

Any URL containing a `list=` parameter — including `/watch?v=...&list=...` links copied while a video is playing as part of a queue — is automatically normalized to the canonical `/playlist?list=...` form, so the full playlist downloads rather than just the single video. YouTube auto-generated "Mix"/radio playlists (IDs starting with `RD`) are left as single-video URLs, since those aren't fixed collections.

---

## Troubleshooting

**`HTTP Error 403: Forbidden`**
Usually a missing PO Token provider (see Requirements above) or too many concurrent workers. Try lowering `--workers` to 3–5, and confirm yt-dlp is up to date (`pip install -U "yt-dlp[default]"`).

**`This playlist type is unviewable`**
Common with YouTube Music channel URLs; the script auto-resolves these to their canonical `youtube.com` channel URL internally.

**PowerShell: "running scripts is disabled"**
Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then retry.

---

## How It Was Built

This script was built entirely through a conversation with **[Claude.ai](https://claude.ai)** by [Anthropic](https://www.anthropic.com) — no code was written by hand. The full feature set, including bug fixes and troubleshooting, was developed iteratively by describing requirements, reporting errors, and requesting improvements in plain language.

It's a practical example of using an AI assistant to build and maintain a real, production-ready command-line tool from scratch.

---

## License

MIT
