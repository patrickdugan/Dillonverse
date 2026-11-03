from __future__ import annotations

import argparse
import json
from pathlib import Path

from .youtube import collect_captions, discover


def main() -> None:
    parser = argparse.ArgumentParser(prog="dillonverse")
    parser.add_argument("command", choices=("discover", "captions"))
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Dillonverse project directory")
    parser.add_argument("--limit", type=int, help="maximum number of videos to process")
    parser.add_argument("--video-id", action="append", dest="video_ids", help="restrict captions to a video ID; may be repeated")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.command == "discover":
        print(json.dumps({"discovered": discover(args.root, args.limit)}, indent=2))
    else:
        print(json.dumps(collect_captions(args.root, args.limit, set(args.video_ids or [])), indent=2))


if __name__ == "__main__":
    main()
