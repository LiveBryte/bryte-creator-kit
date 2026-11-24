# BryteMama Creator Kit

Turns a creator's phone video into a finished, on-brand BryteMama ad inside Claude. Built only on free, shareable tools:
ffmpeg (video), whisper.cpp (transcription, MIT license), Python, and the Montserrat font (SIL Open Font License).
No Tesseract, no VideoDatabase or Content Tools, and no account keys inside.

## What a creator does
1. Pastes `SETUP-PROMPT.md` into a new Claude chat (desktop app, Code tab). Claude installs everything.
2. Restarts Claude and types "check my kit".
3. Drags in a video. Claude checks what she said against the brand rules, offers hooks, and saves the finished
   video to "BryteMama Videos" on her Desktop.

## What's in it
- `skills/bryte-video/SKILL.md` - how Claude walks her through each video
- `skills/bryte-video/references/yap.md`, `voiceover.md`, `montage.md` - the three formats
- `skills/bryte-video/references/brand-rules.md` - creator-safe brand and claim rules, plus disclosure (no prices,
  costs or internal numbers)
- `skills/bryte-video/scripts/bryte_edit.py` - the editor (cut pauses, hook, captions, remove lines)
- `install/install.ps1`, `install/install.sh` - Windows and Mac installers (everything lands in `~/.bryte-kit`)

## Status
- All three formats built and tested on Windows: talking-head yap, voiceover over b-roll, b-roll montage.
- Windows installer: tested on Windows 11. Mac installer: written, not yet tested on a Mac.
- Hosted at https://github.com/LiveBryte/bryte-creator-kit. Creator setup page: `paste/setup.html`.
