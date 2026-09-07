---
name: vcp
when_to_use: User asks for VCP, volatility contraction, Mark Minervini setup, tight base with contracting volatility, or low-volatility base before markup.
tools:
  - tool: screen_vcp
    params:
      index: Nifty 500
      window: 3
      pct_from_top: 3.0
---

# VCP — Volatility Contraction Pattern

## Description
Mark Minervini VCP: contracting volatility into a tight base.

## When to Use
Trigger on VCP, volatility contraction, tightening base, or Minervini-style setup requests.

## Entry Criteria
- Successive contractions with declining volatility (e.g., 3 cycles)
- Price within 3% of 52-week high base
- Volume dries up into the pivot

## Tools
Ordered chain:
1. screen_vcp (window=3, pct_from_top=3.0)

## Exit / Stop
- Stop below last contraction low or tight base low
- Target measured base height; 1:2+ R:R

## Rendering
Table: Stock, Contraction Window, Distance From Top, Volume signature, TradingView link.
