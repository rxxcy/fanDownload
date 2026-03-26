import unittest

import app


PAGE_ONE = """
<html>
  <body>
    <div class="pagination">
      <nav class="navigation posts-navigation">
        <div class="nav-links">
          <div class="nav-previous">
            <a href="https://anime1.me/category/2024%E7%A7%8B%E5%AD%A3/show/page/2">上一頁</a>
          </div>
        </div>
      </nav>
    </div>
    <article>
      <header><h2><a href="https://anime1.me/4">Show [04]</a></h2></header>
      <div class="entry-content"><video data-apireq="%7B%22e%22%3A%224b%22%7D"></video></div>
    </article>
    <article>
      <header><h2><a href="https://anime1.me/3">Show [03]</a></h2></header>
      <div class="entry-content"><video data-apireq="%7B%22e%22%3A%223b%22%7D"></video></div>
    </article>
  </body>
</html>
"""

PAGE_TWO = """
<html>
  <body>
    <article>
      <header><h2><a href="https://anime1.me/2">Show [02]</a></h2></header>
      <div class="entry-content"><video data-apireq="%7B%22e%22%3A%222b%22%7D"></video></div>
    </article>
    <article>
      <header><h2><a href="https://anime1.me/1">Show [01]</a></h2></header>
      <div class="entry-content"><video data-apireq="%7B%22e%22%3A%221b%22%7D"></video></div>
    </article>
  </body>
</html>
"""


class PaginationTests(unittest.TestCase):
    def test_parse_next_page_url_only_accepts_same_category(self):
        next_page = app.parse_next_page_url("https://anime1.me/category/2024%E7%A7%8B%E5%AD%A3/show", PAGE_ONE)
        self.assertEqual("https://anime1.me/category/2024%E7%A7%8B%E5%AD%A3/show/page/2", next_page)

    def test_parse_next_page_url_rejects_other_category(self):
        html = PAGE_ONE.replace("show/page/2", "other-show/page/2")
        self.assertIsNone(app.parse_next_page_url("https://anime1.me/category/2024%E7%A7%8B%E5%AD%A3/show", html))

    def test_collect_video_items_from_pages_merges_and_sorts_across_pages(self):
        items = app.collect_video_items_from_pages([PAGE_ONE, PAGE_TWO])
        self.assertEqual(
            ["Show [01]", "Show [02]", "Show [03]", "Show [04]"],
            [item["title"] for item in items],
        )


if __name__ == "__main__":
    unittest.main()
