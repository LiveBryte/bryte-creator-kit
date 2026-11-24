# BryteMama Creator Kit

Turn your phone video into a BryteMama ad with Claude or Codex. The kit cuts pauses, adds a hook and captions, checks your words against the brand rules, and saves the finished video in **BryteMama Videos** on your Desktop.

## Set up in Codex

Open Codex in the ChatGPT desktop app on Windows or Mac. Start a local chat and paste this:

> I'm a BryteMama creator. Please install the BryteMama Creator Kit on this computer from https://github.com/LiveBryte/bryte-creator-kit.

If you pasted the GitHub link by itself and Codex asks what you want to do, reply **Install the BryteMama Creator Kit**. You can also paste the [full setup message](SETUP-PROMPT-CODEX.md).

Codex downloads the kit and runs setup. If it asks for approval, it will explain what it needs. The first setup includes a large download and can take a few minutes.

When setup is done, quit and reopen the desktop app. Start a new local Codex chat and type **check my kit**. If Codex needs help finding the kit, type **$bryte-video check my kit**.

Then drag in your phone video or tell Codex where you saved it. Say **make this ready to post**.

### For Codex

When a creator supplies this URL and asks for setup, follow [SETUP-PROMPT-CODEX.md](SETUP-PROMPT-CODEX.md). It covers fetching the source, choosing the installer and verifying the result. If the creator only supplied a URL, ask whether they want to install the kit before running the installer.

## Set up in Claude

Open [the Claude setup page](https://claude.ai/artifact/WdrMEeiSS5YATHu9RaXFtz) or copy [the Claude setup message](SETUP-PROMPT.md). Paste it into a new chat in the Claude desktop app's Code tab. After setup, restart Claude and type **check my kit**.

### For Claude

When a creator supplies this URL and asks for setup, follow [SETUP-PROMPT.md](SETUP-PROMPT.md). Run the installer for her operating system with `-Assistant Claude` (Windows) or `claude` (Mac). If the creator only supplied a URL, ask whether she wants to install the kit before running the installer.

## What's in the kit

- [Shared skill](skills/bryte-video/SKILL.md) and [brand rules](skills/bryte-video/references/brand-rules.md)
- [Talking head](skills/bryte-video/references/yap.md), [voiceover](skills/bryte-video/references/voiceover.md), and [silent montage](skills/bryte-video/references/montage.md) workflows
- [Windows installer](install/install.ps1) and [Mac installer](install/install.sh). Both set up the same editor with ffmpeg, whisper.cpp, Python, and the Montserrat fonts. Codex loads the shared skill through a link in its [personal skills folder](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills).

## Status

- **Claude**. All three video formats were previously tested on Windows 11.
- **Codex**. Earlier Windows pilot files include talking-head, voiceover, and silent montage exports. The shareable ZIP uses the included installer and downloads the video tools and transcription model as needed.
- **Mac**. The installer is available for a pilot on a real Mac. It needs an Apple-chip Mac (M1 or newer) on macOS 15 or newer, because that's where Homebrew ships ready-made video tools.
