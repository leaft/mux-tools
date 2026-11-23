# Source this file from ~/.zshrc after adding wt-switch to PATH.
# Ctrl-X, then W runs only at a Zsh prompt; it never types into an editor/agent.
_mux_tools_worktree_widget() {
  zle -I
  command wt-switch --cwd "$PWD"
  zle reset-prompt
}
zle -N mux-tools-worktree _mux_tools_worktree_widget
bindkey '^Xw' mux-tools-worktree
