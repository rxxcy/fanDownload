# -*- coding:utf-8 -*-
# anime1 页面视频下载器

import json
import os
import re
import time
from html.parser import HTMLParser
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit
from urllib.request import ProxyHandler, Request, build_opener


API_URL = "https://v.anime1.me/api"
REFERER = "https://v.anime1.me/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/95.0.4638.69 Safari/537.36"
)


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

    html = fetch_page(page_url)
    items = parse_video_items(html)
    if not items:
        print("页面内未找到可下载视频")
        return

    selected_items = select_video(items)
    for selected in selected_items:
        print(f"获取 {selected['title']} 真实下载地址")
        src, cookie = resolve_download_url(selected["api_req"])
        download_video(src, selected["title"], cookie)


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
    return parser.items


def select_video(items, input_fn=input):
    if not items:
        raise ValueError("未找到可下载视频")

    print("页面内可下载的视频：")
    for index, item in enumerate(items):
        print(f"{index}. {item['title']}")

    while True:
        raw = input_fn("\n输入索引（空格分隔，回车默认全部）：").strip()
        if not raw:
            return items

        parts = raw.split()
        if any(not part.isdigit() for part in parts):
            print("请输入有效数字")
            continue

        indexes = [int(part) for part in parts]
        if any(index < 0 or index >= len(items) for index in indexes):
            print("索引超出范围")
            continue

        selected_items = []
        seen_indexes = set()
        for index in indexes:
            if index in seen_indexes:
                continue
            seen_indexes.add(index)
            selected_items.append(items[index])
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


def download_video(src, title, cookie):
    safe_title = sanitize_title(title)
    file_dir = os.path.join("video", safe_title)
    os.makedirs(file_dir, exist_ok=True)
    file_path = os.path.join(file_dir, f"{safe_title}.mp4")

    headers = {"Referer": REFERER}
    if cookie:
        headers["Cookie"] = cookie

    request = build_request(src, headers=headers)
    print("下载中...")
    with open_url(request) as response, open(file_path, "wb") as file_obj:
        total_length = response.headers.get("Content-Length")
        if total_length is None:
            while True:
                chunk = response.read(4096)
                if not chunk:
                    break
                file_obj.write(chunk)
        else:
            total_size = int(total_length)
            downloaded = 0
            start = time.time()
            while True:
                chunk = response.read(4096)
                if not chunk:
                    break
                file_obj.write(chunk)
                downloaded += len(chunk)
                show_progress(downloaded, total_size, start)
    print()
    print(f"{title} 下载完成")


def sanitize_title(title):
    cleaned = re.sub(r"\[\d+\]", "", title).strip()
    return re.sub(r'[\\/:*?"<>|]', "_", cleaned)


def show_progress(downloaded, total_size, start_time):
    done = int(50 * downloaded / total_size)
    percent_done = int(100 * downloaded / total_size)
    downloaded_mb = downloaded / 1024 / 1024
    total_mb = total_size / 1024 / 1024
    elapsed = max(time.time() - start_time, 0.001)
    speed = downloaded_mb / elapsed
    print(
        f"\r[{'#' * done}{' ' * (50 - done)}] {percent_done}% "
        f"({downloaded_mb:.2f}Mb/{total_mb:.2f}Mb) {speed:.2f}Mb/s",
        end="",
    )


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
