from __future__ import annotations

"""CLI for research-only production-vs-candidate fixture comparisons."""

import argparse
import json

from app.ml.candidates import compare_with_production

COMPETITIONS = {
    "laliga": "La Liga",
    "bundesliga": "Bundesliga",
}


def main():
    parser = argparse.ArgumentParser(description="Compare production v2 with a protected candidate")
    parser.add_argument("--league", choices=COMPETITIONS, required=True)
    parser.add_argument("--home", required=True)
    parser.add_argument("--away", required=True)
    args = parser.parse_args()

    result = compare_with_production(
        args.league, args.home, args.away, COMPETITIONS[args.league]
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
