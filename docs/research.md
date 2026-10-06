# Related-work research

Research date: 2026-10-06. This is a bounded discovery record, **not proof that no equivalent project exists**. Public search indexes can miss repositories or recent features. There is no claim of worldwide originality, affiliation, or program eligibility.

## Search method

Public web searches used the phrases `"AGENTS.md" "diff" "instructions" CLI`, `"AGENTS.md" "lint" "scope" tools`, and `"agent-context-diff"`. GitHub repository-name search for `instruction-impact` returned seven loosely matching repository names, none of the returned descriptions identified this use case. That is a naming check, not an exhaustive functionality search.

The following distinctions are based on the public documentation surfaced in that search, not exhaustive source audits:

| Project | Documented focus | Our narrower focus |
| --- | --- | --- |
| [AGENTS.md](https://agents.md/) | Cross-agent instruction format and nested guidance | Analyze source-scope transitions between commits, not define a new format |
| [YawLabs/ctxlint](https://github.com/YawLabs/ctxlint) | Context linting, broken paths, stale commands, contradictions, session/config auditing | Enumerate unchanged files whose ancestor instruction sources changed |
| [mikiships/agentmd](https://github.com/mikiships/agentmd) | Generate, score, diff against generated context, detect drift | Compare actual committed instructions without generating replacements or calling a model |
| [codeprakhar25/agentdiff](https://github.com/codeprakhar25/agentdiff) | Agent code attribution, signed traces, commit-scoped provenance | Instruction inheritance impact without capturing sessions or attributing code |

## Chosen gap

The specific question is: **Which tracked files have a different root-to-parent `AGENTS.md` source chain between these two commits, even when their own content is unchanged?**

The researched documentation did not identify an exact match for that workflow. This is useful for reviewing agent-guidance changes in monorepos, but it is a modest, focused tool, not a new agent framework. Contributions that identify closer related work are welcome.

## OpenAI program fact check

The official [Codex for Open Source page](https://developers.openai.com/community/codex-for-oss), fetched on the research date, offers selected maintainers six months of ChatGPT Pro with Codex, conditional Codex Security access, and API credits. It invites core maintainers or maintainers of widely used public projects, while allowing other ecosystem-important projects to explain their value.

The [application](https://openai.com/form/codex-for-oss/) asks for a public GitHub profile/repository, maintainer role, and evidence such as stars, downloads, or ecosystem importance. A freshly created repository is not by itself evidence of adoption. No application has been submitted by this project and acceptance is not promised.
