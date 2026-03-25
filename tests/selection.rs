use fan_download::model::EpisodeItem;
use fan_download::selection::{parse_selection_input, render_episode_list};

fn sample_items() -> Vec<EpisodeItem> {
    vec![
        EpisodeItem { title: "Episode 1".to_string(), api_req: "req-1".to_string() },
        EpisodeItem { title: "Episode 2".to_string(), api_req: "req-2".to_string() },
        EpisodeItem { title: "Episode 3".to_string(), api_req: "req-3".to_string() },
    ]
}

#[test]
fn selection_returns_all_items_for_empty_input() {
    let items = sample_items();
    let selected = parse_selection_input("", &items).unwrap();
    assert_eq!(items, selected);
}

#[test]
fn selection_supports_one_based_multi_select() {
    let items = sample_items();
    let selected = parse_selection_input("1 3", &items).unwrap();
    assert_eq!(vec![items[0].clone(), items[2].clone()], selected);
}

#[test]
fn selection_renders_one_based_indexes() {
    let items = sample_items();
    let rendered = render_episode_list(&items);
    assert_eq!("1. Episode 1", rendered[0]);
    assert_eq!("2. Episode 2", rendered[1]);
}
