# Contributing

- Commands live in `bin/`; host or shell launchers live in `integrations/`.
- Keep runtime dependencies explicit. `wt-switch` requires Bash 3.2+, Git, jq, fzf, and the relevant host CLI.
- Pass paths and user input as separate arguments or JSON. Do not evaluate them as shell code.
- Preserve the user's existing tabs and worktree contents. Test terminal operations in isolated sessions/spaces.
- Keep requirements in `docs/spec.md` and user-visible behavior in `README.md` aligned.
- Run `make check` before committing. Tests use temporary Git repositories and host doubles, never a real host by default.
- Follow Conventional Commits. After each substantive commit, review the pinned parent-to-commit diff on Standards and Spec axes before pushing.
