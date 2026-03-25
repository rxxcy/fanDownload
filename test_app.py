import unittest
from pathlib import Path
import threading
import time
import tempfile
import io
from contextlib import redirect_stdout

import app


DEMO_HTML = """
<html>
  <body>
    <article>
      <header><h2><a href="https://anime1.me/28407">身為魔族的我 想向勇者小隊的可愛女孩告白 [12]</a></h2></header>
      <div class="entry-content">
        <video data-apireq="%7B%22c%22%3A%221795%22%2C%22e%22%3A%2212b%22%2C%22t%22%3A1774429603%2C%22p%22%3A0%2C%22s%22%3A%22479a129c287124787d91d6f5236cf996%22%7D"></video>
      </div>
    </article>
    <article>
      <header><h2><a href="https://anime1.me/28345">身為魔族的我 想向勇者小隊的可愛女孩告白 [11]</a></h2></header>
      <div class="entry-content">
        <video data-apireq="%7B%22c%22%3A%221795%22%2C%22e%22%3A%2211b%22%2C%22t%22%3A1774429603%2C%22p%22%3A0%2C%22s%22%3A%229ed796f85e97e7961195f92c9b957a9b%22%7D"></video>
      </div>
    </article>
    <article>
      <header><h2><a href="https://anime1.me/28279">身為魔族的我 想向勇者小隊的可愛女孩告白 [10]</a></h2></header>
      <div class="entry-content">
        <video data-apireq="%7B%22c%22%3A%221795%22%2C%22e%22%3A%2210b%22%2C%22t%22%3A1774429603%2C%22p%22%3A0%2C%22s%22%3A%22b3f11e1774da72d2d773e83666bcb070%22%7D"></video>
      </div>
    </article>
    <article>
      <header><h2><a href="https://anime1.me/28218">身為魔族的我 想向勇者小隊的可愛女孩告白 [09]</a></h2></header>
      <div class="entry-content">
        <video data-apireq="%7B%22c%22%3A%221795%22%2C%22e%22%3A%229b%22%2C%22t%22%3A1774429603%2C%22p%22%3A0%2C%22s%22%3A%22390e06ef3ff8f4f9e3f8c90241e8aff8%22%7D"></video>
      </div>
    </article>
    <article>
      <header><h2><a href="https://anime1.me/28149">身為魔族的我 想向勇者小隊的可愛女孩告白 [08]</a></h2></header>
      <div class="entry-content">
        <video data-apireq="%7B%22c%22%3A%221795%22%2C%22e%22%3A%228b%22%2C%22t%22%3A1774429603%2C%22p%22%3A0%2C%22s%22%3A%22d6e458f8eb1bee5a2a46c641aedc5ca0%22%7D"></video>
      </div>
    </article>
    <article>
      <header><h2><a href="https://anime1.me/28087">身為魔族的我 想向勇者小隊的可愛女孩告白 [07]</a></h2></header>
      <div class="entry-content">
        <video data-apireq="%7B%22c%22%3A%221795%22%2C%22e%22%3A%227b%22%2C%22t%22%3A1774429603%2C%22p%22%3A0%2C%22s%22%3A%22970f15de96befb620bcd4bd565d17fca%22%7D"></video>
      </div>
    </article>
    <article>
      <header><h2><a href="https://anime1.me/28031">身為魔族的我 想向勇者小隊的可愛女孩告白 [06]</a></h2></header>
      <div class="entry-content">
        <video data-apireq="%7B%22c%22%3A%221795%22%2C%22e%22%3A%226b%22%2C%22t%22%3A1774429604%2C%22p%22%3A0%2C%22s%22%3A%229fc38f569bc83daae39427fc22cba7e4%22%7D"></video>
      </div>
    </article>
    <article>
      <header><h2><a href="https://anime1.me/27962">身為魔族的我 想向勇者小隊的可愛女孩告白 [05]</a></h2></header>
      <div class="entry-content">
        <video data-apireq="%7B%22c%22%3A%221795%22%2C%22e%22%3A%225b%22%2C%22t%22%3A1774429604%2C%22p%22%3A0%2C%22s%22%3A%226721e0b0e0b4f00b996d560c2a26237b%22%7D"></video>
      </div>
    </article>
    <article>
      <header><h2><a href="https://anime1.me/27898">身為魔族的我 想向勇者小隊的可愛女孩告白 [04]</a></h2></header>
      <div class="entry-content">
        <video data-apireq="%7B%22c%22%3A%221795%22%2C%22e%22%3A%224b%22%2C%22t%22%3A1774429604%2C%22p%22%3A0%2C%22s%22%3A%225d53c93081a6d5ff6f6c2d6a186f8cff%22%7D"></video>
      </div>
    </article>
    <article>
      <header><h2><a href="https://anime1.me/27827">身為魔族的我 想向勇者小隊的可愛女孩告白 [03]</a></h2></header>
      <div class="entry-content">
        <video data-apireq="%7B%22c%22%3A%221795%22%2C%22e%22%3A%223b%22%2C%22t%22%3A1774429604%2C%22p%22%3A0%2C%22s%22%3A%22acafa7589f3409b6bf389d4f5364f6bd%22%7D"></video>
      </div>
    </article>
    <article>
      <header><h2><a href="https://anime1.me/27748">身為魔族的我 想向勇者小隊的可愛女孩告白 [02]</a></h2></header>
      <div class="entry-content">
        <video data-apireq="%7B%22c%22%3A%221795%22%2C%22e%22%3A%222b%22%2C%22t%22%3A1774429604%2C%22p%22%3A0%2C%22s%22%3A%227456385405a7108806fd59c990166f97%22%7D"></video>
      </div>
    </article>
    <article>
      <header><h2><a href="https://anime1.me/27695">身為魔族的我 想向勇者小隊的可愛女孩告白 [01]</a></h2></header>
      <div class="entry-content">
        <video data-apireq="%7B%22c%22%3A%221795%22%2C%22e%22%3A%221b%22%2C%22t%22%3A1774429604%2C%22p%22%3A0%2C%22s%22%3A%2207594666f57b19eef354490a92620162%22%7D"></video>
      </div>
    </article>
  </body>
</html>
"""


class ParseVideoItemsTests(unittest.TestCase):
    def test_parse_video_items_extracts_entries_from_demo_page(self):
        items = app.parse_video_items(DEMO_HTML)

        self.assertEqual(12, len(items))
        self.assertEqual("身為魔族的我 想向勇者小隊的可愛女孩告白 [01]", items[0]["title"])
        self.assertTrue(items[0]["api_req"])
        self.assertTrue(items[0]["api_req"].startswith("{"))
        self.assertEqual("身為魔族的我 想向勇者小隊的可愛女孩告白 [12]", items[-1]["title"])

    def test_parse_video_items_returns_empty_list_when_page_has_no_video_entries(self):
        html = "<html><body><article><h2>no video</h2></article></body></html>"

        items = app.parse_video_items(html)

        self.assertEqual([], items)


class SelectVideoTests(unittest.TestCase):
    def test_select_video_returns_all_items_when_input_is_empty(self):
        items = [
            {"title": "Episode 1", "api_req": "req-1"},
            {"title": "Episode 2", "api_req": "req-2"},
        ]

        selected = app.select_video(items, input_fn=lambda _: "")

        self.assertEqual(items, selected)

    def test_select_video_returns_items_for_space_separated_indexes(self):
        items = [
            {"title": "Episode 1", "api_req": "req-1"},
            {"title": "Episode 2", "api_req": "req-2"},
            {"title": "Episode 3", "api_req": "req-3"},
        ]

        selected = app.select_video(items, input_fn=lambda _: "1 3")

        self.assertEqual([items[0], items[2]], selected)

    def test_select_video_displays_one_based_indexes(self):
        items = [
            {"title": "Episode 1", "api_req": "req-1"},
            {"title": "Episode 2", "api_req": "req-2"},
        ]
        output = io.StringIO()

        with redirect_stdout(output):
            app.select_video(items, input_fn=lambda _: "")

        rendered = output.getvalue()
        self.assertIn("1. Episode 1", rendered)
        self.assertIn("2. Episode 2", rendered)


class NormalizeUrlTests(unittest.TestCase):
    def test_normalize_url_encodes_non_ascii_path(self):
        url = "https://anime1.me/category/2026年冬季/身為魔族的我-想向勇者小隊的可愛女孩告白"

        normalized = app.normalize_url(url)

        self.assertNotIn("年冬季", normalized)
        self.assertTrue(normalized.startswith("https://anime1.me/category/"))


class DownloadSelectedItemsTests(unittest.TestCase):
    def test_download_selected_items_limits_parallelism_to_three_workers(self):
        items = [
            {"title": f"Episode {index}", "api_req": f"req-{index}"}
            for index in range(5)
        ]
        active_count = 0
        max_active_count = 0
        lock = threading.Lock()

        def downloader(item, progress_callback=None):
            nonlocal active_count, max_active_count
            with lock:
                active_count += 1
                max_active_count = max(max_active_count, active_count)
            time.sleep(0.05)
            with lock:
                active_count -= 1

        result = app.download_selected_items(
            items,
            max_workers=3,
            downloader=downloader,
            printer=lambda *_args, **_kwargs: None,
            progress_enabled=False,
        )

        self.assertEqual(3, max_active_count)
        self.assertEqual([item["title"] for item in items], result["successes"])
        self.assertEqual([], result["failures"])

    def test_download_selected_items_collects_failures_without_stopping_other_tasks(self):
        items = [
            {"title": "Episode 1", "api_req": "req-1"},
            {"title": "Episode 2", "api_req": "req-2"},
            {"title": "Episode 3", "api_req": "req-3"},
        ]

        def downloader(item, progress_callback=None):
            if item["title"] == "Episode 2":
                raise RuntimeError("network error")

        result = app.download_selected_items(
            items,
            max_workers=3,
            downloader=downloader,
            printer=lambda *_args, **_kwargs: None,
            progress_enabled=False,
        )

        self.assertEqual(["Episode 1", "Episode 3"], result["successes"])
        self.assertEqual([("Episode 2", "network error")], result["failures"])

    def test_download_selected_items_only_prints_start_for_running_workers(self):
        items = [
            {"title": f"Episode {index}", "api_req": f"req-{index}"}
            for index in range(5)
        ]
        started = threading.Event()
        release = threading.Event()
        lock = threading.Lock()
        started_count = 0
        logs = []

        def printer(*args, **kwargs):
            with lock:
                logs.append(" ".join(str(arg) for arg in args))

        def downloader(item, progress_callback=None, printer=None):
            nonlocal started_count
            with lock:
                started_count += 1
                if started_count == 3:
                    started.set()
            release.wait(timeout=1)

        thread = threading.Thread(
            target=app.download_selected_items,
            kwargs={
                "items": items,
                "max_workers": 3,
                "downloader": downloader,
                "printer": printer,
                "progress_enabled": False,
            },
        )
        thread.start()
        self.assertTrue(started.wait(timeout=1))
        time.sleep(0.05)
        with lock:
            start_logs = [line for line in logs if line.startswith("开始下载: ")]
        self.assertEqual(
            ["开始下载: Episode 0", "开始下载: Episode 1", "开始下载: Episode 2"],
            start_logs,
        )
        release.set()
        thread.join(timeout=1)
        self.assertFalse(thread.is_alive())


class ParallelProgressReporterTests(unittest.TestCase):
    def test_parallel_progress_reporter_skips_zero_percent_updates(self):
        logs = []
        reporter = app.ParallelProgressReporter(printer=logs.append, percent_step=10)
        callback = reporter.make_callback("Episode 1")

        callback(1024, 100 * 1024 * 1024, 3.91)

        self.assertEqual([], logs)


class StopEventTests(unittest.TestCase):
    def test_download_video_stops_and_removes_partial_file_when_stop_event_is_set(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original_open_url = app.open_url
            original_create_output_path = app.create_output_path
            stop_event = threading.Event()

            class FakeHeaders(dict):
                def get(self, key, default=None):
                    return super().get(key, default)

            class FakeResponse:
                def __init__(self):
                    self.headers = FakeHeaders({"Content-Length": str(16 * 1024)})
                    self._reads = 0

                def read(self, size):
                    if self._reads == 0:
                        self._reads += 1
                        return b"x" * size
                    stop_event.set()
                    self._reads += 1
                    return b"x" * size

                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

            def fake_open_url(_request):
                return FakeResponse()

            def fake_create_output_path(_title):
                output_dir = Path(temp_dir) / "video" / "Episode 1"
                output_dir.mkdir(parents=True, exist_ok=True)
                return str(output_dir / "Episode 1.mp4")

            app.open_url = fake_open_url
            app.create_output_path = fake_create_output_path

            with self.assertRaises(app.DownloadCancelledError):
                app.download_video(
                    "https://example.com/video.mp4",
                    "Episode 1",
                    "",
                    stop_event=stop_event,
                    printer=lambda *_args, **_kwargs: None,
                )

            self.assertFalse((Path(temp_dir) / "video" / "Episode 1" / "Episode 1.mp4").exists())
            app.open_url = original_open_url
            app.create_output_path = original_create_output_path

    def test_download_selected_items_does_not_start_new_tasks_after_stop_event(self):
        items = [
            {"title": f"Episode {index}", "api_req": f"req-{index}"}
            for index in range(5)
        ]
        stop_event = threading.Event()
        started_titles = []
        lock = threading.Lock()

        def downloader(item, progress_callback=None):
            with lock:
                started_titles.append(item["title"])
                if len(started_titles) == 1:
                    stop_event.set()
            time.sleep(0.05)

        result = app.download_selected_items(
            items,
            max_workers=3,
            downloader=downloader,
            printer=lambda *_args, **_kwargs: None,
            progress_enabled=False,
            stop_event=stop_event,
        )

        self.assertEqual(["Episode 0"], started_titles)
        self.assertEqual(["Episode 0"], result["successes"])
        self.assertEqual([], result["failures"])


if __name__ == "__main__":
    unittest.main()
