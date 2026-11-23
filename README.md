# mux-tools

面向 **Rex、Herdr 等 Agent 终端复用器**的快捷操作脚本。当前提供 `wt-switch`：搜索当前 Git 仓库的 worktree，在对应标签页中继续工作。

```text
worktree 列表 → fzf 搜索选择 → 已有标签页则聚焦，否则新建
```

- **一个 worktree，一个标签页**，在当前 Rex session / Herdr space 内复用。
- 按规范化绝对路径识别；标签页改名后继续复用。
- 自动识别已经打开在目标 worktree 或其子目录的终端。
- 关闭标签页后再选会重新创建；同时触发两次不会重复创建。
- Enter 确认，Esc / Ctrl-C 取消。支持空格、中文和引号等常见路径。

## 支持的宿主

| 宿主 | 接口 | 状态 |
|---|---|---|
| Rex | `rex window ls/new/focus`、`rex block call … pwd` | 以本机 `0.1.0-preview.21` / API revision 18 验证 |
| Herdr 桌面 App | `herdr-app ls/do`、`hc get` | 以本机 App `0.1.16` 验证 |

**Herdr 桌面 App 与 Herdr TUI 是不同接口。** 本版的 `--host herdr` 指 `herdr-app` + `hc`，不支持 `herdr tab …` 的 TUI。远程 Herdr space 会明确报错；本版只操作本机目录。

## 安装

macOS 安装依赖：

```bash
brew install fzf jq
```

`fzf` 是终端里的交互式模糊搜索选择器；`jq` 用来读取宿主 CLI 的 JSON。运行还需要 Git、Bash 3.2+ 和对应宿主 CLI。

```bash
git clone https://github.com/leaft/mux-tools.git
cd mux-tools
make install
```

默认安装为 `~/.local/bin/wt-switch`。确保该目录在终端的 `PATH` 中：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

也可以直接运行仓库里的 `bin/wt-switch`。`make install PREFIX=/your/prefix` 可指定安装目录。

## 使用

在仓库或任一 worktree 的目录中执行：

```bash
wt-switch
```

在 Herdr 里通过 `HC_TERMINAL_ID` 定位当前 space；在 Rex 中使用 `REX_SESSION`。两者同时存在时优先 Herdr，适合嵌套启动的环境。没有这些变量时明确指定宿主：

```bash
wt-switch --host rex
wt-switch --host herdr
```

可指定源仓库和目标 session / space，防止跟随界面焦点变化：

```bash
wt-switch --host rex --scope 'session:…' --cwd /path/to/repo
wt-switch --host herdr --scope 'sp…' --cwd /path/to/repo
```

自动化或不使用菜单时，用 `--path` 选择**属于源仓库的现有 worktree 根目录**：

```bash
wt-switch --host rex --cwd /path/to/repo --path '/path/to/another worktree'
wt-switch --cwd /path/to/repo --list   # 只输出 JSON，不连接任何宿主
```

它不创建或删除 Git worktree，不执行 `git switch`，也不会向正在运行的编辑器或 Agent 输入 `cd`。

## 快捷键

### Zsh：两端都能用

把下面一行加入 `~/.zshrc`，路径换成你的克隆位置：

```zsh
source "$HOME/code/mux-tools/integrations/zsh.zsh"
```

重开 Shell 后，在 **Zsh 提示符**按 `Ctrl-X`，再按 `W`。菜单在当前终端运行；按键不会向正在运行的编辑器或 Agent 注入命令。可以修改示例最后一行 `bindkey` 选择自己的组合。

### Rex：原生浮动菜单（可选）

先 `make install`，再在 `~/.config/rex/init.lua` 中加入：

```lua
dofile(os.getenv("HOME") .. "/code/mux-tools/integrations/rex.lua")
```

检查配置后加载：

```bash
rex config check
rex config reload
```

按 `Ctrl-A`，再按 `W` 打开浮动终端中的 fzf。Launcher 从当前 pane 读取目录，把 session ID 固定传给 Shell 脚本。Lua 仅负责启动菜单，查询、去重和切换都由 Bash 实现。

仓库不自动改写你的 Shell 或应用配置；加载前确认快捷键没有与你的配置冲突。

## 缓存和故障处理

关联记录默认保存在 `${XDG_STATE_HOME:-~/.local/state}/mux-tools/`，按 Rex 服务实例 + session 或 Herdr app home + space 隔离。记录的是 worktree 路径与标签页 ID，重新运行时验证 ID 是否仍存在。

- 新建标签页后，改变该标签页里的 Shell 目录不会改变它原来的 worktree 关联。
- 尚未关联的 Rex 标签页需要终端能报告目录；无法识别目录时不能可靠自动接管。
- 本版忽略已失效的 worktree 路径和 bare checkout；不支持名称含控制字符的路径。
- 聚焦失败会报错，不用新建标签页掩盖失败。
- 缓存 JSON 损坏时会报告具体文件，先移走该文件再重试。
- 并发锁最多等待约 5 秒。若进程被强制结束，可能残留 `.lock` 目录；核对其中 `pid` 对应进程已结束后再移除锁。普通退出、取消和错误会清理自己的锁。

CLI 不在 PATH 或安装位置不同时，可以使用以下环境变量指定可执行文件：

```bash
export MUX_TOOLS_REX_BIN='/path/to/rex'
export MUX_TOOLS_HERDR_BIN='/path/to/herdr-app'
export MUX_TOOLS_HC_BIN='/path/to/hc'
```

Rex Beta 的标准 macOS App 路径和 Herdr 的 `~/.local/bin` 会自动作为后备位置。`MUX_TOOLS_STATE_DIR` 可将关联记录放到其他目录，适合隔离测试。

## 开发与验证

```bash
brew install shellcheck  # 仅开发检查需要
make check
```

测试使用真实临时 Git 仓库、真实 jq/fzf 和状态化 CLI 替身；不会连接你的实际终端宿主。Python 3 仅用于测试，不是运行时依赖。CI 在 macOS 与 Linux 上执行相同检查。

初次发布另外在临时 Rex session 与 Herdr space 中验证创建、复用、改名、关闭后重建，并清理测试资源。详细需求见 [docs/spec.md](docs/spec.md)，实测边界见 [docs/validation.md](docs/validation.md)。

接口依据：[Rex CLI](https://www.superlogical.com/rex/docs/reference/cli)、[Rex Shell Scripting](https://www.superlogical.com/rex/docs/automate/shell-scripting)、[Herdr App commands](https://github.com/herdrdev/herdr-app/blob/master/docs/commands.md)、[fzf](https://github.com/junegunn/fzf)。宿主 CLI 升级后以本机帮助和实际响应为准。

## License

[MIT](LICENSE)
