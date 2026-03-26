use fan_download::anime::{collect_video_items_from_pages, parse_next_page_url, parse_video_items};

const DEMO_HTML: &str = r#"
<html>
  <body>
    <article>
      <header><h2><a href="https://anime1.me/3">Title [03]</a></h2></header>
      <div class="entry-content"><video data-apireq="%7B%22e%22%3A%223b%22%7D"></video></div>
    </article>
    <article>
      <header><h2><a href="https://anime1.me/2">Title [02]</a></h2></header>
      <div class="entry-content"><video data-apireq="%7B%22e%22%3A%222b%22%7D"></video></div>
    </article>
    <article>
      <header><h2><a href="https://anime1.me/1">Title [01]</a></h2></header>
      <div class="entry-content"><video data-apireq="%7B%22e%22%3A%221b%22%7D"></video></div>
    </article>
  </body>
</html>
"#;

#[test]
fn parsing_extracts_and_reverses_episode_order() {
    let items = parse_video_items(DEMO_HTML);
    assert_eq!(3, items.len());
    assert_eq!("Title [01]", items[0].title);
    assert_eq!("{\"e\":\"1b\"}", items[0].api_req);
    assert_eq!("Title [03]", items[2].title);
}

#[test]
fn parsing_returns_empty_when_no_video_entries_exist() {
    let items = parse_video_items("<html><body><article><h2>no video</h2></article></body></html>");
    assert!(items.is_empty());
}

#[test]
fn parsing_extracts_next_page_link_only_for_same_category() {
    let html = r#"
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
      </body>
    </html>
    "#;

    let next_page = parse_next_page_url("https://anime1.me/category/2024%E7%A7%8B%E5%AD%A3/show", html);

    assert_eq!(
        Some("https://anime1.me/category/2024%E7%A7%8B%E5%AD%A3/show/page/2".to_string()),
        next_page
    );
}

#[test]
fn parsing_ignores_unrelated_pagination_links() {
    let html = r#"
    <html>
      <body>
        <div class="pagination">
          <nav class="navigation posts-navigation">
            <div class="nav-links">
              <div class="nav-previous">
                <a href="https://anime1.me/category/other-show/page/2">上一頁</a>
              </div>
            </div>
          </nav>
        </div>
      </body>
    </html>
    "#;

    let next_page = parse_next_page_url("https://anime1.me/category/2024%E7%A7%8B%E5%AD%A3/show", html);

    assert_eq!(None, next_page);
}

#[test]
fn collect_video_items_merges_and_sorts_across_pages() {
    let page_one = r#"
    <html>
      <body>
        <article>
          <header><h2><a href="https://anime1.me/3">Show [04]</a></h2></header>
          <div class="entry-content"><video data-apireq="%7B%22e%22%3A%224b%22%7D"></video></div>
        </article>
        <article>
          <header><h2><a href="https://anime1.me/2">Show [03]</a></h2></header>
          <div class="entry-content"><video data-apireq="%7B%22e%22%3A%223b%22%7D"></video></div>
        </article>
      </body>
    </html>
    "#;
    let page_two = r#"
    <html>
      <body>
        <article>
          <header><h2><a href="https://anime1.me/1">Show [02]</a></h2></header>
          <div class="entry-content"><video data-apireq="%7B%22e%22%3A%222b%22%7D"></video></div>
        </article>
        <article>
          <header><h2><a href="https://anime1.me/0">Show [01]</a></h2></header>
          <div class="entry-content"><video data-apireq="%7B%22e%22%3A%221b%22%7D"></video></div>
        </article>
      </body>
    </html>
    "#;

    let items = collect_video_items_from_pages(vec![page_one.to_string(), page_two.to_string()]);

    assert_eq!(
        vec!["Show [01]", "Show [02]", "Show [03]", "Show [04]"],
        items.iter().map(|item| item.title.as_str()).collect::<Vec<_>>()
    );
}
