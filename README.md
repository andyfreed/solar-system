# TRMNL Solar System Viewer

A TRMNL plugin that displays real-time planet positions around the Sun on your e-ink display. Uses NASA/JPL Keplerian orbital elements to compute positions — no external API needed.

## What's in here

```
api/index.py                       — Vercel serverless function (computes planet positions)
templates/full.liquid               — Full-screen layout (orbital diagram + distance list)
templates/half_horizontal.liquid    — Half-screen layout
templates/quadrant.liquid           — Quadrant layout (diagram only)
settings.yml                        — Plugin config reference
vercel.json                         — Vercel routing config
```

## What it shows

- Orbital diagram with real-time planet positions
- Distance from the Sun for each planet (in millions/billions of miles)
- Current date and time (UTC)

## Setup

1. Import this repo into [Vercel](https://vercel.com) (Add New Project → Import Git Repository)
2. Vercel auto-deploys on every push to main
3. In the [TRMNL dashboard](https://usetrmnl.com), create a **Private Plugin**:
   - **Strategy**: Polling
   - **Polling URL**: `https://your-vercel-app.vercel.app/api`
   - Click **Edit Markup** and paste the contents of `templates/full.liquid`
   - **Refresh rate**: 2 hours or longer (positions don't change fast)
4. Click **Save**, then **Force Refresh** to test

## Notes

- No external API calls — all positions computed from orbital mechanics
- No API keys needed
- Vercel caches responses for 1 hour
- E-ink optimized: black and white, no animations
