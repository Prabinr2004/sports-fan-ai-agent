# ML data checkpoint — 2026-10-06

## Decision

FanSphere production remains on domestic model v2. Do not auto-promote research artifacts.

## Data requirements for the next model

The next domestic experiment must use match-level historical records with:
- Big Five league coverage.
- Completed 2025/26 season data.
- Match-level home/away xG (not player-season aggregate xG).
- Dates and final scores so all rolling features can be computed strictly pre-match.
- Enough prior seasons to train and evaluate chronologically.
- 2026/27 treated as an in-progress current-state season, never as a completed training season.

## Evaluation

Use chronological splits only. Compare against the current v2 approach using:
1. log loss (primary probability-quality metric),
2. Brier score,
3. accuracy,
4. calibration by probability bucket.

No production promotion unless the richer-data model improves probability quality across multiple leagues rather than one isolated test.

## Research findings

- StatsBomb Open Data was rejected for production training because recent Big Five coverage is too selective.
- Direct Understat page parsing was rejected after the October 2026 audit could not reliably extract the league schedule payload.
- Current research indicates complete 2025/26 Big Five match-level datasets with xG exist, but source/licensing/access must be verified before ingestion.
- APIs exposing only player-season xG aggregates are not sufficient for rolling pre-match xG features.

## Next implementation checkpoint

Before writing v6 training code:
1. acquire/verify one reproducible match-level dataset;
2. inspect its exact columns and licensing/usage terms;
3. create a normalized loader;
4. run leakage checks;
5. benchmark results-only vs results+xG on identical chronological rows;
6. only then consider integrating xG into the five-league production trainer.
