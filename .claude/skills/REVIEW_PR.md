---
name: review-pr
description: |
  Review a pull request by analyzing the diff between branches. Produces a structured review
  with a summary, inline code comments, severity-tagged findings (BLOCKER/MINOR/NIT),
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
   gh api repos/{owner}/{repo}/pulls/<number>/comments --paginate   # inline code comments
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

   **For every finding, determine whether it is pre-existing.**
   Use the diff from step 4 to make this judgment — the line markers (`+`, `-`,
   unchanged context) usually provide enough signal without reading additional files.
   When uncertain, lean toward **not pre-existing**.

   Pre-existing issues are informational only — this PR did not introduce them.
   Tag them 🟣 **PRE-EXISTING** and **never treat them as a blocker**.

6. **Produce the review** using the output format below:
   - **Summary**: 2-4 sentences on what the PR does and why. MUST appear at the top.
   - **Findings**: list each issue with severity, referencing specific files and line numbers.
     Use a single continuous numbering sequence across ALL sections (1, 2, 3… never restart
     at 1 per section).
   - **Verdict**: either `APPROVE` or `REJECT until <blockers>`.
     Even on APPROVE, list non-blocking minors/nits as feedback.
     🟣 Pre-existing findings **never count as blockers**, regardless of severity.

7. **Post the review** using the formal GitHub review mechanism:
   ```bash
   # APPROVE verdict (no BLOCKERs):
   gh pr review <number> --approve --body "<review text>"

   # REJECT verdict (has BLOCKERs):
   gh pr review <number> --request-changes --body "<review text>"
   ```
   `--approve` and `--request-changes` count toward branch protection rules.
   Always use one or the other — never use `--comment` as a substitute for a verdict.

   Always include the reviewed-at SHA in the review footer (see output format).

---

## Severity definitions

### 🔴 BLOCKER (must fix before merge)
- Logic bugs that affect model optimization correctness
- Quantization accuracy regressions (wrong dtype, broken STE, bad observer logic)
- FX graph transformations that break semantics or silently drop nodes
- Security vulnerabilities (command injection, unsafe deserialization, leaked secrets)
- Breaking changes to public API without a migration path
- Missing tests for new non-trivial logic
- Data loss or corruption risks in calibration/export flows
- Test coverage gaps for important branches

### 🟡 MINOR (non-blocking feedback)
- Missing edge-case handling that could cause runtime errors
- Performance regressions (unnecessary copies, redundant passes)
- Incomplete error messages that would make debugging hard
- Naming suggestions
- Minor documentation improvements
- Small refactoring opportunities

### 💭 SUGGESTIONS & NITPICKS (optional improvements)
- Cap: report at most 5 suggestions per review. If more exist, say the 5 most important ones.

---

## Do NOT report (CI handles these)

The following are enforced by CI checks that run in parallel with this review.
Do not duplicate their coverage — focus on logic, correctness, and design:

- Style/formatting (CI runs ruff)
- Type annotation issues (CI runs mypy)
- Lockfile or generated file changes
- Trailing whitespace, EOF newlines (pre-commit handles these)

Pre-existing issues must NOT be omitted — tag them 🟣 PRE-EXISTING (see analysis step 5).

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

**🔴 BLOCKERS** (must fix before merge)

1. [Issue description] - `file:line` - [Specific recommendation]
2. 🟣 Pre-existing: [Issue description] - `file:line` - [informational, not a blocker]

**🟡 MINOR ISSUES** (non-blocking feedback)

3. [Issue description] - `file:line` - [Suggestion]
4. 🟣 Pre-existing: [Issue description] - `file:line` - [informational]

**💭 SUGGESTIONS & NITPICKS** (optional improvements)

5. [Suggestion with rationale]

**✅ NOTABLE PATTERNS** (optional — only include if genuinely noteworthy)

Include only if the PR demonstrates a pattern worth highlighting for the team
(e.g., a clever test strategy, good use of an existing utility, well-structured
error handling). Skip this section entirely rather than writing generic praise.

## Verdict
APPROVE | REJECT until <reasons>

<!-- reviewed-at: <git rev-parse HEAD> "<git log -1 --format=%s HEAD>" -->
```

---

## Re-review Mode

When `Review mode: re-review` is set in the prompt, the triggering comment is also provided.
Read that comment and determine its intent before proceeding:

- **Override intent** — the commenter is asking Claude to stop treating one or more findings
  as blockers (e.g. "ignore finding 3", "point 5 is acceptable risk", "don't block on #2").
  → Follow the **Override Flow** below.

- **Re-review intent** — the commenter is asking Claude to re-examine the PR, typically
  after fixes have been pushed (e.g. "re-review", "take another look", "I fixed the issues").
  → Follow the **Re-review Flow** below.

- **Both** — the comment requests an override AND a re-review.
  → Apply the override(s) first, then run the Re-review Flow with the overrides in effect.

If the intent is unclear, default to the Re-review Flow.

---

### Override Flow

Any user can ask Claude to downgrade a blocking finding by posting a comment tagging
`@claude` and expressing the intent in natural language. No specific format is required —
Claude must understand the intent from context. Examples:

- `@claude finding #3 is pre-existing, please don't block on it`
- `@claude point 5 is acceptable risk for this PR`
- `@claude ignore issue 2 as a blocker, it's out of scope`

Steps:
1. Fetch the previous Claude review to retrieve the full finding list:
   ```bash
   gh api repos/{owner}/{repo}/pulls/<number>/reviews --paginate \
     | jq -s '[.[][] | select(.user.login == "claude[bot]")] | last | .body'
   ```
2. Identify which finding(s) the override refers to using judgment — no strict format required.
3. Downgrade those findings to MINOR, acknowledge each override in the reply
   (e.g. "Finding #3 downgraded to MINOR per override by @username"), and recalculate the verdict.
4. Post the updated verdict (`--approve` or `--request-changes`).

---

### Re-review Flow

1. **Fetch the previous Claude review and extract the reviewed-at SHA**:
   The Claude GitHub App bot login is `claude[bot]` (app slug: `claude`, owned by `anthropics`).
   ```bash
   gh api repos/{owner}/{repo}/pulls/<number>/reviews --paginate \
     | jq -s '[.[][] | select(.user.login == "claude[bot]")] | last | .body' \
   | grep -oP '(?<=reviewed-at: )[^\s]+'
   ```
   The `reviewed-at` footer contains both the SHA and the commit title (see output format).
   Extract only the SHA portion (first token before the space).

2. **Fetch existing comments** (same as initial review, to avoid duplication):
   ```bash
   gh pr view <number> --comments
   gh api repos/{owner}/{repo}/pulls/<number>/comments --paginate
   ```
   Check for any override comments posted since the last review — apply them before
   calculating the verdict (see Override Flow above for how to detect and apply them).

3. **Diff from the last reviewed commit to HEAD**:
   ```bash
   git diff <extracted_sha>..HEAD
   ```
   This covers all commits pushed since the last review, regardless of how many there are.

4. **Always do a targeted re-check** of the findings flagged in the previous review.
   If the user explicitly requests a full re-review (e.g. `@claude full re-review`),
   run the initial review flow instead and note that it supersedes the previous one.

5. **Post the re-review** — always either approve or request changes, never comment-only:
   - Use `--request-changes` if **new** BLOCKERs were introduced since the last review or if previous BLOCKERs were not properly resolved
   - Use `--approve` if **all** BLOCKERs are resolved and no new ones were found

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
