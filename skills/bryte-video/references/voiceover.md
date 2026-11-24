# Voiceover over b-roll

She narrates (her routine, her day, her mom-brain story) while clips of her life play on screen. It feels like a mini vlog. A strong text hook opens it.

## What she needs to give you

1. **Her voice.** Either a voice memo, or a video of her talking. A video is better: the kit can open on her face for the first sentence (`--face-first`), which makes people stop scrolling.
2. **3 to 15 short clips (b-roll).** Things like making her BryteMama drink, the tub on the counter, kids' toys on the floor, coffee, school drop-off, folding laundry, a quiet moment outside. 3-10 seconds each, phone held upright.

If she only has a few clips, that's fine: the kit takes different moments from each one so the video doesn't feel repetitive. Fewer than 3 will feel repetitive, so ask for a couple more if you can.

## What the finished video looks like

- Her narration with every pause cut. Her words are unchanged.
- The picture changes every 2-3 seconds, always at the start of a phrase, so cuts land with her speech.
- Clips play in the order she gave them, repeating if needed. Clip sound is off, so only her voice plays.
- Hook on top for the first 3 seconds, captions at chest height (same look as the talking-head video).
- Everything is cropped to fill a vertical phone screen.

## Steps

1. `frame` on her voice file (if it's a video) and on 2-3 clips. Check: vertical? Anything that shouldn't be on screen? (See "Clip check" below.)
2. `sentences` on her voice file. Proofread `words.json`. Run the brand check on every sentence.
3. Offer 3 hooks (same rules as `yap.md`).
4. Ask her clip order only if she cares. Otherwise keep the order she gave them.
5. Run `voiceover <voice> <work> --clips <clip1> <clip2> ... --hook "..." [--face-first] [--remove S-E] --out <file>`.
6. `frame` the finished video at 1 second and in the middle. Check the hook and captions, and that the shots change.

## Clip check (look at the frames)

Flag, kindly, if you see:
- **Other supplement or drink brands** clearly visible next to BryteMama.
- **Children's faces** clearly visible: ask if she's comfortable with that in an ad. It's her call, but BryteMama may not be able to use it as an ad.
- **Anything that suggests medicine:** pill bottles, prescriptions, a hospital.
- **Alcohol** in the shot.

## Options

- Shots feel too fast: `--shot-min 2.5 --shot-max 4.5`. Too slow: `--shot-min 1.4 --shot-max 2.5`.
- Captions already in her clips: still add captions (they come from her voice), but tell her the clips' own text may show through.
- Voice memo with no video: leave out `--face-first`.
