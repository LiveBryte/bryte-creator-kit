# B-roll montage

Quick cuts of her day set to a song, with one line of text on screen the whole time. Nobody talks. It's the easiest one to make: she just films little moments.

## What she needs to give you

- **At least 3 clips, ideally 8 to 15.** Little moments, 2-10 seconds each, phone held upright: scooping BryteMama into a glass, stirring, the first sip, sunlight in the kitchen, kids playing, a calm moment with a book, a walk.
- **One line of text** (optional) if she has wording she wants on screen.
- **Music (optional):** better to leave it out. She adds a trending sound in TikTok or Instagram when she posts, which also helps the video get seen. Only use `--music` with a song file she owns or got from a free library, never a song downloaded from somewhere else.

## What the finished video looks like

- About 10-12 seconds, a new shot every ~1.2 seconds. Each clip shows up once or twice, taken from its steadiest middle part.
- One text line the whole time, near the top (or mid-frame with `--text-middle`).
- Silent, ready for her to add a sound in the app.

## Writing the text line

It's a feeling or a moment, written like a thought she'd text a friend. Under 12 words.
- "POV: you finally have a morning routine that's just for you"
- "The 5 minutes a day that are just mine"
- "Romanticizing the tiny moments of motherhood"
- "Me remembering why I walked into the kitchen"

It must pass `brand-rules.md` too: no "fixes my mom brain", no results promises, no prices.

## Steps

1. `frame` on a few clips. Do the clip check from `voiceover.md`.
2. Use the supplied text if it passes the brand check. If she has not supplied text, render the first cut without it and suggest a line after export.
3. Run `montage <work> --clips <clip1> <clip2> ... [--text "..."] --out <file>`. Add `--length 15` for a longer one, `--shot 0.8` for faster cuts.
4. `frame` the finished video at 1 second and near the end: is the text readable and the shots changing?
5. Tell her: "It's silent on purpose. When you post, tap Add sound in TikTok or Instagram and pick a trending song."
