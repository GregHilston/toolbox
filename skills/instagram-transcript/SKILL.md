---
name: instagram-transcript
description: Transcribe an Instagram reel and get its author, date and caption as JSON, using speech-to-text on moria. Use when given an instagram.com reel or post URL and you need what is said in the video, to summarize, clip or quote it.
---

# Instagram Transcript

Reels have no captions to download, so the script downloads the audio and
runs Parakeet speech-to-text on moria over ssh. It takes a few seconds and
needs moria awake.

## Usage

One command, already on `PATH`. Run it in your shell (the `terminal` tool in
Hermes, Bash in Claude Code, `bash` in pi) exactly as shown: no `python3` in
front and no directory.

```bash
instagram-transcript.py "<instagram_url>"
```

Do not fetch the page with `curl` or web search instead: Instagram serves a
login wall with no transcript.

## Output

```json
{
  "author": "ayoships",
  "published": "2026-10-13",
  "caption": "the post's caption text",
  "transcript": "everything said in the video, as one string"
}
```

On failure it exits non-zero and says why on stderr, usually that moria is
asleep. Don't run Whisper locally as a fallback; it takes minutes and uses a
lot of RAM.
