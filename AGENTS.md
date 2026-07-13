# Bache RAG API Agent Instructions

This repository serves citation-grounded search and answers over the public Bache Archive corpus.

## Codex Startup From This Repo

- These instructions must be sufficient when Codex CLI is started from this repository instead of `/Users/howardrhee/projects/bache-archive`.
- Also read `../AGENTS.md` and `../CODEX_WORKSPACE.md` when they are available; they contain cross-repo policy and current workspace priorities.
- Use `AGENTS.md` for durable Codex instructions. Do not create `CODEX.md` unless a separate non-Codex tool explicitly requires it.
- For GitHub CLI commands, set `GH_CONFIG_DIR="$HOME/.config/gh-bache"` so archive auth does not overwrite or use personal GitHub accounts.
- Start broad archive work from `/Users/howardrhee/projects/bache-archive`; keep RAG/API/chat-answer implementation work in this repo.
- Web/frontend/domain work belongs in `../bache-archive-web`.
- Corpus/transcript/fixity work belongs in `../chris-bache-archive`.

## GitHub Issue Ownership

When taking on a GitHub issue, always mark it as in progress before starting local work so other agents can see it is claimed.

1. Read recent issue comments first. If another agent already owns the issue and there is no clear handoff or completion note, do not duplicate the work.
2. Before any code change, branch creation, or dependency install, post a claim comment on the issue using this exact format:

```text
🤖 In progress — branch agent/issue-{N}-{short-slug}
```

3. After posting the claim comment, try to add the GitHub label:

```bash
GH_CONFIG_DIR="$HOME/.config/gh-bache" gh issue edit {N} --add-label "in-progress"
```

If the label does not exist or permissions do not allow it, do not block on that step. The claim comment is still required.

4. Then create the branch and start implementation.
5. When the work is done, blocked, or handed off, comment again with the outcome. If the issue was labeled `in-progress`, remove that label when appropriate.

## Identity Boundary

- Remote must be `git@github-bache:bache-archive/bache-rag-api.git`.
- Local Git identity must be `Bache Archive <bache-archive@tuta.com>`.
- Keep the `meta` submodule on `git@github-bache:bache-archive/bache-archive-meta.git`; do not use default `github.com` or HTTPS remotes for archive repositories.
- Do not deploy, link, or configure this service from personal GitHub, Vercel, Render, or API accounts.
- Keep `logs/`, local `.env*`, and new `reports/quote_packs/<date>/` output out of commits unless explicitly justified.

## Behavior Contract

- Answers must be grounded in retrieved archive context and return citations.
- Do not answer from model priors when retrieval fails.
- Preserve stable response fields used by frontend clients unless a versioned migration is documented.
- Keep raw API keys and local `.env` files out of Git.

## Verification

- Before changing retrieval behavior, run representative `/search` and `/answer` checks for known terms such as Diamond Luminosity, Future Human, reincarnation, and collective consciousness.
- When vectors change, record vector count, metadata row count, and source corpus version.
