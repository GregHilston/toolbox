# PR Review Command

**IMPORTANT: This command produces a REVIEW for user feedback. Do NOT automatically post comments or make changes.**

Perform a thorough code review of either a GitHub pull request or local changes.

## Usage

### Review a GitHub PR
Invoke with a GitHub PR URL:
```
/pr https://github.com/owner/repo/pull/123
```

### Review Local Changes
Invoke without arguments to review current working changes:
```
/pr
```

## Behavior

### When given a GitHub PR URL:
1. Use `gh pr view <number> --json <fields>` and `gh pr diff <number>` to fetch PR details
2. Review the PR description, changed files, and diff
3. Analyze code quality, potential bugs, and design decisions
4. Provide constructive feedback

### When reviewing local changes:
1. Run `git status` to see current state
2. Run `git diff` to see unstaged changes
3. Run `git diff --cached` to see staged changes
4. If on a feature branch (not main/master):
   - Determine base branch (usually `main` or `master`)
   - Run `git log <base>..HEAD` to see commits not on base
   - Run `git diff <base>...HEAD` to see all changes since branching
5. Review all changes as if preparing for a PR

## Review Areas

### Code Quality
- **Readability**: Is the code clear and well-organized?
- **Naming**: Are variables, functions, and classes named appropriately?
- **Complexity**: Are there overly complex functions that should be simplified?
- **Duplication**: Is there duplicated code that should be extracted?

### Correctness & Safety
- **Logic errors**: Any potential bugs or edge cases not handled?
- **Security**: Any vulnerabilities (injection, XSS, auth bypasses, etc.)?
- **Error handling**: Are errors handled gracefully?
- **Data validation**: Is input validated at boundaries?

### Design & Architecture
- **Separation of concerns**: Are responsibilities properly divided?
- **Dependencies**: Are new dependencies justified?
- **Breaking changes**: Will this break existing functionality?
- **API design**: Are interfaces clear and well-designed?

### Testing
- **Test coverage**: Are there tests for new/changed code?
- **Test quality**: Do tests cover edge cases and failure scenarios?
- **Missing tests**: What should be tested but isn't?

### Documentation
- **Code comments**: Are non-obvious parts explained?
- **API documentation**: Are public interfaces documented?
- **README/docs**: Do user-facing changes need doc updates?

### Project-Specific Patterns
- Check CLAUDE.md for project conventions
- Ensure changes align with existing patterns
- Flag deviations from established practices

## Output Format

### Summary
- High-level assessment of the changes
- Key changes and their purpose
- Overall impression

### MUST (Critical Issues)
Bugs, crashes, functional errors, security vulnerabilities, data loss risks, or anything that MUST be fixed before merging.

For each MUST item:
- **Location**: file path and line numbers (e.g., `src/foo.ts:42-51`)
- **Issue**: What's wrong?
- **Impact**: What happens if not fixed?
- **Fix**: How to resolve it

### SHOULD (Important Improvements)
Things we should fix but aren't critical — refactors, better code organization, improvements that don't change functionality, missing tests, unclear naming.

For each SHOULD item:
- **Location**: file path and line numbers
- **Issue**: What could be better?
- **Why**: Why it matters (maintainability, clarity, performance)
- **Suggestion**: How to improve it

### COULD (Nice-to-Haves)
Nice-to-have improvements, nitpicks, typos, formatting, minor style issues that don't affect functionality.

For each COULD item:
- **Location**: file path and line numbers
- **Issue**: Minor improvement opportunity
- **Suggestion**: Optional enhancement

### Positives
- Call out particularly good code, clever solutions, or improvements
- Acknowledge well-written tests or documentation

### Questions
- Anything unclear that needs clarification?
- Potential edge cases to consider?
- Design decisions that might need discussion?

### Test Coverage Assessment
- What's currently tested?
- What should be tested but isn't?
- Are there any test gaps or weaknesses?

---

**After presenting the review, ask the user which items they'd like to address.**

**If reviewing a GitHub PR, ask if they want to post any of this feedback as a PR comment.**
