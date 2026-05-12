# DocSearch AI Development Workflow

## Branch Model

- `main`
  - preserves the original V1 prototype
  - release-only branch
  - no direct feature work
- `develop`
  - integration branch for the rebuild
  - every new feature branch starts from `develop`
  - reviewed changes merge back into `develop`

## Branch Naming

Use a type prefix for every working branch.

- `feat/<scope>`
- `fix/<scope>`
- `chore/<scope>`
- `docs/<scope>`
- `refactor/<scope>`
- `test/<scope>`

Examples:

- `chore/workflow`
- `feat/scaffold`
- `feat/auth`
- `feat/ingestion`
- `feat/retrieval`
- `fix/search-filter`

## PR Rules

- Every PR targets `develop`
- `main` only receives reviewed integration from `develop`
- One PR should contain one concern only
- Keep PRs small enough to review in one sitting
- Prefer stacked PRs when the next slice depends on the previous one

Recommended size:

- under 400 changed lines when practical
- under 10 files when practical
- split early when infra, API, storage, and UI start mixing

## Commit Rules

Use conventional commits:

- `feat(scope): summary`
- `fix(scope): summary`
- `chore(scope): summary`
- `docs(scope): summary`
- `refactor(scope): summary`
- `test(scope): summary`

Examples:

- `feat(scaffold): add backend bootstrap`
- `feat(auth): add api key validation`
- `chore(infra): replace runtime layout and ci`
- `docs(scaffold): refresh repository overview`

Each commit should do one thing:

1. add a failing test
2. add the minimal implementation
3. refactor without changing behavior
4. update docs or config

## Merge Rules

- feature branches merge into `develop` after review
- use linear history where practical
- avoid force-pushing after review starts unless the branch is still private
- prefer follow-up commits over rewriting reviewed history

## Review Sequence

Review the rebuild in this order:

1. workflow and plans
2. scaffold and runtime boundaries
3. API key auth and request context
4. document upload and storage
5. indexing worker and queue abstraction
6. retrieval and reranking
7. local LLM gateway
8. chat and citation response
9. frontend flows
10. observability and hardening

## Initial Branch Plan

- `develop`
- `chore/workflow`
- `feat/scaffold`
- `feat/auth`
- `feat/ingestion`
- `feat/indexing-worker`
- `feat/retrieval`
- `feat/llm-gateway`
- `feat/chat-api`
- `feat/frontend-shell`
- `chore/observability`
- `fix/hardening`

## Review Checklist

Before opening a PR:

- branch name follows the type rule
- commit history is grouped by concern
- tests for the touched area were run
- docs changed with the code when behavior changed
- PR body explains scope, non-goals, and verification

Before merging into `develop`:

- no unrelated file churn
- no opportunistic refactors outside the PR scope
- follow-up work is explicitly deferred to another branch
