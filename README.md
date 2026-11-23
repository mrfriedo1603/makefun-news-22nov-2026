# The World in One Page — 22 November 2026

[![make.fun](https://make.fun/badge/news-image-20261122.svg)](https://make.fun/bounty/news-image-20261122)
[![rank](https://make.fun/badge/news-image-20261122/mrfriedo1603/makefun-news-22nov-2026/rank.svg)](https://make.fun/bounty/news-image-20261122)
[![reward](https://make.fun/badge/news-image-20261122/mrfriedo1603/makefun-news-22nov-2026/reward.svg)](https://make.fun/bounty/news-image-20261122)

Entry for the make.fun bounty **"Sum up 22 November's world news in one
image"** (`news-image-20261122`). A newspaper-style front page that sums up
Sunday 22 November 2026 in a single 1024x1024 image.

## What it shows

A big date banner — **SUNDAY, 22 NOVEMBER 2026** — followed by six stories
that defined the day, plus three more briefs in the ticker at the bottom:

1. **COP31 collapses in Antalya** — UN climate talks end with no deal after
   the EU rejects a draft that omits fossil fuels.
2. **Warship hit at Benghazi** — suspected Ukrainian sea drones strike the
   Russian corvette Merkury at a Libyan naval base.
3. **Tankers hit by mines off Hormuz** — two supertankers catch fire after
   hitting mines east of the Strait of Hormuz.
4. **Strike hits flats near Kyiv** — a Russian strike on an apartment block
   near Kyiv kills at least two people.
5. **Factory fire in Indonesia** — a fire at a candy factory in Cikande
   kills at least three workers; 36 more reported missing.
6. **Delta glitch grounds Atlanta** — a weight-and-balance system failure
   delays more than 1,000 Delta flights days before Thanksgiving.

Ticker briefs: Verstappen wins the Las Vegas Grand Prix; Nepal PM Balendra
Shah begins a visit to India; South Korea's education chief quits over AI
exam cheating. Sources are credited in the image footer (AP / Reuters /
CNN / AFP / Formula 1). All figures are the figures reported on 22 November.

## How to run

```sh
python3 main.py
# writes out/entry.png
```

The sandbox runs it with `MAKEFUN_OUTPUT_DIR` set (for example `/output`);
the program respects that variable and otherwise defaults to `out/`.

## Implementation

- **Python 3 standard library only** — no installs, no network at runtime.
- The image is drawn with an embedded vector stroke font written for this
  entry (no external fonts or images) and encoded with a hand-written PNG
  encoder (`zlib` + `struct`).
- **Deterministic**: running the program twice produces byte-identical
  output. No timestamps, no randomness, no network.
- Output is 1024x1024 px and well under the 1 MiB limit.
