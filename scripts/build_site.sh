#!/bin/sh
# Build the deployable site into ./book (gitignored).
#
# Also stages the attribution and licence next to the book, because the
# rendered site itself contains neither: ATTRIBUTION.md and license-MIT are
# project files, not chapters, so mdBook never sees them. Publishing the book
# without them would drop the MIT notice and the "unofficial translation"
# disclaimer.
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"

rm -rf book
mdbook build

cp ATTRIBUTION.md book/ATTRIBUTION.md
cp license-MIT book/license-MIT

echo "site built: $root/book"
