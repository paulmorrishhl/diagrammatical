# Decision 0001: Root-level Claude Code plugin packaging

Status: accepted for Milestone 1

Diagrammatical is packaged as a single plugin rooted at the repository root. Claude Code's default `commands/` and `skills/` locations remain thin wrappers around one shared skill rather than duplicating workflow instructions. The marketplace entry uses `./` because the marketplace and plugin share a repository.

The specification also reserves `.agents/plugins/marketplace.json`. Milestone 1 includes that catalog as an empty compatibility placeholder, because Codex packaging is explicitly outside v1 and adding a second plugin manifest would expand the supported-platform scope. A future platform milestone can add an installable entry without changing the Claude Code package.

