#!/usr/bin/env python3
import hashlib
import re
import sys
from pathlib import Path


FENCE_RE = re.compile(r"^((?:(?: {0,3}> ?)+| {0,3}))(`{3,}|~{3,})([^\n]*)(\n?)$")
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(\s*<?([^\s)>]+)>?[^)]*\)")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(\s*<?([^\s)>]+)>?[^)]*\)")
REFERENCE_RE = re.compile(r"^\s*\[[^]]+\]:\s*<?([^\s>]+)>?", re.MULTILINE)
HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s")
LIST_ITEM_RE = re.compile(r"^\s*([*+-]|\d+[.)])\s")
BLOCKQUOTE_RE = re.compile(r"^ {0,3}>")
TRANSLATED_METADATA = {"book.toml"}


def markdown_paths(root):
    return {
        path.relative_to(root).as_posix() for path in root.rglob("*.md")
    }


def fences(text, path):
    result = []
    lines = text.splitlines(keepends=True)
    index = 0
    while index < len(lines):
        match = FENCE_RE.match(lines[index])
        if not match:
            index += 1
            continue
        _prefix, marker, _info, _newline = match.groups()
        character = marker[0]
        closing = None
        for end in range(index + 1, len(lines)):
            candidate = lines[end]
            closing_match = FENCE_RE.match(candidate)
            if not closing_match or closing_match.group(2)[0] != character:
                continue
            candidate_body = closing_match.group(2)
            if len(candidate_body) >= len(marker) and not closing_match.group(3).strip():
                closing = end
                break
        if closing is None:
            raise ValueError(f"{path}: unterminated {character} fence at line {index + 1}")
        result.append((lines[index], tuple(lines[index + 1:closing]), lines[closing]))
        index = closing + 1
    return result


def block_structure(text):
    """Block-level markers outside fenced blocks.

    Returns the sequence of heading levels, the number of list items, and the
    number of blockquote blocks. Counting blockquote *blocks* rather than lines
    lets a translator re-wrap a quotation without tripping the check, while a
    dropped `>` marker still collapses the block and fails.
    """
    headings = []
    items = 0
    quote_blocks = 0
    in_quote = False
    in_fence = False
    fence_character = None
    for line in text.splitlines():
        match = FENCE_RE.match(line + "\n")
        if match:
            character = match.group(2)[0]
            if not in_fence:
                in_fence, fence_character = True, character
            elif character == fence_character:
                in_fence, fence_character = False, None
            continue
        if in_fence:
            continue
        if BLOCKQUOTE_RE.match(line):
            if not in_quote:
                quote_blocks += 1
                in_quote = True
            continue
        in_quote = False
        heading = HEADING_RE.match(line)
        if heading:
            headings.append(len(heading.group(1)))
            continue
        if LIST_ITEM_RE.match(line):
            items += 1
    return tuple(headings), items, quote_blocks


def protected_links(text):
    links = [("inline link", match.group(1)) for match in LINK_RE.finditer(text)]
    images = [("image", match.group(1)) for match in IMAGE_RE.finditer(text)]
    references = [("reference link", match.group(1)) for match in REFERENCE_RE.finditer(text)]
    return links, images, references


def compare(source, target):
    errors = []
    if not (target / "book.toml").is_file():
        errors.append("Missing target book.toml")
    source_md_root, target_md_root = source / "src", target / "src"
    source_paths, target_paths = markdown_paths(source_md_root), markdown_paths(target_md_root)
    if source_paths != target_paths:
        errors.append(f"Markdown paths differ: missing={sorted(source_paths - target_paths)}, extra={sorted(target_paths - source_paths)}")
    for relative in sorted(source_paths & target_paths):
        source_text = (source_md_root / relative).read_text(encoding="utf-8")
        target_text = (target_md_root / relative).read_text(encoding="utf-8")
        try:
            source_fences, target_fences = fences(source_text, relative), fences(target_text, relative)
        except ValueError as error:
            errors.append(str(error)); continue
        if source_fences != target_fences:
            errors.append(f"{relative}: fenced blocks differ")
        source_protected = protected_links(source_text)
        target_protected = protected_links(target_text)
        if source_protected != target_protected:
            errors.append(f"{relative}: protected link or image destinations differ")
        source_structure = block_structure(source_text)
        target_structure = block_structure(target_text)
        if source_structure != target_structure:
            errors.append(
                f"{relative}: block structure differs "
                f"(headings/list items/blockquotes {source_structure} != {target_structure})"
            )
    source_summary_path, target_summary_path = source / "src/SUMMARY.md", target / "src/SUMMARY.md"
    if source_summary_path.exists() and target_summary_path.exists():
        source_summary = protected_links(source_summary_path.read_text(encoding="utf-8"))[0]
        target_summary = protected_links(target_summary_path.read_text(encoding="utf-8"))[0]
        if [destination for _, destination in source_summary if not destination.startswith(("http://", "https://", "mailto:"))] != [destination for _, destination in target_summary if not destination.startswith(("http://", "https://", "mailto:"))]:
            errors.append("SUMMARY.md: local destinations differ")
    excluded_directories = {".git", ".github", ".superpowers", "book"}
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if not path.is_file() or path.suffix.lower() == ".md" or path.name == ".gitignore" or relative.as_posix() in TRANSLATED_METADATA or any(part in excluded_directories for part in relative.parts) or relative.parts[:2] == ("lists", "target"):
            continue
        counterpart = target / relative
        if not counterpart.is_file():
            errors.append(f"Missing copied asset: {relative}")
            continue
        if hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(counterpart.read_bytes()).digest():
            errors.append(f"Asset SHA-256 differs: {relative}")
    return errors


def main(argv):
    if len(argv) != 3:
        print(f"usage: {argv[0]} SOURCE TARGET", file=sys.stderr)
        return 2
    errors = compare(Path(argv[1]), Path(argv[2]))
    if errors:
        print("Translation verification failed:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print("Translation structure verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
