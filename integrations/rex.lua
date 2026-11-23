-- Optional native launcher; the switching logic stays in bin/wt-switch.
-- Requires wt-switch in ~/.local/bin. Load this file from Rex init.lua.
rex.action {
  name = "mux_worktree",
  title = "Worktree: Switch Tab",
  category = "Mux Tools",
  run = function(ctx)
    local location, err = rex.block.call("com.superlogical.terminal", "pwd", {
      block_id = ctx.block_id,
      session_id = ctx.session_id,
    })
    if not location or not location.pwd then
      error(err or "The focused terminal has not reported its directory")
    end
    local created, why = rex.session.new_layer {
      session_id = ctx.session_id,
      bounds = { 0.1, 0.15, 0.8, 0.7 },
      focus = true,
      layout = rex.layout.block {
        flavor = "com.superlogical.terminal.shell",
        options = {
          command = {
            "/bin/bash", "-c", [[
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
"$HOME/.local/bin/wt-switch" "$@"
mux_status=$?
if [ "$mux_status" -ne 0 ]; then
  printf '\nPress Enter to close…'
  read -r mux_ack
fi
exit "$mux_status"
]],
            "wt-switch", "--host", "rex", "--scope", ctx.session_id,
            "--cwd", location.pwd,
          },
          shell = "none",
          exit = { on_completion = true },
        },
      },
    }
    if not created then error(why) end
  end,
}
rex.bind("ctrl+a>w", "mux_worktree")
