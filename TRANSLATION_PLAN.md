# Chinese mdBook Translation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` or `executing-plans` to implement this plan task-by-task. Each translation batch is independently reviewable and must pass the structural checks before the next batch begins.

**Goal:** Create an unofficial Chinese translation of `/home/mofeng/book-trans/too-many-lists` in `/home/mofeng/book-trans/too-many-lists-cn`, preserving mdBook navigation, runnable Rust examples, source attribution, and the original project layout.

**Architecture:** Build an independent sibling mdBook with the same `src/` Markdown filenames and relative paths as the source. Translate prose, headings, visible link labels, and explanatory text; preserve code, commands, compiler output, URLs, link destinations, and image paths. Copy the companion Rust crate unchanged so readers can use the translated book with the same examples.

**Tech Stack:** mdBook, Markdown, Rust/Cargo, Python 3 standard library for structural validation, Git.

## Global Constraints

- Source baseline: Git commit `1b0b264d9a64d436aaed361a360cb738be88c4c6`.
- Source content: 59 Markdown files under `src/`, totaling 14,267 lines.
- `src/SUMMARY.md` remains a 60-line file with the same 58 entries, destinations, ordering, and nesting.
- Preserve every source Markdown filename and every image path.
- Preserve every fenced block byte-for-byte, including fence markers, info strings, code, comments, whitespace, diagnostics, and output.
- Preserve inline Rust identifiers, API names, lifetimes, trait names, commands, versions, paths, URLs, and compiler error codes.
- Translate prose, headings, visible link labels, image alt text, and explanatory text outside code/output blocks.
- Keep the original informal, humorous, and sarcastic tone where it appears in the source.
- Do not silently correct historical source behavior, old compiler output, source typos, or labels such as `TODO`.
- Retain `license-MIT` unchanged and include the original author attribution.
- Do not copy `.github/workflows/main.yml`; it deploys the original repository rather than the translated sibling.
- Do not commit generated `book/`, `lists/target/`, Python cache, or other build artifacts.

## Source Inventory

- Configuration: `too-many-lists/book.toml`
- Book navigation: `too-many-lists/src/SUMMARY.md`
- Introduction: `src/README.md`
- First stack: `src/first.md`, `src/first-layout.md`, `src/first-new.md`, `src/first-ownership.md`, `src/first-push.md`, `src/first-pop.md`, `src/first-test.md`, `src/first-drop.md`, `src/first-final.md`
- Second stack: `src/second.md`, `src/second-option.md`, `src/second-generic.md`, `src/second-peek.md`, `src/second-into-iter.md`, `src/second-iter.md`, `src/second-iter-mut.md`, `src/second-final.md`
- Persistent stack: `src/third.md`, `src/third-layout.md`, `src/third-basics.md`, `src/third-drop.md`, `src/third-arc.md`, `src/third-final.md`
- Safe deque: `src/fourth.md`, `src/fourth-layout.md`, `src/fourth-building.md`, `src/fourth-breaking.md`, `src/fourth-peek.md`, `src/fourth-symmetry.md`, `src/fourth-iteration.md`, `src/fourth-final.md`
- Unsafe queue: `src/fifth.md`, `src/fifth-layout.md`, `src/fifth-unsafe.md`, `src/fifth-basics.md`, `src/fifth-miri.md`, `src/fifth-stacked-borrows.md`, `src/fifth-testing-stacked-borrows.md`, `src/fifth-layout-basics-redux.md`, `src/fifth-extras.md`, `src/fifth-final.md`
- Production deque: `src/sixth.md`, `src/sixth-layout.md`, `src/sixth-variance.md`, `src/sixth-basics.md`, `src/sixth-panics.md`, `src/sixth-combinatorics.md`, `src/sixth-random-bits.md`, `src/sixth-testing.md`, `src/sixth-send-sync.md`, `src/sixth-cursors-intro.md`, `src/sixth-cursors-impl.md`, `src/sixth-cursors-testing.md`, `src/sixth-final.md`
- Bonus lists: `src/infinity.md`, `src/infinity-double-single.md`, `src/infinity-stack-allocated.md`
- Images: `src/img/indy.gif`, `src/img/profbee.gif`
- Rust companion crate: `lists/Cargo.toml` and 8 files under `lists/src/`
- Root project documentation: `README.md`
- License: `license-MIT`

## Approach Decision

Three possible execution paths were considered:

1. **One-pass bulk translation:** fastest to start, but it makes terminology drift, broken fences, and hard-to-review errors likely across roughly 14k lines.
2. **Manual file-by-file translation without tooling:** gives close editorial control, but repeated structural checks are easy to skip and omissions are difficult to detect.
3. **Recommended: copied baseline plus validator and chapter batches:** first copy the complete book structure, add a structural validator, then translate small dependency-ordered batches. This keeps every batch reviewable, catches changed code or links mechanically, and allows independent batches to be assigned to separate workers when their files do not overlap.

The recommended route is a translation workflow, not machine translation followed by a single cleanup pass. A translator may use automation for inventory and structural comparison, but every batch must receive human terminology and Markdown review.

## Target Layout

Create the following target structure:

```text
too-many-lists-cn/
├── .gitignore
├── ATTRIBUTION.md
├── README.md
├── SOURCE_COMMIT.txt
├── TRANSLATION_GLOSSARY.md
├── TRANSLATION_MANIFEST.tsv
├── TRANSLATION_PLAN.md
├── book.toml
├── license-MIT
├── lists/
├── scripts/verify_translation.py
├── tests/test_verify_translation.py
└── src/
    ├── SUMMARY.md
    ├── README.md
    ├── first*.md through sixth*.md
    ├── infinity*.md
    └── img/indy.gif and profbee.gif
```

The target must contain exactly the same 59 Markdown paths under `src/` as the source. Root `README.md`, `ATTRIBUTION.md`, the glossary, manifest, plan, and validation tools are project files, not additional mdBook chapters.

## Dependency Graph

```text
Task 0: target metadata and source baseline
  -> Task 1: copied mdBook and Rust assets
  -> Task 2: structural validator and tests
  -> Task 3: glossary, attribution, metadata, and navigation
  -> Batch 1: introduction and first stack
  -> Batches 2 and 3: second and persistent stacks
  -> Batch 4: safe deque
  -> Batches 5a through 5d: unsafe queue
  -> Batches 6a through 6h: production deque
  -> Batch 7: bonus lists
  -> Task 4: final validation and handoff
```

Translation batches may run in parallel only when they own disjoint files and the shared glossary is already fixed. The dependency order remains the review order because later chapters use terminology and concepts introduced earlier.

## Implementation Tasks

### Task 0: Initialize Target Baseline

**Files:** Create `SOURCE_COMMIT.txt`, `.gitignore`, and this plan in `too-many-lists-cn/`.

- Record `1b0b264d9a64d436aaed361a360cb738be88c4c6` in `SOURCE_COMMIT.txt`.
- Add `/book/`, `/lists/target/`, `__pycache__/`, and `*.pyc` to `.gitignore`.
- Initialize a separate Git repository in `too-many-lists-cn` if commit-level batch tracking is desired.
- Commit only the baseline planning files with message `chore: initialize Chinese translation workspace`.

Completion criterion: the target records the exact source baseline and no generated files are tracked.

### Task 1: Copy the Structural Baseline

**Files:** Copy source `book.toml`, `src/`, `lists/`, `license-MIT`, and both GIFs into `too-many-lists-cn/`; create root `README.md` as a copy of the source project README before translation.

- Keep all source Markdown paths and all Rust paths.
- Copy `lists/` byte-for-byte; do not translate Rust comments or identifiers in this phase.
- Copy `src/img/indy.gif` and `src/img/profbee.gif` byte-for-byte.
- Leave `.github/workflows/main.yml` out of the target.

Completion criterion: the copied target has 59 Markdown files, 8 Rust files, 2 GIFs, and an unchanged license.

### Task 2: Add Structural Validation Before Translation

**Files:** Create `scripts/verify_translation.py` and `tests/test_verify_translation.py`.

Implement this command-line interface:

```bash
python3 scripts/verify_translation.py \
  /home/mofeng/book-trans/too-many-lists \
  /home/mofeng/book-trans/too-many-lists-cn
```

The validator must return nonzero when any of these invariants fails:

- Source and target Markdown path sets differ.
- Any fenced block differs, including opening fence, info string, body, or closing fence. Support both backtick and tilde fences if present.
- Any inline or reference Markdown link destination differs.
- Any image destination differs.
- Any copied asset has a different SHA-256 hash.
- `SUMMARY.md` has a different sequence of local destinations.

It must allow prose, headings, visible link labels, and image alt text to differ. Write `unittest` cases first for prose-only changes passing, code-fence changes failing, text/compiler-output changes failing, missing pages failing, changed URLs failing, changed image bytes failing, and changed summary destinations failing. Run the tests once before implementation to record the expected red state, then implement the smallest standard-library validator that makes them pass.

Completion criterion: the validator tests pass and the validator passes against the untouched copied baseline.

### Task 3: Establish Editorial and mdBook Metadata

**Files:** Modify `book.toml`, `src/SUMMARY.md`, and `README.md`; create `ATTRIBUTION.md`, `TRANSLATION_GLOSSARY.md`, and `TRANSLATION_MANIFEST.tsv`.

Keep these `book.toml` settings unchanged:

```toml
author = "Aria Desires"
build-dir = "book"
create-missing = false
git-repository-url = "https://github.com/rust-unofficial/too-many-lists"
limit-results = 30
```

Use these translated metadata values:

```toml
title = "用完全太多的链表学习 Rust"
description = "用完全太多的链表学习 Rust"
```

Translate only visible labels in `SUMMARY.md`. Keep every destination filename, entry order, indentation, and local-link sequence unchanged. The root README must retain the exact commands `cargo install mdbook` and `mdbook build`.

Use these canonical glossary forms: 链表, 单向链表, 双向链表, 栈, 队列, 双端队列, 节点, 堆分配, 栈分配, 所有权, 借用, 借用检查器, 共享引用, 可变引用, 原始指针, 内部可变性, 生命周期, 型变, 协变, 逆变, 不变性, 子类型关系, 析构函数, panic 安全性, 未定义行为, 空指针优化, 零大小类型, 迭代器, 游标, 标记特征, 编译测试, 文档测试, and `Stacked Borrows（堆叠借用）`.

Always preserve exact API and tool spellings: `Box`, `Rc`, `Arc`, `Option`, `Vec`, `VecDeque`, `Cell`, `RefCell`, `UnsafeCell`, `NonNull`, `PhantomData`, `Send`, `Sync`, `Miri`, `rustc`, `Cargo`, `rustup`, and `mdBook`.

`ATTRIBUTION.md` must identify this as an unofficial Chinese translation of *Learning Rust With Entirely Too Many Linked Lists* by Aria Desires, link `https://github.com/rust-unofficial/too-many-lists`, state that source and code remain under the MIT license, and make no official-status claim.

The manifest must have one row per source Markdown path with columns `relative_path`, `source_lines`, `target_path`, `batch`, and `status`; initial status is `source-copied`.

Completion criterion: a new reader can identify the source, license, terminology policy, navigation, and every translation unit without reading source internals.

## Translation Batches

For each batch, read the source files and glossary, translate only text outside protected regions, run the validator and unit tests, run `mdbook build` when the command is installed, run `git diff --check`, update only that batch's manifest rows, and make one atomic commit. Use source filenames as target filenames.

### Batch 1: Introduction and First Stack

**Files:** `src/README.md`, `src/first.md`, `src/first-layout.md`, `src/first-new.md`, `src/first-ownership.md`, `src/first-push.md`, `src/first-pop.md`, `src/first-test.md`, `src/first-drop.md`, `src/first-final.md`.

Blocked by Tasks 0-3. Commit as `docs(zh): translate introduction and first stack`.

### Batch 2: Second Stack

**Files:** `src/second.md`, `src/second-option.md`, `src/second-generic.md`, `src/second-peek.md`, `src/second-into-iter.md`, `src/second-iter.md`, `src/second-iter-mut.md`, `src/second-final.md`.

Blocked by Batch 1. Commit as `docs(zh): translate second stack`.

### Batch 3: Persistent Stack

**Files:** `src/third.md`, `src/third-layout.md`, `src/third-basics.md`, `src/third-drop.md`, `src/third-arc.md`, `src/third-final.md`.

Blocked by Batch 1. This batch may be translated in parallel with Batch 2. Commit as `docs(zh): translate persistent stack`.

### Batch 4: Safe Deque

**Files:** `src/fourth.md`, `src/fourth-layout.md`, `src/fourth-building.md`, `src/fourth-breaking.md`, `src/fourth-peek.md`, `src/fourth-symmetry.md`, `src/fourth-iteration.md`, `src/fourth-final.md`.

Blocked by Batches 2 and 3. Commit as `docs(zh): translate safe deque`.

### Batch 5a: Unsafe Queue Core

**Files:** `src/fifth.md`, `src/fifth-layout.md`, `src/fifth-unsafe.md`, `src/fifth-basics.md`.

Blocked by Batch 4. Commit as `docs(zh): translate unsafe queue core`.

### Batch 5b: Miri and Stacked Borrows

**Files:** `src/fifth-miri.md`, `src/fifth-stacked-borrows.md`.

Blocked by Batch 5a. Commit as `docs(zh): translate miri and stacked borrows`.

### Batch 5c: Stacked Borrows Tests

**Files:** `src/fifth-testing-stacked-borrows.md`.

Blocked by Batch 5b. Commit as `docs(zh): translate stacked borrows tests`.

### Batch 5d: Queue Completion

**Files:** `src/fifth-layout-basics-redux.md`, `src/fifth-extras.md`, `src/fifth-final.md`.

Blocked by Batch 5c. Commit as `docs(zh): complete unsafe queue translation`.

### Batch 6a: Production Deque Foundations

**Files:** `src/sixth.md`, `src/sixth-layout.md`, `src/sixth-variance.md`, `src/sixth-basics.md`, `src/sixth-panics.md`.

Blocked by Batch 5d. Commit as `docs(zh): translate production deque foundations`.

### Batch 6b: Combinatorics

**Files:** `src/sixth-combinatorics.md`.

Blocked by Batch 6a. Commit as `docs(zh): translate deque combinatorics`.

### Batch 6c: Random Bits

**Files:** `src/sixth-random-bits.md`.

Blocked by Batch 6b. Commit as `docs(zh): translate deque random bits`.

### Batch 6d: Testing and Thread Traits

**Files:** `src/sixth-testing.md`, `src/sixth-send-sync.md`.

Blocked by Batch 6c. Commit as `docs(zh): translate deque testing and thread traits`.

### Batch 6e: Cursor Introduction

**Files:** `src/sixth-cursors-intro.md`.

Blocked by Batch 6d. Commit as `docs(zh): translate cursor introduction`.

### Batch 6f: Cursor Implementation

**Files:** `src/sixth-cursors-impl.md`.

Blocked by Batch 6e. Commit as `docs(zh): translate cursor implementation`.

### Batch 6g: Cursor Tests

**Files:** `src/sixth-cursors-testing.md`.

Blocked by Batch 6f. Commit as `docs(zh): translate cursor tests`.

### Batch 6h: Production Deque Final Code

**Files:** `src/sixth-final.md`.

Blocked by Batch 6g. Commit as `docs(zh): translate production deque final code`.

### Batch 7: Bonus Lists

**Files:** `src/infinity.md`, `src/infinity-double-single.md`, `src/infinity-stack-allocated.md`.

Blocked by Batch 6h. Commit as `docs(zh): translate bonus lists`.

## Per-Batch Review Rules

Review every batch against these rules before marking it translated:

- Markdown headings, prose, blockquote narration, visible link labels, and image alt text are Chinese and preserve the source meaning and tone.
- Fenced code and output are unchanged byte-for-byte; this includes Rust, `rust,ignore`, shell, text, compiler diagnostics, and comments inside fences.
- Inline code is unchanged unless it is ordinary prose text that is not an identifier, command, path, API, or diagnostic.
- Markdown destination URLs, local chapter paths, reference definitions, and image filenames are unchanged.
- Relative links point to existing target files, and `SUMMARY.md` still describes the complete book.
- Technical terms use `TRANSLATION_GLOSSARY.md`; new terms are added there before use rather than silently creating competing translations.
- No batch changes `lists/` Rust source, assets, license text, or unrelated metadata.
- No generated files or formatting-only churn are included in the batch commit.

## Final Validation

Run from `too-many-lists-cn/`:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/verify_translation.py \
  /home/mofeng/book-trans/too-many-lists \
  /home/mofeng/book-trans/too-many-lists-cn
git diff --check
test "$(rg --files src -g '*.md' | wc -l)" -eq 59
test "$(rg --files src/img | wc -l)" -eq 2
test "$(rg --files lists/src -g '*.rs' | wc -l)" -eq 8
```

When mdBook is installed, build to an external destination so generated HTML is not mixed with the source tree:

```bash
mdbook --version
mdbook build /home/mofeng/book-trans/too-many-lists-cn \
  --dest-dir /tmp/too-many-lists-cn-book
test -f /tmp/too-many-lists-cn-book/index.html
```

`SUMMARY.md` is mandatory for the build and controls chapter inclusion, order, hierarchy, and relative paths. `create-missing = false` must remain enabled so a missing translated page fails instead of being silently created. `mdbook test` is supplementary because it tests Rust code blocks, not translation completeness or all Markdown links.

Also verify unchanged companion material:

```bash
diff -ru --exclude=target \
  /home/mofeng/book-trans/too-many-lists/lists \
  /home/mofeng/book-trans/too-many-lists-cn/lists
cmp /home/mofeng/book-trans/too-many-lists/license-MIT \
  /home/mofeng/book-trans/too-many-lists-cn/license-MIT
sha256sum /home/mofeng/book-trans/too-many-lists/src/img/indy.gif \
  /home/mofeng/book-trans/too-many-lists-cn/src/img/indy.gif
sha256sum /home/mofeng/book-trans/too-many-lists/src/img/profbee.gif \
  /home/mofeng/book-trans/too-many-lists-cn/src/img/profbee.gif
cargo test --manifest-path /home/mofeng/book-trans/too-many-lists-cn/lists/Cargo.toml
```

The last Cargo command is required only when Rust/Cargo is available; because the crate is copied unchanged, any failure must be compared with the source crate before being treated as a translation defect.

## Acceptance Criteria

- `too-many-lists-cn/src/` contains exactly the source's 59 Markdown paths.
- `SUMMARY.md` has the same 58 destinations, order, and nesting as the source.
- All pages referenced by `SUMMARY.md` exist and mdBook does not create missing files.
- All fenced code/output blocks, commands, URLs, local destinations, reference destinations, and image paths are unchanged.
- Both GIFs, the `lists/` crate, and `license-MIT` are byte-identical to the source.
- `ATTRIBUTION.md` identifies Aria Desires, the original title and repository, unofficial status, and MIT licensing.
- The glossary is used consistently across all translated batches.
- Validator unit tests pass, and the validator passes against the completed trees.
- `git diff --check` reports no whitespace errors.
- `mdbook build` succeeds when mdBook is installed and produces `index.html` in the external destination.
- Each translation batch has one atomic commit, and generated build output is absent from Git history.

## References

- Source repository: https://github.com/rust-unofficial/too-many-lists
- mdBook build command: https://rust-lang.github.io/mdBook/cli/build.html
- mdBook `SUMMARY.md` format: https://rust-lang.github.io/mdBook/format/summary.html
- mdBook general configuration: https://rust-lang.github.io/mdBook/format/configuration/general.html
- mdBook test command: https://rust-lang.github.io/mdBook/cli/test.html
