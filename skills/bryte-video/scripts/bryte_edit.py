"""BryteMama Creator Kit: the editing helper Claude runs for a creator.

Commands
  check                                  report whether ffmpeg, Whisper and the model are ready
  transcribe <video> <workdir>           write <workdir>/words.json (every word with its start and end time)
  yap <video> <workdir> [options]        cut every pause, add a text hook and captions, write the finished video

yap options
  --hook "text"          on-screen hook for the first seconds (keep it under ~10 words)
  --hook-seconds 3.0     how long the hook stays up
  --no-captions          skip captions (use when the clip already has captions burned in)
  --max-pause 0.25       pauses longer than this many seconds get cut
  --out path.mp4         where to save (default: <workdir>/<video name>-yap.mp4)
  --remove 61.2-64.9     drop a line she said (seconds from `sentences`); repeatable

  voiceover <voice> <workdir> --clips a.mp4 b.mov ... [--hook ..] [--face-first] [--no-captions] [--remove ..]
                                         her narration with pauses cut, b-roll changing every ~2-3 s at phrase
                                         starts, hook and captions. --face-first opens on her talking.
  montage <workdir> --clips a b c ... --text "..." [--text-middle] [--shot 1.2] [--length 12] [--music f]
                                         quick cuts, one text overlay the whole time; silent unless --music,
                                         so she adds a trending sound in the app

  sentences <video> <workdir>            numbered sentences with their start-end seconds
  frame <video> <workdir> --at 2         save one still (to see if captions are already burned in)

Only uses ffmpeg, whisper.cpp and Python's standard library.
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
HOME_KIT = Path.home() / ".bryte-kit"
MODEL = "ggml-large-v3-turbo-q5_0.bin"
FONT_DIR = KIT / "fonts"
FONT_CAP = "Montserrat ExtraBold"
FONT_HOOK = "Montserrat"

# The desktop app may launch without the shell profile that adds Homebrew.
if sys.platform == "darwin":
    brew_bins = [p for p in ("/opt/homebrew/bin", "/usr/local/bin") if Path(p).is_dir()]
    os.environ["PATH"] = os.pathsep.join([os.environ.get("PATH", ""), *brew_bins]).strip(os.pathsep)


# ---------------------------------------------------------------- tools
def find_whisper():
    found = shutil.which("whisper-cli")
    if found:
        return found
    exe = "whisper-cli.exe" if os.name == "nt" else "whisper-cli"
    places = [HOME_KIT / "whisper" / "bin" / exe]
    if os.name == "nt":
        places.append(Path(os.environ.get("LOCALAPPDATA", "")) / "whisper.cpp" / "bin" / exe)
    for p in places:
        if p.is_file():
            return str(p)
    return None


def find_model():
    places = [HOME_KIT / "models" / MODEL]
    if os.name == "nt":
        places.append(Path(os.environ.get("LOCALAPPDATA", "")) / "whisper.cpp" / "models" / MODEL)
    places.append(Path.home() / ".local" / "share" / "whisper.cpp" / "models" / MODEL)
    for p in places:
        if p.is_file():
            return str(p)
    return None


def need(tool, value):
    if not value:
        sys.exit(f"MISSING: {tool}. Run the kit installer again.")
    return value


def run(cmd, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd)
    if r.returncode != 0:
        sys.exit("FAILED: " + " ".join(map(str, cmd[:3])) + "\n" + r.stderr[-2000:])
    return r.stdout


def probe(video):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=width,height:stream_side_data=rotation:format=duration", "-of", "json", video])
    d = json.loads(out)
    s = d["streams"][0]
    w, h = s["width"], s["height"]
    rot = 0
    for sd in s.get("side_data_list", []) or []:
        rot = int(sd.get("rotation", 0) or 0)
    if abs(rot) in (90, 270):
        w, h = h, w
    return w, h, float(d["format"]["duration"])


def is_hdr(video):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer",
               "-of", "csv=p=0", video]).strip()
    return out in ("arib-std-b67", "smpte2084")


def has_filters(*names):
    listing = run(["ffmpeg", "-hide_banner", "-filters"])
    return all(f" {n} " in listing for n in names)


# ---------------------------------------------------------------- transcribe
def fix_brand(words):
    """Whisper hears the brand as 'Bright Mama' / 'Brightmama'. Always write it BryteMama."""
    out = []
    for w in words:
        core = w["text"].rstrip(".,!?;:'s")
        tail = w["text"][len(core):]
        prev = out[-1]["text"].lower() if out else ""
        if core.lower() in ("mama", "mamma", "momma") and prev in ("bright", "bryte", "brite"):
            out[-1] = {"text": "BryteMama" + tail, "start": out[-1]["start"], "end": w["end"]}
            continue
        if core.lower() in ("brightmama", "brytemama", "britemama", "brightmamma"):
            w = dict(w, text="BryteMama" + tail)
        out.append(w)
    return out


def transcribe(video, workdir):
    workdir.mkdir(parents=True, exist_ok=True)
    whisper = need("Whisper", find_whisper())
    model = need("the transcription model", find_model())
    wav = workdir / "audio.wav"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-ar", "16000", "-ac", "1", str(wav)])
    # No --prompt: a vocabulary prompt made Whisper invent words and smear word timings (pauses vanished).
    # Brand spelling is fixed afterwards by fix_brand, and Claude proofreads words.json.
    run([whisper, "-m", model, "-f", str(wav), "-ml", "1", "-ojf", "-of", str(workdir / "whisper"), "-np"])
    raw = json.loads((workdir / "whisper.json").read_text(encoding="utf-8"))
    words = []
    for seg in raw["transcription"]:
        text = seg["text"]
        if not text.strip():
            continue
        start, end = seg["offsets"]["from"] / 1000, seg["offsets"]["to"] / 1000
        # Whisper splits some words into pieces; a piece with no leading space belongs to the word before it.
        if words and (not text.startswith(" ") or text.strip() in ".,!?;:%"):
            words[-1]["text"] += text.strip()
            words[-1]["end"] = end
        else:
            words.append({"text": text.strip(), "start": start, "end": end})
    words = fix_brand(words)
    (workdir / "words.json").write_text(json.dumps(words, indent=1), encoding="utf-8")
    wav.unlink(missing_ok=True)
    print(" ".join(w["text"] for w in words))
    return words


# ---------------------------------------------------------------- cutting
def keep_ranges(words, duration, max_pause, pad=0.06):
    ranges = []
    for w in words:
        s, e = max(0.0, w["start"] - pad), min(duration, w["end"] + pad)
        if ranges and s - ranges[-1][1] <= max_pause:
            ranges[-1][1] = max(ranges[-1][1], e)
        else:
            ranges.append([s, e])
    return ranges


def remap(t, ranges):
    acc = 0.0
    for s, e in ranges:
        if t <= e:
            return acc + max(0.0, t - s)
        acc += e - s
    return acc


# ---------------------------------------------------------------- on-screen text (ASS)
def ass_time(t):
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def ass_escape(text):
    return text.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", "\\N")


def caption_chunks(words, max_words=3):
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        breaks = (len(cur) >= max_words or w["text"][-1:] in ".,!?;:" or nxt is None
                  or nxt["start"] - w["end"] > 0.35)
        if breaks:
            chunks.append(cur)
            cur = []
    return chunks


def build_ass(path, w, h, words, ranges, hook, hook_seconds, captions, hook_middle=False):
    k = h / 1920
    cap_size, hook_size = round(78 * k), round(74 * k)
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {w}", f"PlayResY: {h}", "WrapStyle: 0", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding",
        # Captions: white, heavy dark outline, lower-middle of the frame (clear of the app buttons at the bottom).
        f"Style: Cap,{FONT_CAP},{cap_size},&H00FFFFFF,&H00FFFFFF,&H00301A2E,&H64000000,0,0,0,0,100,100,0,0,1,"
        f"{round(6 * k)},{round(2 * k)},2,{round(80 * k)},{round(80 * k)},{round(620 * k)},1",
        # Hook: dark plum text on a soft white box near the top.
        f"Style: Hook,{FONT_HOOK},{hook_size},&H00402A3D,&H00402A3D,&H00F7F5FB,&H00F7F5FB,-1,0,0,0,100,100,0,0,3,"
        f"{round(22 * k)},0,8,{round(90 * k)},{round(90 * k)},{round(250 * k)},1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    if hook:
        where = "{\\an5}" if hook_middle else ""  # montage text sits in the middle of the frame
        lines.append(f"Dialogue: 1,{ass_time(0)},{ass_time(hook_seconds)},Hook,,0,0,0,,{where}{ass_escape(hook)}")
    if captions:
        chunks = caption_chunks(words)
        for i, c in enumerate(chunks):
            start = remap(c[0]["start"], ranges)
            end = remap(c[-1]["end"], ranges) + 0.08
            if i + 1 < len(chunks):
                end = min(end + 0.3, remap(chunks[i + 1][0]["start"], ranges))
            text = " ".join(x["text"] for x in c).upper()
            lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Cap,,0,0,0,,{ass_escape(text)}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def ff_filter_path(p):
    # ffmpeg filter arguments need forward slashes and an escaped drive colon on Windows.
    s = str(Path(p).resolve()).replace("\\", "/")
    return s.replace(":", "\\:")


# ---------------------------------------------------------------- yap
def sentences(video, workdir):
    words_file = workdir / "words.json"
    words = (json.loads(words_file.read_text(encoding="utf-8")) if words_file.is_file()
             else transcribe(video, workdir))
    cur = []
    n = 0
    for i, w in enumerate(words):
        cur.append(w)
        if w["text"][-1:] in ".!?" or i == len(words) - 1:
            n += 1
            print(f"{n:>2}. [{cur[0]['start']:.2f}-{cur[-1]['end']:.2f}] " + " ".join(x["text"] for x in cur))
            cur = []


def frame(video, workdir, at):
    workdir.mkdir(parents=True, exist_ok=True)
    out = workdir / f"frame-{at:.1f}.jpg"
    filters = (TONEMAP if is_hdr(video) else "") + "scale=540:-1:out_range=pc"
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(at), "-i", str(video), "-frames:v", "1",
         "-vf", filters, "-pix_fmt", "yuvj420p", str(out)])
    print(out)


def yap(video, workdir, hook, hook_seconds, captions, max_pause, out, remove=None):
    workdir = Path(workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    words_file = workdir / "words.json"
    words = (json.loads(words_file.read_text(encoding="utf-8")) if words_file.is_file()
             else transcribe(video, workdir))
    for span in remove or []:
        a, b = (float(x) for x in span.split("-"))
        words = [x for x in words if not (a <= (x["start"] + x["end"]) / 2 <= b)]
    if not words:
        sys.exit("No speech found in this clip.")
    w, h, duration = probe(str(video))
    ranges = keep_ranges(words, duration, max_pause)
    kept = sum(e - s for s, e in ranges)

    ass = workdir / "text.ass"
    build_ass(ass, w, h, words, ranges, hook, hook_seconds, captions)

    parts, labels = [], []
    for i, (s, e) in enumerate(ranges):
        parts.append(f"[0:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS[v{i}];")
        parts.append(f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.02,afade=t=out:st={max(0, e - s - 0.02):.3f}:d=0.02[a{i}];")
        labels.append(f"[v{i}][a{i}]")
    # Paths inside a filter graph break on apostrophes (a user named O'Brien) and drive colons, so ffmpeg runs from the
    # work folder and the graph names only plain relative files.
    fonts_here = workdir / "fonts"
    fonts_here.mkdir(exist_ok=True)
    for f in FONT_DIR.glob("*.ttf"):
        shutil.copy2(f, fonts_here / f.name)
    # iPhones often film in HDR; without tone mapping it looks washed out on most phones once posted.
    tonemap = ""
    if is_hdr(str(video)):
        tonemap = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
                   "zscale=t=bt709:m=bt709:r=tv,format=yuv420p,")
    graph = ("".join(parts) + "".join(labels) + f"concat=n={len(ranges)}:v=1:a=1[cv][ca];"
             f"[cv]{tonemap}ass=text.ass:fontsdir=fonts[outv]")
    (workdir / "graph.txt").write_text(graph, encoding="utf-8")

    out = (Path(out) if out else workdir / f"{Path(video).stem}-yap.mp4").resolve()
    video = Path(video).resolve()
    # ffmpeg 7+ reads a filter graph from a file with "-/filter_complex"; older builds use -filter_complex_script.
    ver = run(["ffmpeg", "-version"]).split()[2]
    major = int(ver.split(".")[0]) if ver[:1].isdigit() else 7
    graph_opt = ["-/filter_complex"] if major >= 7 else ["-filter_complex_script"]
    run(["ffmpeg", "-v", "error", "-y", "-i", str(video), *graph_opt, str(workdir / "graph.txt"),
         "-map", "[outv]", "-map", "[ca]", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)],
        cwd=workdir)
    print(f"DONE: {out}")
    print(f"Length: {duration:.1f}s before, {kept:.1f}s after ({duration - kept:.1f}s of pauses cut, {len(ranges)} pieces)")
    return out


# ---------------------------------------------------------------- shared by voiceover and montage
OUT_W, OUT_H = 1080, 1920
TONEMAP = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
           "zscale=t=bt709:m=bt709:r=tv,format=yuv420p,")


def has_video(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=codec_name",
               "-of", "csv=p=0", str(path)]).strip()
    return bool(out) and out not in ("mjpeg", "png")  # cover art in an audio file isn't video


def graph_flag():
    ver = run(["ffmpeg", "-version"]).split()[2]
    major = int(ver.split(".")[0]) if ver[:1].isdigit() else 7
    return "-/filter_complex" if major >= 7 else "-filter_complex_script"


def shot_filter(inp, start, dur, hdr, label):
    """One piece of footage, trimmed and fitted to a full vertical frame (cropped, never letterboxed)."""
    return (f"[{inp}:v]trim=start={start:.3f}:duration={dur:.3f},setpts=PTS-STARTPTS,"
            f"{TONEMAP if hdr else ''}scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
            f"crop={OUT_W}:{OUT_H},fps=30,setsar=1,format=yuv420p[{label}];")


def finish(workdir, inputs, graph, out):
    """inputs: list of ffmpeg input argument lists. graph must end in [outv] and [outa]."""
    fonts_here = workdir / "fonts"
    fonts_here.mkdir(exist_ok=True)
    for f in FONT_DIR.glob("*.ttf"):
        shutil.copy2(f, fonts_here / f.name)
    (workdir / "graph.txt").write_text(graph, encoding="utf-8")
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for i in inputs:
        cmd += i
    cmd += [graph_flag(), str(workdir / "graph.txt"), "-map", "[outv]", "-map", "[outa]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)]
    run(cmd, cwd=workdir)
    print(f"DONE: {out}")


def fill_from_clips(clips, info, need, state):
    """Take `need` seconds of footage, moving round-robin through the clips so shots keep changing."""
    pieces = []
    while need > 0.01:
        c = state["next"] % len(clips)
        state["next"] += 1
        dur = info[c]["dur"]
        off = state["offset"][c]
        if dur - off < 0.6:  # this clip is used up: start it over
            off = min(0.3, dur * 0.1)
        take = min(need, dur - off)
        pieces.append((c, off, take))
        state["offset"][c] = off + take
        need -= take
    return pieces


# ---------------------------------------------------------------- voiceover over b-roll
def voiceover(voice, clips, workdir, hook, hook_seconds, captions, max_pause, face_first, shot_min, shot_max,
              out, remove=None):
    workdir = Path(workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    voice = Path(voice).resolve()
    clips = [Path(c).resolve() for c in clips]
    if not clips:
        sys.exit("Voiceover needs at least one b-roll clip.")
    words_file = workdir / "words.json"
    words = (json.loads(words_file.read_text(encoding="utf-8")) if words_file.is_file()
             else transcribe(voice, workdir))
    for span in remove or []:
        a, b = (float(x) for x in span.split("-"))
        words = [x for x in words if not (a <= (x["start"] + x["end"]) / 2 <= b)]
    if not words:
        sys.exit("No speech found in the voiceover.")
    vdur = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                      str(voice)]).strip())
    ranges = keep_ranges(words, vdur, max_pause)
    total = sum(e - s for s, e in ranges)

    # Where shots change: at the start of a caption phrase, at least shot_min apart, never longer than shot_max.
    marks = [remap(c[0]["start"], ranges) for c in caption_chunks(words)]
    cuts, last = [0.0], 0.0
    for t in marks + [total]:
        while t - last > shot_max:
            last += shot_max
            cuts.append(last)
        if t - last >= shot_min and t < total - 0.8:
            cuts.append(t)
            last = t
    cuts.append(total)

    # Optional: open on her face for the first sentence (only when the voiceover was filmed, not just recorded).
    face_until = 0.0
    if face_first and has_video(voice):
        for w in words:
            if w["text"][-1:] in ".!?":
                face_until = remap(w["end"], ranges) + 0.06
                break
        face_until = min(face_until, total)
        later = [c for c in cuts if c > face_until + 0.8]
        cuts = [0.0, face_until] + later if face_until > 0 else cuts

    info = []
    for c in clips:
        cw, ch, cd = probe(str(c))
        info.append({"dur": cd, "hdr": is_hdr(str(c))})
    voice_hdr = has_video(voice) and is_hdr(str(voice))
    state = {"next": 0, "offset": [min(0.3, i["dur"] * 0.1) for i in info]}

    parts, labels, n = [], [], 0
    for a, b in zip(cuts, cuts[1:]):
        if b - a < 0.05:
            continue
        if a < face_until:  # her face: the same voiceover pieces, so lips match
            acc = 0.0
            for s, e in ranges:
                lo, hi = max(a, acc), min(b, acc + (e - s))
                if hi > lo:
                    parts.append(shot_filter(0, s + (lo - acc), hi - lo, voice_hdr, f"s{n}"))
                    labels.append(f"[s{n}]")
                    n += 1
                acc += e - s
            continue
        for c, off, take in fill_from_clips(clips, info, b - a, state):
            parts.append(shot_filter(c + 1, off, take, info[c]["hdr"], f"s{n}"))
            labels.append(f"[s{n}]")
            n += 1

    alabels = []
    for i, (s, e) in enumerate(ranges):
        parts.append(f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.02,afade=t=out:st={max(0, e - s - 0.02):.3f}:d=0.02[a{i}];")
        alabels.append(f"[a{i}]")

    build_ass(workdir / "text.ass", OUT_W, OUT_H, words, ranges, hook, hook_seconds, captions)
    # Each shot rounds to whole frames, which adds up over 30+ shots; pin the picture to the voice's length.
    graph = ("".join(parts) + "".join(labels) + f"concat=n={n}:v=1:a=0[bv0];"
             + "".join(alabels) + f"concat=n={len(ranges)}:v=0:a=1[outa];"
             f"[bv0]tpad=stop_mode=clone:stop_duration=2,trim=duration={total:.3f}[bv];"
             "[bv]ass=text.ass:fontsdir=fonts[outv]")
    out = (Path(out) if out else workdir / f"{voice.stem}-voiceover.mp4").resolve()
    finish(workdir, [["-i", str(voice)]] + [["-i", str(c)] for c in clips], graph, out)
    print(f"Length: {total:.1f}s, {n} shots from {len(clips)} clips"
          + (f", her face for the first {face_until:.1f}s" if face_until else ""))
    return out


# ---------------------------------------------------------------- b-roll montage
def montage(clips, workdir, text, text_middle, shot, length, music, out):
    workdir = Path(workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    clips = [Path(c).resolve() for c in clips]
    if len(clips) < 3:
        sys.exit("A montage needs at least 3 clips (8 or more looks best).")
    info = []
    for c in clips:
        cw, ch, cd = probe(str(c))
        info.append({"dur": cd, "hdr": is_hdr(str(c))})
    count = max(len(clips), round(length / shot))
    uses = [0] * len(clips)
    plan = []
    for k in range(count):
        uses[k % len(clips)] += 1
    seen = [0] * len(clips)
    for k in range(count):
        c = k % len(clips)
        seen[c] += 1
        d = min(shot, info[c]["dur"] - 0.1)
        # Spread a clip's shots across it; the middle of a clip is usually its steadiest part.
        center = info[c]["dur"] * seen[c] / (uses[c] + 1)
        start = min(max(0.0, center - d / 2), max(0.0, info[c]["dur"] - d - 0.05))
        plan.append((c, start, d))
    total = sum(d for _, _, d in plan)

    parts, labels = [], []
    for i, (c, s, d) in enumerate(plan):
        parts.append(shot_filter(c, s, d, info[c]["hdr"], f"s{i}"))
        labels.append(f"[s{i}]")
    inputs = [["-i", str(c)] for c in clips]
    if music:
        inputs.append(["-i", str(Path(music).resolve())])
        audio = (f"[{len(clips)}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,"
                 f"afade=t=out:st={max(0, total - 1):.3f}:d=1[outa];")
    else:
        # Silent track: she adds a trending sound in TikTok or Instagram when she posts.
        inputs.append(["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=48000:cl=stereo"])
        audio = f"[{len(clips)}:a]anull[outa];"

    build_ass(workdir / "text.ass", OUT_W, OUT_H, [], [], text, total, False, hook_middle=text_middle)
    graph = ("".join(parts) + "".join(labels) + f"concat=n={len(plan)}:v=1:a=0[bv];" + audio
             + "[bv]ass=text.ass:fontsdir=fonts[outv]")
    out = (Path(out) if out else workdir / "montage.mp4").resolve()
    finish(workdir, inputs, graph, out)
    print(f"Length: {total:.1f}s, {len(plan)} shots from {len(clips)} clips"
          + ("" if music else ", silent (add a sound in the app)"))
    return out


# ---------------------------------------------------------------- check
def check():
    ok = True
    ff = shutil.which("ffmpeg")
    for name, value in [("ffmpeg", ff), ("ffprobe", shutil.which("ffprobe")),
                        ("ffmpeg captions and HDR support", ff and has_filters("ass", "zscale", "tonemap") or None),
                        ("Whisper", find_whisper()), ("transcription model", find_model()),
                        ("fonts", (FONT_DIR / "Montserrat-ExtraBold.ttf").is_file() or None)]:
        print(("READY   " if value else "MISSING ") + name)
        ok = ok and bool(value)
    print("ALL READY" if ok else "NOT READY")
    return ok


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    t = sub.add_parser("transcribe")
    t.add_argument("video")
    t.add_argument("workdir")
    y = sub.add_parser("yap")
    y.add_argument("video")
    y.add_argument("workdir")
    y.add_argument("--hook", default="")
    y.add_argument("--hook-seconds", type=float, default=3.0)
    y.add_argument("--no-captions", action="store_true")
    y.add_argument("--max-pause", type=float, default=0.25)
    y.add_argument("--out")
    y.add_argument("--remove", action="append", metavar="START-END",
                   help="drop everything said between these seconds (repeatable), e.g. --remove 61.2-64.9")
    s = sub.add_parser("sentences")
    s.add_argument("video")
    s.add_argument("workdir")
    f = sub.add_parser("frame")
    f.add_argument("video")
    f.add_argument("workdir")
    f.add_argument("--at", type=float, default=2.0)
    v = sub.add_parser("voiceover")
    v.add_argument("voice", help="her voiceover: a voice memo or a video of her talking")
    v.add_argument("workdir")
    v.add_argument("--clips", nargs="+", required=True, help="b-roll clips, in the order she wants them")
    v.add_argument("--hook", default="")
    v.add_argument("--hook-seconds", type=float, default=3.0)
    v.add_argument("--no-captions", action="store_true")
    v.add_argument("--max-pause", type=float, default=0.25)
    v.add_argument("--face-first", action="store_true", help="show her talking for the first sentence")
    v.add_argument("--shot-min", type=float, default=1.8)
    v.add_argument("--shot-max", type=float, default=3.5)
    v.add_argument("--remove", action="append", metavar="START-END")
    v.add_argument("--out")
    m = sub.add_parser("montage")
    m.add_argument("workdir")
    m.add_argument("--clips", nargs="+", required=True)
    m.add_argument("--text", default="", help="the one text overlay, shown the whole time")
    m.add_argument("--text-middle", action="store_true", help="put the text mid-frame instead of near the top")
    m.add_argument("--shot", type=float, default=1.2, help="seconds per shot")
    m.add_argument("--length", type=float, default=12.0, help="about how long the montage runs")
    m.add_argument("--music", help="an audio file she owns; leave out to add a sound in the app")
    m.add_argument("--out")
    a = p.parse_args()
    if a.cmd == "check":
        sys.exit(0 if check() else 1)
    if a.cmd == "voiceover":
        voiceover(a.voice, a.clips, a.workdir, a.hook, a.hook_seconds, not a.no_captions, a.max_pause,
                  a.face_first, a.shot_min, a.shot_max, a.out, a.remove)
        return
    if a.cmd == "montage":
        montage(a.clips, a.workdir, a.text, a.text_middle, a.shot, a.length, a.music, a.out)
        return
    if a.cmd == "transcribe":
        transcribe(Path(a.video), Path(a.workdir))
    elif a.cmd == "sentences":
        sentences(Path(a.video), Path(a.workdir))
    elif a.cmd == "frame":
        frame(Path(a.video), Path(a.workdir), a.at)
    else:
        yap(Path(a.video), Path(a.workdir), a.hook, a.hook_seconds, not a.no_captions, a.max_pause, a.out,
            a.remove)


if __name__ == "__main__":
    main()
