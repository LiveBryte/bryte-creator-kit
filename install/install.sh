#!/usr/bin/env bash
# BryteMama Creator Kit installer for Mac.
# Sets up the video tools and adds the kit to Claude. Safe to run again: every step skips itself when done.
#
#   bash install.sh
#
# Uses only free tools: ffmpeg (video), whisper.cpp (transcription), Python, installed with Homebrew.
# Everything the kit adds lives in ~/.bryte-kit.
set -uo pipefail

KIT_ZIP="${KIT_ZIP:-https://github.com/LiveBryte/bryte-creator-kit/archive/refs/heads/main.zip}"
HOME2="$HOME/.bryte-kit"
KIT_DIR="$HOME2/kit"
MODEL_DIR="$HOME2/models"
MODEL="ggml-large-v3-turbo-q5_0.bin"
MODEL_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$MODEL"

ok()   { echo "  READY  $1"; }
fail() { echo "STOPPED: $1"; exit 1; }
has()  { command -v "$1" >/dev/null 2>&1; }

[[ "$(uname -s)" == Darwin ]] || fail "This installer is for Mac. On Windows, use install.ps1."
mkdir -p "$HOME2" "$MODEL_DIR"

# 1. The kit itself ----------------------------------------------------------------
echo "1. The BryteMama kit"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$HERE/.claude-plugin/marketplace.json" ]]; then
  if [[ "$HERE" != "$KIT_DIR" ]]; then rm -rf "$KIT_DIR"; cp -R "$HERE" "$KIT_DIR"; fi
else
  TMP="$(mktemp -d)"
  curl -fsSL -o "$TMP/kit.zip" "$KIT_ZIP" || fail "Couldn't download the kit. Check the internet connection and run the installer again."
  (cd "$TMP" && unzip -q kit.zip)
  SRC="$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -1)"
  rm -rf "$KIT_DIR"; mv "$SRC" "$KIT_DIR"; rm -rf "$TMP"
fi
ok "kit in $KIT_DIR"

# 2. Homebrew (asks for the Mac password once) -------------------------------------
echo "2. Homebrew"
for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do [[ -x "$b" ]] && eval "$("$b" shellenv)"; done
if ! has brew; then
  # Claude runs this without a terminal, so sudo can't prompt in text. Homebrew's installer uses SUDO_ASKPASS
  # when it's set, so the password is asked for in a normal Mac window instead.
  ASK="$HOME2/askpass.sh"
  cat > "$ASK" <<'ASKEOF'
#!/bin/bash
/usr/bin/osascript -e 'text returned of (display dialog "The BryteMama Creator Kit needs your Mac password to install its video tools." default answer "" with hidden answer with title "BryteMama Creator Kit" with icon caution)'
ASKEOF
  chmod 700 "$ASK"
  export SUDO_ASKPASS="$ASK"
  echo "  A window will ask for your Mac password. Type it and click OK."
  NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" \
    || { rm -f "$ASK"; fail "Homebrew didn't finish installing. Run the installer again."; }
  rm -f "$ASK"
  for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do [[ -x "$b" ]] && eval "$("$b" shellenv)"; done
fi
has brew || fail "Homebrew didn't finish installing. Run the installer again."
ok "Homebrew"

# 3. ffmpeg, Whisper, Python ------------------------------------------------------
echo "3. Video tools, transcription and Python"
for pkg in ffmpeg whisper-cpp python@3.12; do
  brew list "$pkg" >/dev/null 2>&1 || brew install "$pkg" || fail "Couldn't install $pkg. Run the installer again."
done
PY="$(brew --prefix python@3.12)/bin/python3.12"
[[ -x "$PY" ]] || PY="$(command -v python3.12 || command -v python3)"
"$PY" -c 'import sys; sys.exit(sys.version_info < (3, 8))' || fail "Python didn't finish installing. Run the installer again."
printf '%s' "$PY" > "$HOME2/python-path.txt"
ok "ffmpeg, Whisper, Python"

# 4. Add the kit to Claude ------------------------------------------------------------
echo "4. Adding the kit to Claude"
if ! has claude; then
  for c in "$HOME/.local/bin/claude" "$HOME/.claude/local/claude" \
           $(find "$HOME/Library/Application Support/Claude" -name claude -type f -perm -u+x 2>/dev/null | head -1); do
    [[ -x "$c" ]] && { PATH="$(dirname "$c"):$PATH"; break; }
  done
fi
has claude || fail "Couldn't find Claude on this Mac. Install the Claude desktop app, then run this again."
if claude plugin marketplace list 2>/dev/null | grep -q bryte-creator-kit; then
  claude plugin marketplace remove bryte-creator-kit >/dev/null 2>&1
fi
claude plugin marketplace add "$KIT_DIR" || fail "Couldn't add the kit to Claude. Run the installer again."
if claude plugin list 2>/dev/null | grep -q 'bryte-video@bryte-creator-kit'; then
  claude plugin update bryte-video@bryte-creator-kit --scope user
else
  claude plugin install bryte-video@bryte-creator-kit --scope user
fi || fail "Couldn't turn the kit on in Claude. Run the installer again."
ok "kit added to Claude"

# 5. Transcription model, last: the biggest download (about 550 MB) ----------------
echo "5. Transcription model (about 550 MB, the slow part)"
if [[ ! -f "$MODEL_DIR/$MODEL" ]]; then
  curl -fL -C - -o "$MODEL_DIR/$MODEL.part" "$MODEL_URL" \
    || fail "The model download stopped partway. Run the installer again; it picks up where it left off."
  mv "$MODEL_DIR/$MODEL.part" "$MODEL_DIR/$MODEL"
fi
ok "transcription model"

# 6. Final check -------------------------------------------------------------------
echo "6. Final check"
"$PY" -I "$KIT_DIR/skills/bryte-video/scripts/bryte_edit.py" check || fail "Something is still missing. Run the installer again."
echo
echo "DONE. Quit Claude, open it again, start a new chat and type: check my kit"
