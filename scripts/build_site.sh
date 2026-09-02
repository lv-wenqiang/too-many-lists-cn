#!/bin/sh
# Build the deployable site into ./book (gitignored).
#
# Also stages the attribution and licence next to the book and injects a notice
# into every page: ATTRIBUTION.md and license-MIT are project files rather than
# chapters, so mdBook never sees them, and publishing without them would drop
# the MIT notice and the "unofficial translation" disclaimer.
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"

rm -rf book
mdbook build

cp ATTRIBUTION.md book/ATTRIBUTION.md
cp license-MIT book/license-MIT
python3 scripts/inject_footer.py book

echo "site built: $root/book"
