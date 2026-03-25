use fan_download::anime::parse_video_items;

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
