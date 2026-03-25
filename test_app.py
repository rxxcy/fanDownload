import unittest

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
        self.assertEqual("身為魔族的我 想向勇者小隊的可愛女孩告白 [12]", items[0]["title"])
        self.assertTrue(items[0]["api_req"])
        self.assertTrue(items[0]["api_req"].startswith("{"))
        self.assertEqual("身為魔族的我 想向勇者小隊的可愛女孩告白 [01]", items[-1]["title"])

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

        selected = app.select_video(items, input_fn=lambda _: "0 2")

        self.assertEqual([items[0], items[2]], selected)


class NormalizeUrlTests(unittest.TestCase):
    def test_normalize_url_encodes_non_ascii_path(self):
        url = "https://anime1.me/category/2026年冬季/身為魔族的我-想向勇者小隊的可愛女孩告白"

        normalized = app.normalize_url(url)

        self.assertNotIn("年冬季", normalized)
        self.assertTrue(normalized.startswith("https://anime1.me/category/"))


if __name__ == "__main__":
    unittest.main()
