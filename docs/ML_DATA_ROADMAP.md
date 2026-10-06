# FanSphere ML Data Roadmap

## Current stopping point — 2026-10-06

Production remains pinned to domestic **v2**. Experimental v3/v4/v5 models and the StatsBomb xG prototype are research only and must not silently replace production.

## What the experiments established

1. Changing algorithms alone did not reliably beat v2 across the five domestic leagues.
2. Adding more results-derived rolling features also did not reliably beat v2.
3. StatsBomb Open Data is valuable for event research but its open competition/season coverage is not broad enough for FanSphere's complete, current five-league production training requirement.
4. The next material improvement should therefore come from better football information rather than another arbitrary model version.

## Data requirements for the next benchmark

A candidate source/dataset should provide, ideally across Premier League, La Liga, Bundesliga, Serie A and Ligue 1:

- complete match results by season;
- stable team and match identifiers;
- match-level expected goals (xG), preferably home and away;
- shots / shots on target and other pre-match-derivable rolling statistics;
- lineups and player availability where licensing/coverage permits;
- enough historical seasons for chronological training and testing;
- current or recently completed seasons;
- clear usage terms suitable for the project.

Do not introduce any feature that would only be known after the match being predicted.

## Research findings

### Understat ecosystem

Public documentation around the `soccerdata` ecosystem describes Understat coverage for the European big five, including schedules with home/away xG and per-match team statistics such as xG, non-penalty xG, expected points, PPDA and deep completions. This is a strong research candidate because its historical span is much broader than the StatsBomb open-season subset.

Before integrating it, verify current accessibility, terms, exact match-level completeness, team-name mapping and whether automated retrieval is reliable enough for a reproducible project.

### Current API/data-provider candidates

Several current providers advertise complete historical results and richer match statistics. Some richer fields are paid or plan-gated. Do not add a paid dependency merely to improve a benchmark; first determine whether a reproducible research dataset can establish that the extra information materially improves held-out results.

### Player availability

There are public research datasets covering matchday player availability/injuries across the European big leagues. Availability is potentially useful, but it creates a harder historical feature-engineering problem: FanSphere must represent the importance of unavailable players using information available before kickoff. It should be a later experiment after a match-level xG baseline is established.

## Next session plan

1. Audit an Understat/soccerdata-style match-level dataset for all five leagues and several seasons.
2. Build a local normalized schema: date, league, season, home team, away team, home goals, away goals, home xG, away xG.
3. Check missingness, duplicate matches, naming consistency and chronological coverage before training anything.
4. Join or derive only pre-match rolling features.
5. Benchmark results-only vs results+xG on identical chronological splits.
6. Compare accuracy, multiclass log loss and Brier score league by league against v2.
7. Promote nothing unless the improvement is repeatable rather than isolated to one league/test window.

## Evaluation guardrails

- Keep final test periods untouched during feature/model selection.
- Use chronological validation rather than random cross-validation for time-dependent football data.
- If probability calibration is added, use a chronological calibration block.
- Report failures and regressions, not just wins.
- Preserve explicit per-league production version selection.
- Do not infer model quality from a handful of visually plausible fixtures.

## Production status

**Domestic:** v2 remains production.

**European/cross-league:** keep the current chronology-correct European model/bridge behavior until a stronger validated replacement exists.

**Tomorrow's first task:** data audit, not another model version.
