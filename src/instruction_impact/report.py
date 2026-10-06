"""Human reports with bounded file lists and untrusted content fencing."""

import json
import re


def quoted(value):
    return json.dumps(value, ensure_ascii=True)


def fenced(value, language=""):
    longest = max((len(match) for match in re.findall(r"`+", value)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}{language}\n{value.rstrip(chr(10))}\n{fence}\n"


def file_state(item):
    if item["status"] != "existing":
        return item["status"]
    return "modified" if item["file_changed"] else "unchanged"


def render_text(report, max_files=20):
    summary = report["summary"]
    lines = [
        f"Instruction impact: {report['base'][:12]} -> {report['head'][:12]} [{report['profile']}]",
        f"{summary['instruction_changes']} instruction change(s); "
        f"{summary['affected_files']} affected file(s); "
        f"{summary['unchanged_files_affected']} with unchanged file content/mode.",
        "",
        "INSTRUCTION EDITS",
    ]
    for item in report["instruction_changes"]:
        lines.append(
            f"  [{item['kind']}] {quoted(item['path'])} — {len(item['affected_files'])} affected file(s)"
        )
        lines.append(f"    selection: {item['before_state']} -> {item['after_state']}")
    if not report["instruction_changes"]:
        lines.append("  No instruction source edits.")
    lines.extend(["", "CONTEXT TRANSITIONS"])
    for item in report["affected_files"][:max_files]:
        lines.append(f"  [{file_state(item)}] {quoted(item['path'])}")
        for cause in item["causes"]:
            lines.append(f"    {cause['kind']}: {quoted(cause['path'])}")
        for label in ("before", "after"):
            sources = " -> ".join(
                quoted(source["path"]) + "@" + source["blob"][:8] for source in item[label]
            )
            lines.append(f"    {label}: {sources or '(none)'}")
    if len(report["affected_files"]) > max_files:
        lines.append(
            f"  ... {len(report['affected_files']) - max_files} more; use --format json or increase --max-files."
        )
    if not report["affected_files"]:
        lines.append("  No file context transitions.")
    return "\n".join(lines) + "\n"


def render_markdown(report, max_files=20):
    summary = report["summary"]
    output = "# Instruction impact\n\n"
    output += f"**Instruction edits: {summary['instruction_changes']} · File context transitions: {summary['affected_files']} · Unchanged files affected: {summary['unchanged_files_affected']}**\n\n"
    output += "This is a repository source-scope report, not an agent prompt reconstruction or security verdict.\n\n"
    output += fenced(f"{report['base']} -> {report['head']}\nProfile: {report['profile']}", "text")
    files = {item["path"]: item for item in report["affected_files"]}
    for index, item in enumerate(report["instruction_changes"], 1):
        output += f"\n## {index}. Instruction edit ({item['kind']})\n\n"
        output += fenced(quoted(item["path"]), "text")
        output += f"\nSelection: **{item['before_state']} → {item['after_state']}**. {len(item['affected_files'])} file context transitions attributed to this source.\n\n"
        output += fenced(item["diff"] or "(source changed; no normalized text difference)", "diff")
        listing = [
            f"[{file_state(files[path])}] {quoted(path)}"
            for path in item["affected_files"][:max_files]
        ]
        if len(item["affected_files"]) > max_files:
            listing.append(
                f"... {len(item['affected_files']) - max_files} more (full list in JSON)"
            )
        output += "\n" + fenced(
            "\n".join(listing) or "No file context transitions attributed to this source.", "text"
        )
    output += "\n<details>\n<summary>File-level before/after chains</summary>\n\n"
    output += fenced(render_text(report, max_files), "text")
    output += "\n</details>\n"
    return output
