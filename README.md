# fanDownload

Anime1 页面视频下载器，现已使用 Rust 重写为命令行工具。

输入 Anime1 页面链接后，程序会解析页面中的可下载剧集，按你的选择执行单集或多集下载。

## 运行环境

- Rust 工具链
- 已在 `cargo 1.94.0` 上验证
- 需要能够访问 `anime1.me` 和 `v.anime1.me`

## 依赖

项目依赖通过 Cargo 管理，首次运行测试或构建时会自动下载所需 crate。

核心依赖包括：

- `tokio`
- `reqwest`
- `scraper`
- `serde`
- `ctrlc`
- `futures`

## 运行方式

直接运行：

```bash
cargo run
```

编译后运行：

```bash
cargo build --release
./target/release/fan_download
```

Windows PowerShell：

```powershell
cargo build --release
.\target\release\fan_download.exe
```

启动后输入页面链接，例如：

```text
https://anime1.me/category/2026年冬季/異世界的處置依社畜而定
```

程序会列出页面里的剧集条目，然后提示：

```text
输入索引（空格分隔，回车默认全部）：
```

输入规则：

- 直接回车：下载当前页面内全部剧集
- 输入单个索引：下载一个剧集
- 输入多个索引并用空格分隔，例如 `1 3 5`
- 重复索引会自动去重
- 剧集列表会按正序显示，索引从 `1` 开始

## 下载行为

- 只下载 1 集时，按单任务方式下载
- 一次选择多集时，程序会自动启用并行下载
- 默认最大并发数为 `3`
- 并行下载时会输出每一集的开始、进度、完成或失败状态
- 某一集下载失败不会中断其他任务，结束后会输出汇总
- 下载过程中按 `Ctrl+C` 会尽快停止所有任务，并清理未完成的部分下载文件

## 下载目录

下载文件默认保存到当前目录下的 `video/` 文件夹，结构如下：

```text
video/
  番剧标题/
    番剧标题.mp4
```

文件名中的非法路径字符会自动替换为 `_`。

## 代理

如果你的网络环境需要代理，可以设置以下环境变量之一：

- `FAN_DOWNLOAD_HTTP_PROXY`
- `FAN_DOWNLOAD_HTTPS_PROXY`
- `HTTP_PROXY`
- `HTTPS_PROXY`

示例：

```powershell
$env:FAN_DOWNLOAD_HTTP_PROXY="http://127.0.0.1:7890"
$env:FAN_DOWNLOAD_HTTPS_PROXY="http://127.0.0.1:7890"
cargo run
```

## 测试

运行完整测试：

```bash
cargo test
```

## 分支说明

- `python-version`：保留 Python 版本完整实现
- `main`：Rust CLI 版本
