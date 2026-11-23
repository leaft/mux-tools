# 本地验证记录

日期：2026-11-23；平台：macOS arm64。

## 自动化检查

- `make check`：Bash 语法、ShellCheck、27 项自动化测试全部通过。
- 提交后审查发现的标签页关联复用与换行路径问题均先用回归测试复现，再修复；覆盖两端宿主及原始路径、file URL、符号链接、worktree 列表入口。
- `zsh -n integrations/zsh.zsh`：通过。
- `rex config check integrations/rex.lua --json`：1 个 action、1 个绑定，0 条诊断。
- 测试使用真实临时 Git 仓库及 jq/fzf；CLI 替身模拟宿主协议，包括异常和并发场景，不冒充真实 App。

## 真实宿主检查

Rex `0.1.0-preview.21`、API revision 18；Herdr desktop App `0.1.16`。

- 分别创建临时 Rex session 与本机 Herdr space，均验证新标签页的目录和分支名称。
- 连续选择同一 worktree 没有增加标签页；改名后仍聚焦原 ID。
- 手动关闭测试标签页后重新选择，创建新 ID 并替换缓存关联。
- Rex Lua launcher 实际启动了浮动终端中的 fzf；输入筛选条件并确认后创建目标标签页，浮动层退出。
- Rex picker 按 Escape 后退出，标签页数量不变。
- 测试后清理临时 session/space，并恢复 Herdr 原先选中的标签页；没有关闭用户原有会话或终端。

`wt-switch` 已通过 `make install` 安装到本机用户级 bin 目录。没有加载或改写用户的 `.zshrc`、Rex `init.lua` 或 Herdr 设置。快捷键接入仍由用户选择启用。

GitHub Actions 状态以仓库的实时运行记录为准；上述结果只陈述本地检查，不替代远端 CI。
