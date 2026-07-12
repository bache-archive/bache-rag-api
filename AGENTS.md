# Bache RAG API Agent Instructions

This repository serves citation-grounded search and answers over the public Bache Archive corpus.

## Identity Boundary

- Remote must be `git@github-bache:bache-archive/bache-rag-api.git`.
- Local Git identity must be `Bache Archive <bache-archive@tuta.com>`.
- Do not deploy, link, or configure this service from personal GitHub, Vercel, Render, or API accounts.

## Behavior Contract

- Answers must be grounded in retrieved archive context and return citations.
- Do not answer from model priors when retrieval fails.
- Preserve stable response fields used by frontend clients unless a versioned migration is documented.
- Keep raw API keys and local `.env` files out of Git.

## Verification

- Before changing retrieval behavior, run representative `/search` and `/answer` checks for known terms such as Diamond Luminosity, Future Human, reincarnation, and collective consciousness.
- When vectors change, record vector count, metadata row count, and source corpus version.
