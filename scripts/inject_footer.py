#!/usr/bin/env python3
"""Append the translation notice to every rendered page.

ATTRIBUTION.md and license-MIT are project files rather than chapters, so
mdBook never renders them and the published site would otherwise carry neither
the MIT notice nor the "unofficial translation" disclaimer. Injecting here
keeps src/ byte-identical to what verify_translation.py checks.
"""
import sys
from pathlib import Path

MARKER = "data-translation-notice"

FOOTER = (
    '<hr>\n'
    f'<p {MARKER} style="font-size:0.85em;opacity:0.75;line-height:1.7">'
    '本站为 <em>Learning Rust With Entirely Too Many Linked Lists</em> 的'
    '<strong>非官方</strong>中文翻译，不代表原作者，也未获其认可。<br>'
    '原作 Aria Desires · '
    '原项目 <a href="https://github.com/rust-unofficial/too-many-lists">rust-unofficial/too-many-lists</a> · '
    '以 <a href="license-MIT">MIT 许可证</a> 发布 · '
    '<a href="ATTRIBUTION.md">完整署名说明</a>'
    '</p>\n'
)


def inject(path):
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return False
    for anchor in ("</main>", "</body>"):
        if anchor in text:
            head, sep, tail = text.rpartition(anchor)
            path.write_text(head + FOOTER + sep + tail, encoding="utf-8")
            return True
    return False


def main(argv):
    if len(argv) != 2:
        print(f"usage: {argv[0]} SITE_DIR", file=sys.stderr)
        return 2
    pages = sorted(Path(argv[1]).rglob("*.html"))
    if not pages:
        print(f"no HTML found under {argv[1]}", file=sys.stderr)
        return 1
    done = sum(inject(page) for page in pages)
    print(f"translation notice added to {done}/{len(pages)} pages")
    return 0 if done == len(pages) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
