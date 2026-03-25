use crate::model::EpisodeItem;

pub fn parse_selection_input(input: &str, items: &[EpisodeItem]) -> Result<Vec<EpisodeItem>, String> {
    let trimmed = input.trim();
    if trimmed.is_empty() {
        return Ok(items.to_vec());
    }

    let mut selected = Vec::new();
    let mut seen = std::collections::HashSet::new();

    for part in trimmed.split_whitespace() {
        let index: usize = part.parse().map_err(|_| "请输入有效数字".to_string())?;
        if index == 0 || index > items.len() {
            return Err("索引超出范围".to_string());
        }
        if seen.insert(index) {
            selected.push(items[index - 1].clone());
        }
    }

    Ok(selected)
}

pub fn render_episode_list(items: &[EpisodeItem]) -> Vec<String> {
    items
        .iter()
        .enumerate()
        .map(|(index, item)| format!("{}. {}", index + 1, item.title))
        .collect()
}
