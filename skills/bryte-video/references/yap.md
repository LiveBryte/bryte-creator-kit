# Talking-head yap

She talks straight to the camera in a real setting (kitchen, car, backyard). The edit makes it feel quick and alive without changing what she said.

## What the finished video looks like

- **No dead air.** Every pause longer than about a quarter second is cut. Her words stay exactly as she said them.
- **Hook on top for the first 3 seconds.** Dark text on a soft white box near the top of the frame. Under 10 words.
- **Captions underneath.** White, bold, capital letters, 1-3 words at a time, sitting at chest height so they don't cover her face or the app buttons.
- **Length:** whatever she said, minus the pauses. 30-75 seconds is normal. Don't cut lines just to make it shorter unless she asks.

## Writing hook options

The hook is what stops the scroll. Build it from her first sentence or her strongest line. It names what she felt, in her words.

Good hook patterns:
- Her opening line, tightened: "Nobody warned me about this part of motherhood"
- The moment: "I walked into a room and forgot why. Again."
- The relief: "I finally feel like myself again"
- The question: "Is mom brain real? Here's what I learned"

Rules:
- Under 10 words. Sentence case, not all capitals.
- About her experience, not about the product. "I couldn't finish a sentence" beats "Try BryteMama today."
- Must pass `brand-rules.md`, the same as anything she says. Never "fixes", "cures" or "reverses" in a hook.
- No prices or discounts in the hook.

## When to change the defaults

- **Captions already burned in** (you see words on the `frame` image that she didn't add): use `--no-captions` so there aren't two sets.
- **She talks very fast and it feels breathless after cutting:** re-run with `--max-pause 0.4`.
- **She wants a line gone** (a stumble, an off-brand claim, an old offer): find its seconds in `sentences` and add `--remove START-END`. You can add `--remove` more than once.
- **Horizontal video:** it still works, but tell her vertical (phone held upright) works much better for ads and ask if she can re-film.
- **Hook should stay up longer** (a long hook): `--hook-seconds 4`.
