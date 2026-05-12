# DocSearch AI V2 Development Workflow

## Branch Model

- `main`
  - v1 stable branch
  - release-only branch
  - direct commits are not allowed
- `develop`
  - v2 integration branch
  - every V2 feature branch starts from `develop`
  - reviewed changes merge back into `develop`

## Branch Naming

Every working branch must use a type prefix.

- `feat/<scope>-<summary>`
- `fix/<scope>-<summary>`
- `chore/<scope>-<summary>`
- `docs/<scope>-<summary>`
- `refactor/<scope>-<summary>`
- `test/<scope>-<summary>`

Examples:

- `feat/api-key-auth`
- `feat/document-ingestion`
- `feat/rag-retrieval`
- `fix/search-filter-bug`
- `chore/v2-workflow`

## PR Rules

- Every PR targets `develop`
- `main` only receives reviewed integration from `develop`
- One PR should contain one concern only
- Do not mix scaffold, feature logic, and cleanup in one PR unless they are inseparable
- Keep PRs small enough to review in one sitting

Recommended PR size:

- target under 400 changed lines when practical
- target under 10 files when practical
- split earlier if infra, schema, and API changes start mixing

## Commit Rules

Use conventional commit style:

- `feat(scope): summary`
- `fix(scope): summary`
- `chore(scope): summary`
- `docs(scope): summary`
- `refactor(scope): summary`
- `test(scope): summary`

Examples:

- `chore(workflow): add v2 branch strategy`
- `feat(scaffold): add backend v2 app skeleton`
- `feat(auth): add API key middleware`
- `fix(search): handle empty rerank candidates`

Each commit should do one thing:

1. failing test
2. minimal implementation
3. follow-up refactor
4. docs or config

Avoid mixing all four in a single commit.

## Merge Rules

- feature branches merge into `develop` after review
- use linear history where possible
- avoid force-pushing after review starts unless the branch is still private to the author
- if review feedback requires significant change, add a new commit instead of rewriting all previous commits

## V2 Review Sequence

The V2 rebuild should be reviewed in this order:

1. workflow and implementation plan
2. repository scaffold
3. backend config and app bootstrap
4. API key auth and request context
5. document ingestion and storage
6. async indexing worker
7. retrieval and reranking
8. LLM proxy and vLLM integration
9. chat and citation response
10. frontend shell and core user flows
11. observability, hardening, and release prep

## Initial Branch Plan

- `develop`
- `chore/v2-workflow`
- `feat/v2-scaffold`
- `feat/v2-auth`
- `feat/v2-ingestion`
- `feat/v2-indexing-worker`
- `feat/v2-retrieval`
- `feat/v2-llm-gateway`
- `feat/v2-chat-api`
- `feat/v2-frontend-shell`
- `chore/v2-observability`
- `fix/v2-hardening`

## Review Checklist

Before opening a PR:

- branch name follows the type rule
- commit history is grouped by concern
- tests for the touched area were run
- docs changed with the code when behavior changed
- PR body explains scope, non-goals, and test evidence

Before merging into `develop`:

- no unrelated file churn
- no opportunistic refactors outside the PR scope
- follow-up work is explicitly deferred to another branch
