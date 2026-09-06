# CONTEXT.md

Single-context repo. This file is a glossary and nothing else: canonical
terms for Screeni-py v4. No implementation details live here.

## Glossary

- **Chat**: the Open WebUI service. The sole user-facing front door in v4;
  all queries and answers flow through it.
- **Screenipy service (engine)**: the app service holding the screener brain
  (agent engine, read-only MCP tools, data adapter, background cache warmer).
  Serves an OpenAI-compatible `/v1` chat endpoint that Chat points at.
- **Dumb shell**: the wiring pattern where Chat holds no agent logic and
  forwards conversation to the Screenipy service's `/v1` endpoint.
- **Skill**: a markdown strategy-as-skill (entry criteria plus tool chain
  plus exit rules). Curated seed set ships with v4; users may author custom
  skills.
- **BYOK**: bring your own key. The single user supplies one API key plus
  endpoint for an OpenAI-compatible model; first-run onboarding collects and
  persists it.
- **Warmer**: the background job that refreshes cached market data on app
  open so answers serve from cache when not stale.
