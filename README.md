# Dillonverse

A resumable source catalog and local caption collector for public uploads on [The Tim Dillon Show's official YouTube channel](https://www.youtube.com/@TimDillonShow). It follows the provenance-first collection patterns used in Levinverse and Chitraverse: discovery records metadata and source links, while captions remain local and untracked.

## Set up

```powershell
python -m pip install -e ".[collector]"
```

## Collect

Discover the channel's public uploads without downloading media or captions:

```powershell
dillonverse discover
```

Then request English captions only for the videos in the catalog:

```powershell
dillonverse captions
```

Use `--limit 10` to process a smaller batch, or repeat `--video-id ID` to select specific uploads. Both steps can be rerun; the catalog is upserted by YouTube video ID and existing local caption files are skipped.

## Storage and provenance

- `catalog/videos.jsonl` is a public metadata-only index of video IDs, canonical links, titles, dates, durations, discovery source, and caption availability. It contains no transcript text or local file paths.
- Caption VTT files and timestamped text are written to `transcripts/private/` and are kept out of commits.
- The collector uses `yt-dlp` to request YouTube-provided captions and does not download video or audio.
- A missing caption is recorded as unavailable; it is not treated as proof that a transcript does not exist elsewhere.
- Each channel upload is marked `review_required` for scope. Review clips, guests, and other non-show material before treating it as Tim Dillon's own comedy.
- Full caption text is not committed or published by this project. Any redistribution requires a separate rights basis.

## Source

The channel ID and discovery URL are in `config/sources.json`. The channel is linked from the show's official [Linktree](https://linktr.ee/timdillonshow).
