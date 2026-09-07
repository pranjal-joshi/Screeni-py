---
name: breakout
when_to_use: User asks for breakout, 52-week high, resistance break, volume-supported breakout, or early breakout setups.
tools:
  - tool: screen_breakout
    params:
      index: Nifty 500
      days_lookback: 20
  - tool: screen_volume_breakout
    params:
      index: Nifty 500
      volume_ratio: 1.5
---

# Breakout

## Description
Flagship breakout skill: finds stocks breaking key resistance on volume.

## When to Use
Trigger when the user description mentions breakout, new high, resistance, consolidation break, or wants momentum breakout ideas without naming a specific indicator.

## Entry Criteria
- Price closing above prior 20-day high or consolidation high
- Volume >= 1.5x 20-day average on breakout day
- Close above 50-DMA (Stage 2 uptrend) preferred but not mandatory

## Tools
Ordered chain:
1. screen_breakout (days_lookback=20) to find structural breakouts
2. screen_volume_breakout (volume_ratio=1.5) to confirm with volume

## Exit / Stop
- Stop below breakout base low or 20-day low
- Target next resistance; minimum 1:2 R:R
- Flag separately if breakout fails to hold on closing basis

## Rendering
Table columns: Stock, LTP, Volume, Breakout Days, Pattern, TradingView link. One line per pick.
