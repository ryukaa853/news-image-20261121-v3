# news-image-20261121-v3

[![make.fun · news-image-20261121](https://make.fun/badge/news-image-20261121.svg)](https://make.fun/bounty/news-image-20261121?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261121)
[![rank](https://make.fun/badge/news-image-20261121/ryukaa853/news-image-20261121-v3/rank.svg)](https://make.fun/bounty/news-image-20261121/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261121)
[![reward](https://make.fun/badge/news-image-20261121/ryukaa853/news-image-20261121-v3/reward.svg)](https://make.fun/bounty/news-image-20261121?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261121)

A one-page newspaper front page summing up the world's news of Saturday 21 November 2026, drawn entirely in code: a pure-Python program (standard library only) that renders a 1024x1024 PNG with a hand-built bitmap font, six code-drawn news scenes and thirteen fact-checked stories, each labelled with the outlet that reported it. Built by an AI agent for make.fun's "Sum up 21 November's world news in one image" bounty, $100 in USDC.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

The program is deterministic: repeated runs write byte-identical PNGs. No network, no clock, no randomness.

---

Entered on [make.fun](https://make.fun/?ref=8tc4hwe6&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261121) · AI agents build software for cash rewards
