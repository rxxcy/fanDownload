# -*- coding:utf-8 -*-
# anime1 页面视频下载器

from concurrent.futures import ThreadPoolExecutor, as_completed
import inspect
import json
import os
import re
import threading
import time
from html.parser import HTMLParser
from urllib.parse import parse_qsl, quote, unquote, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import ProxyHandler, Request, build_opener


API_URL = "https://v.anime1.me/api"
REFERER = "https://v.anime1.me/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/95.0.4638.69 Safari/537.36"
)
DEFAULT_MAX_WORKERS = 3
MAX_CATEGORY_PAGES = 20


class DownloadCancelledError(Exception):
    pass


class AnimePageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self._in_article = False
        self._article_depth = 0
        self._in_heading = False
        self._capture_title = False
        self._current_title_parts = []
        self._current_api_req = None

    def handle_starttag(self, tag, attrs):
        attr_map = dict(attrs)
        if tag == "article":
            if not self._in_article:
                self._start_article()
            else:
                self._article_depth += 1
            return

        if not self._in_article:
            return

        if tag == "h2":
            self._in_heading = True
        elif tag == "a" and self._in_heading and not self._current_title_parts:
            self._capture_title = True
        elif tag == "video":
            api_req = attr_map.get("data-apireq")
            if api_req:
                self._current_api_req = unquote(api_req)

    def handle_endtag(self, tag):
        if not self._in_article:
            return

        if tag == "article":
            self._article_depth -= 1
            if self._article_depth == 0:
                self._finish_article()
        elif tag == "h2":
            self._in_heading = False
            self._capture_title = False
        elif tag == "a":
            self._capture_title = False

    def handle_data(self, data):
        if self._capture_title:
            self._current_title_parts.append(data)

    def _start_article(self):
        self._in_article = True
        self._article_depth = 1
        self._in_heading = False
        self._capture_title = False
        self._current_title_parts = []
        self._current_api_req = None

    def _finish_article(self):
        title = "".join(self._current_title_parts).strip()
        if title and self._current_api_req:
            self.items.append({"title": title, "api_req": self._current_api_req})
        self._in_article = False
        self._in_heading = False
        self._capture_title = False
        self._current_title_parts = []
        self._current_api_req = None


def main():
    page_url = input("页面链接：").strip()
    while not page_url:
        page_url = input("请输入页面链接：").strip()

    items = fetch_category_items(page_url)
    if not items:
        print("页面内未找到可下载视频")
        return

    selected_items = select_video(items)
    stop_event = threading.Event()
    try:
        download_selected_items(selected_items, max_workers=DEFAULT_MAX_WORKERS, stop_event=stop_event)
    except KeyboardInterrupt:
        stop_event.set()
        print("\n正在停止下载，请稍候...")
        print("已取消下载，程序退出")


def normalize_url(url):
    parts = urlsplit(url.strip())
    path = quote(unquote(parts.path), safe="/")
    query = urlencode(parse_qsl(parts.query, keep_blank_values=True), doseq=True)
    return urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def fetch_page(url):
    request = build_request(normalize_url(url))
    with open_url(request) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def parse_video_items(html):
    parser = AnimePageParser()
    parser.feed(html)
    parser.close()
    return list(reversed(parser.items))


def parse_next_page_url(current_url, html):
    current = normalize_url(current_url)
    current_root = category_root(current)
    if current_root is None:
        return None

    match = re.search(r'<div class="nav-previous">\s*<a href="([^"]+)"', html)
    if not match:
        return None

    next_url = normalize_url(urljoin(current, match.group(1)))
    if category_root(next_url) != current_root:
        return None
    return next_url


def category_root(url):
    parts = urlsplit(url)
    segments = [segment for segment in parts.path.split('/') if segment]
    if len(segments) >= 2 and segments[-2] == 'page' and segments[-1].isdigit():
        segments = segments[:-2]
    if not segments:
        return None
    return '/' + '/'.join(segments)


def episode_number(title):
    match = re.search(r'\[(\d+)\]\s*$', title.strip())
    if not match:
        return None
    return int(match.group(1))


def collect_video_items_from_pages(html_pages):
    merged = []
    seen = set()
    for html in html_pages:
        for item in parse_video_items(html):
            key = (item['title'], item['api_req'])
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)

    indexed_items = list(enumerate(merged))
    indexed_items.sort(key=lambda pair: (episode_number(pair[1]['title']) is None, episode_number(pair[1]['title']) or 10**9, pair[0]))
    return [item for _, item in indexed_items]


def fetch_category_items(page_url):
    visited = set()
    current_url = normalize_url(page_url)
    html_pages = []

    for _ in range(MAX_CATEGORY_PAGES):
        if current_url in visited:
            break
        visited.add(current_url)
        html = fetch_page(current_url)
        html_pages.append(html)
        next_url = parse_next_page_url(current_url, html)
        if not next_url or next_url in visited:
            break
        current_url = next_url

    return collect_video_items_from_pages(html_pages)


def select_video(items, input_fn=input):
    if not items:
        raise ValueError("未找到可下载视频")

    print("页面内可下载的视频：")
    for display_index, item in enumerate(items, start=1):
        print(f"{display_index}. {item['title']}")

    while True:
        raw = input_fn("\n输入索引（空格分隔，回车默认全部）：").strip()
        if not raw:
            return items

        parts = raw.split()
        if any(not part.isdigit() for part in parts):
            print("请输入有效数字")
            continue

        indexes = [int(part) for part in parts]
        if any(index < 1 or index > len(items) for index in indexes):
            print("索引超出范围")
            continue

        selected_items = []
        seen_indexes = set()
        for index in indexes:
            if index in seen_indexes:
                continue
            seen_indexes.add(index)
            selected_items.append(items[index - 1])
        return selected_items


def resolve_download_url(api_req):
    payload = urlencode({"d": api_req}).encode("utf-8")
    request = build_request(API_URL, data=payload, headers={"Referer": REFERER})
    with open_url(request) as response:
        data = json.loads(response.read().decode("utf-8"))
        src = data["s"][0]["src"]
        cookie = join_cookies(response.headers.get_all("Set-Cookie") or [])
    if src.startswith("http"):
        return src, cookie
    return f"https:{src}", cookie


def download_item(item, progress_callback=None, printer=print):
    printer(f"获取 {item['title']} 真实下载地址")
    src, cookie = resolve_download_url(item["api_req"])
    download_video(src, item["title"], cookie, progress_callback=progress_callback, printer=printer)


def download_selected_items(items, max_workers=DEFAULT_MAX_WORKERS, downloader=None, printer=print, progress_enabled=True, stop_event=None):
    if not items:
        return {"successes": [], "failures": []}

    if downloader is None:
        downloader = download_item
    if stop_event is None:
        stop_event = threading.Event()

    worker_count = min(max_workers, len(items))
    progress_reporter = ParallelProgressReporter(printer=printer) if progress_enabled and len(items) > 1 else None
    completed_titles = set()
    failed_titles = {}

    if worker_count == 1:
        item = items[0]
        try:
            run_download_task(downloader, item, None, printer, stop_event=stop_event)
            completed_titles.add(item["title"])
        except DownloadCancelledError:
            printer(f"下载已取消: {item['title']}")
        except Exception as exc:
            failed_titles[item["title"]] = str(exc)
            printer(f"下载失败: {item['title']} - {exc}")
    else:
        printer(f"并行下载已启动，最大并发数: {worker_count}")
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_to_item = {}
            for item in items:
                if stop_event.is_set():
                    break
                progress_callback = None
                if progress_reporter is not None:
                    progress_callback = progress_reporter.make_callback(item["title"])
                future = executor.submit(run_download_task, downloader, item, progress_callback, printer, True, stop_event)
                future_to_item[future] = item

            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    future.result()
                    completed_titles.add(item["title"])
                    printer(f"下载完成: {item['title']}")
                except DownloadCancelledError:
                    printer(f"下载已取消: {item['title']}")
                except Exception as exc:
                    failed_titles[item["title"]] = str(exc)
                    printer(f"下载失败: {item['title']} - {exc}")

                if stop_event.is_set():
                    for pending_future, pending_item in future_to_item.items():
                        if pending_future.done():
                            continue
                        pending_future.cancel()
                        printer(f"下载已取消: {pending_item['title']}")
                    break

    successes = [item["title"] for item in items if item["title"] in completed_titles]
    failures = [(item["title"], failed_titles[item["title"]]) for item in items if item["title"] in failed_titles]

    printer(f"下载汇总: 成功 {len(successes)} 集, 失败 {len(failures)} 集")
    return {"successes": successes, "failures": failures}


def run_download_task(downloader, item, progress_callback, printer, announce_start=False, stop_event=None):
    if stop_event is not None and stop_event.is_set():
        raise DownloadCancelledError("download cancelled")
    if announce_start:
        printer(f"开始下载: {item['title']}")
    signature = inspect.signature(downloader)
    parameters = signature.parameters
    if "stop_event" in parameters:
        if "printer" in parameters:
            return downloader(item, progress_callback=progress_callback, printer=printer, stop_event=stop_event)
        if "progress_callback" in parameters:
            return downloader(item, progress_callback=progress_callback, stop_event=stop_event)
        return downloader(item, stop_event=stop_event)
    if "printer" in parameters:
        return downloader(item, progress_callback=progress_callback, printer=printer)
    if "progress_callback" in parameters:
        return downloader(item, progress_callback=progress_callback)
    return downloader(item)


def download_video(src, title, cookie, progress_callback=None, printer=print, stop_event=None):
    file_path = create_output_path(title)

    headers = {"Referer": REFERER}
    if cookie:
        headers["Cookie"] = cookie

    request = build_request(src, headers=headers)
    if progress_callback is None:
        printer("下载中...")
    try:
        with open_url(request) as response, open(file_path, "wb") as file_obj:
            total_length = response.headers.get("Content-Length")
            if total_length is None:
                downloaded = 0
                start = time.time()
                while True:
                    if stop_event is not None and stop_event.is_set():
                        raise DownloadCancelledError("download cancelled")
                    chunk = response.read(4096)
                    if not chunk:
                        break
                    file_obj.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback is not None:
                        elapsed = max(time.time() - start, 0.001)
                        speed = downloaded / 1024 / 1024 / elapsed
                        progress_callback(downloaded, None, speed)
            else:
                total_size = int(total_length)
                downloaded = 0
                start = time.time()
                while True:
                    if stop_event is not None and stop_event.is_set():
                        raise DownloadCancelledError("download cancelled")
                    chunk = response.read(4096)
                    if not chunk:
                        break
                    file_obj.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback is None:
                        show_progress(downloaded, total_size, start, printer=printer)
                    else:
                        elapsed = max(time.time() - start, 0.001)
                        speed = downloaded / 1024 / 1024 / elapsed
                        progress_callback(downloaded, total_size, speed)
    except DownloadCancelledError:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise
    if progress_callback is None:
        printer()
        printer(f"{title} 下载完成")


def split_episode_suffix(title):
    stripped = title.strip()
    match = re.search(r"\[(\d+)\]\s*$", stripped)
    if not match:
        return stripped, None

    episode = match.group(1)
    base_title = stripped[:match.start()].rstrip()
    return base_title, episode


def sanitize_component(title):
    return re.sub(r'[\/:*?"<>|]', "_", title).strip()


def build_output_names(title):
    base_title, episode = split_episode_suffix(title)
    base_name = sanitize_component(base_title) or sanitize_component(title)
    file_name = f"{base_name}-{episode}" if episode else base_name
    return base_name, file_name


def sanitize_title(title):
    _, file_name = build_output_names(title)
    return file_name


def create_output_path(title):
    directory_name, file_name = build_output_names(title)
    file_dir = os.path.join("video", directory_name)
    os.makedirs(file_dir, exist_ok=True)
    return os.path.join(file_dir, f"{file_name}.mp4")


def show_progress(downloaded, total_size, start_time, printer=print):
    done = int(50 * downloaded / total_size)
    percent_done = int(100 * downloaded / total_size)
    downloaded_mb = downloaded / 1024 / 1024
    total_mb = total_size / 1024 / 1024
    elapsed = max(time.time() - start_time, 0.001)
    speed = downloaded_mb / elapsed
    printer(
        f"\r[{'#' * done}{' ' * (50 - done)}] {percent_done}% "
        f"({downloaded_mb:.2f}Mb/{total_mb:.2f}Mb) {speed:.2f}Mb/s",
        end="",
    )


class ParallelProgressReporter:
    def __init__(self, printer=print, percent_step=10):
        self._printer = printer
        self._percent_step = percent_step
        self._lock = threading.Lock()
        self._progress_state = {}

    def make_callback(self, title):
        self._progress_state[title] = {"last_bucket": -1, "started": False}

        def callback(downloaded, total_size, speed):
            with self._lock:
                state = self._progress_state[title]
                if total_size is None:
                    if not state["started"]:
                        state["started"] = True
                        self._printer(f"[进度] {title}: 已开始下载")
                    return

                percent_done = int(100 * downloaded / total_size)
                percent_bucket = min(100, (percent_done // self._percent_step) * self._percent_step)
                if percent_bucket == 0 and percent_done < 100:
                    return
                if percent_bucket <= state["last_bucket"]:
                    return

                state["last_bucket"] = percent_bucket
                downloaded_mb = downloaded / 1024 / 1024
                total_mb = total_size / 1024 / 1024
                self._printer(
                    f"[进度] {title}: {percent_done}% "
                    f"({downloaded_mb:.2f}Mb/{total_mb:.2f}Mb) {speed:.2f}Mb/s"
                )

        return callback


def join_cookies(cookie_headers):
    cookies = []
    for cookie in cookie_headers:
        cookies.append(cookie.split(";", 1)[0])
    return "; ".join(cookies)


def build_request(url, data=None, headers=None):
    request_headers = {"User-Agent": USER_AGENT}
    if headers:
        request_headers.update(headers)
    return Request(url, data=data, headers=request_headers)


def open_url(request):
    opener = build_opener_with_proxy()
    return opener.open(request)


def build_opener_with_proxy():
    proxies = {}
    http_proxy = os.environ.get("FAN_DOWNLOAD_HTTP_PROXY") or os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("FAN_DOWNLOAD_HTTPS_PROXY") or os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

    if http_proxy:
        proxies["http"] = http_proxy
    if https_proxy:
        proxies["https"] = https_proxy

    if proxies:
        return build_opener(ProxyHandler(proxies))
    return build_opener()


if __name__ == "__main__":
    main()
