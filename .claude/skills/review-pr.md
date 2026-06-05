---
name: review-pr
description: |
  Review a pull request by analyzing the diff between branches. Produces a structured review
  with a summary, inline code comments, severity-tagged findings (CRITICAL/IMPORTANT/MINOR/NIT),
  and a clear APPROVE or REJECT verdict. Use when someone asks to review a PR, asks for
  code review, or references a PR number/URL for review.
---

# PR Review Command

Review the specified pull request. If a PR number or URL is provided as an argument, use it.
Otherwise, detect the current branch's open PR.

## Steps

1. **Identify the PR**: Use `gh pr view` to get PR metadata (title, body, base branch, head
   branch, author). If no PR number was given, use `gh pr view --json number` on the current
   branch.

2. **Fetch existing comments** (always do this first to avoid duplication):
   ```bash
   gh pr view <number> --comments                              # PR-level comments
   gh api repos/{owner}/{repo}/pulls/<number>/comments        # inline code comments
   ```
   Do not raise a finding that has already been flagged by another reviewer or a previous
   Claude review.

3. **Extract linked issue context**:
   ```bash
   gh pr view <number> --json body | grep -oE '#[0-9]+'
   ```
   Use any linked issues to understand the intent of the PR before analyzing changes.

4. **Fetch the diff**: Run `gh pr diff <number>` to get the full diff. For large diffs,
   focus on the most impactful files first.

5. **Analyze the changes** using the review criteria and domain-specific checks below.
   Read surrounding code for context — never review lines in isolation.

6. **Produce the review** using the output format below:
   - **Summary**: 2-4 sentences on what the PR does and why. MUST appear at the top.
   - **Findings**: list each issue with severity, referencing specific files and line numbers.
     Use a single continuous numbering sequence across ALL sections (1, 2, 3… never restart
     at 1 per section).
   - **Verdict**: either `APPROVE` or `REJECT until <blockers>`.
     Even on APPROVE, list non-blocking warnings/nits as feedback.

7. **Post the review** using the formal GitHub review mechanism:
   ```bash
   # APPROVE verdict (no CRITICAL or IMPORTANT blockers):
   gh pr review <number> --approve --body "<review text>"

   # REJECT verdict (has CRITICAL or IMPORTANT blockers):
   gh pr review <number> --request-changes --body "<review text>"

   # Suggestions only (no verdict change needed):
   gh pr review <number> --comment --body "<review text>"
   ```
   `--approve` and `--request-changes` count toward branch protection rules.
   Use `--comment` only when there are no blockers and no approval is being granted yet.

   Post inline comments on specific diff lines where relevant using `gh api`.

   Always include the reviewed-at SHA in the review footer (see output format).

---

## Severity definitions

### 🔴 CRITICAL ISSUES (must fix before merge)
- Logic bugs that affect model optimization correctness
- Quantization accuracy regressions (wrong dtype, broken STE, bad observer logic)
- FX graph transformations that break semantics or silently drop nodes
- Security vulnerabilities (command injection, unsafe deserialization, leaked secrets)
- Breaking changes to public API without a migration path
- Missing tests for new non-trivial logic
- Data loss or corruption risks in calibration/export flows

### 🟡 IMPORTANT ISSUES (should fix before merge)
- Missing edge-case handling that could cause runtime errors
- Performance regressions (unnecessary copies, redundant passes)
- Incomplete error messages that would make debugging hard
- Test coverage gaps for important branches

### 🔵 MINOR ISSUES (nice to have, can address in PR or later)
- Naming suggestions
- Minor documentation improvements
- Small refactoring opportunities

### 💭 SUGGESTIONS & NITPICKS (optional improvements)
- Cap: report at most 5 suggestions per review. If more exist, say "plus N similar items".

---

## Do NOT report
- Style/formatting (CI runs ruff)
- Type annotation issues (CI runs mypy)
- Lockfile or generated file changes
- Trailing whitespace, EOF newlines (pre-commit handles these)
- Issues that already exist in the codebase before this PR (pre-existing debt)

---

## Always check
- New quantization passes have corresponding tests
- FX graph rewrites preserve node metadata and tensor shapes
- Changes to `api/config.py` or public API are backward-compatible or documented as breaking
- Calibration data handling doesn't introduce data leaks between train/val
- New custom ops in `axnn/` have numerical correctness tests
- Hardware capability DB changes (`intermediate_representation/`) are versioned
- New model architectures in `axelera-transformers` implement `get_torch_export_data()` correctly

---

## Output format

```
**PR REVIEW - Summary**

<what is this PR and why was it needed, 2-4 sentences>

**🔴 CRITICAL ISSUES** (must fix before merge)

1. [Issue description] - `file:line` - [Specific recommendation]
2. [Issue description] - `file:line` - [Specific recommendation]

**🟡 IMPORTANT ISSUES** (should fix before merge)

3. [Issue description] - `file:line` - [Specific recommendation]

**🔵 MINOR ISSUES** (nice to have, can address in PR or later)

4. [Issue description] - `file:line` - [Suggestion]

**💭 SUGGESTIONS & NITPICKS** (optional improvements)

5. [Suggestion with rationale]

**✅ POSITIVE FEEDBACK** (things done well)

- [Specific praise for good practices]

## Verdict
APPROVE | REJECT until <reasons>

<!-- reviewed-at: <git rev-parse HEAD> "<git log -1 --format=%s HEAD>" -->
```

---

## Re-review Mode

When `Review mode: re-review` is set in the prompt, follow these steps instead of the
initial review steps above.

### Steps

1. **Fetch the previous Claude review and extract the reviewed-at SHA**:
   The Claude GitHub App bot login is `claude[bot]` (app slug: `claude`, owned by `anthropics`).
   ```bash
   gh api repos/{owner}/{repo}/pulls/<number>/reviews \
     --jq '[.[] | select(.user.login == "claude[bot]")] | last | .body' \
   | grep -oP '(?<=reviewed-at: )[^\s]+'
   ```
   The `reviewed-at` footer contains both the SHA and the commit title (see output format).
   Extract only the SHA portion (first token before the space).

2. **Fetch existing comments** (same as initial review, to avoid duplication):
   ```bash
   gh pr view <number> --comments
   gh api repos/{owner}/{repo}/pulls/<number>/comments
   ```

3. **Diff from the last reviewed commit to HEAD**:
   ```bash
   git diff <extracted_sha>..HEAD
   ```
   This covers all commits pushed since the last review, regardless of how many there are.

4. **Always do a targeted re-check** of the findings flagged in the previous review.
   If the user explicitly requests a full re-review (e.g. `@claude full re-review`),
   run the initial review flow instead and note that it supersedes the previous one.

5. **Post the re-review**:
   - Use `--request-changes` if **new** CRITICAL or IMPORTANT blockers were introduced since the last review
   - Use `--comment` if previous blockers remain unresolved but no new ones were introduced
   - Use `--approve` only if **all** previous blockers are resolved and no new blockers were found

   The verdict is **mandatory** — never omit it in a re-review.

### Re-review output format

```
**RE-REVIEW - Summary**

<what changed since last review, 2-3 sentences>

---

**Finding Status** (from previous review)

1. [Original finding description] — ✅ Resolved — [brief note]
2. [Original finding description] — ❌ Still present — [what is still wrong]
3. [Original finding description] — ⚠️ Partially addressed — [what remains]

**New findings** (regressions or newly introduced issues)

4. [Issue] - `file:line` - [recommendation]

---

## Verdict
APPROVE | REJECT until <specific remaining blockers listed by finding number>

<!-- reviewed-at: <git rev-parse HEAD> "<git log -1 --format=%s HEAD>" -->
```
