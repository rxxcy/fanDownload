# fanDownload

Anime1 页面视频下载器。

输入 Anime1 链接，脚本会解析页面内可下载的视频条目，列出索引后按你的选择下载对应视频。


## 运行环境

- Python 3
- 已在 Python 3.12 本地验证

## 依赖

当前版本只使用 Python 标准库，不需要安装第三方包。

## 运行方式

```bash
python app.py
```

启动后输入页面链接，例如：

```text
https://anime1.me/category/2026年冬季/身為魔族的我-想向勇者小隊的可愛女孩告白
```

脚本会列出页面里的视频条目，然后提示：

```text
输入索引（空格分隔，回车默认全部）：
```

输入规则：

- 直接回车：下载当前页面内全部视频
- 输入单个索引：下载一个视频
- 输入多个索引并用空格分隔，例如 `0 2 4`
- 重复索引会自动去重

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
python app.py
```