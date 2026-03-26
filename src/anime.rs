use crate::model::EpisodeItem;
use reqwest::header::{HeaderMap, HeaderValue, REFERER, USER_AGENT};
use scraper::{Html, Selector};
use serde::Deserialize;
use std::collections::HashSet;
use url::Url;

const API_URL: &str = "https://v.anime1.me/api";
const REFERER_VALUE: &str = "https://v.anime1.me/";
const USER_AGENT_VALUE: &str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36";
const MAX_CATEGORY_PAGES: usize = 20;

#[derive(Deserialize)]
struct ApiSource {
    src: String,
}

#[derive(Deserialize)]
struct ApiResponse {
    s: Vec<ApiSource>,
}

pub fn normalize_url(url: &str) -> Result<String, String> {
    let parsed = Url::parse(url.trim()).map_err(|err| err.to_string())?;
    Ok(parsed.to_string())
}

pub fn parse_video_items(html: &str) -> Vec<EpisodeItem> {
    let document = Html::parse_document(html);
    let article_selector = Selector::parse("article").expect("valid article selector");
    let title_selector = Selector::parse("h2 a").expect("valid title selector");
    let video_selector = Selector::parse("video[data-apireq]").expect("valid video selector");

    let mut items = Vec::new();
    for article in document.select(&article_selector) {
        let title = article
            .select(&title_selector)
            .next()
            .map(|node| node.text().collect::<String>().trim().to_string())
            .unwrap_or_default();
        let api_req = article
            .select(&video_selector)
            .next()
            .and_then(|node| node.value().attr("data-apireq"))
            .map(|value| urlencoding::decode(value).map(|decoded| decoded.into_owned()).unwrap_or_default())
            .unwrap_or_default();

        if !title.is_empty() && !api_req.is_empty() {
            items.push(EpisodeItem { title, api_req });
        }
    }

    items.reverse();
    items
}

pub fn parse_next_page_url(current_url: &str, html: &str) -> Option<String> {
    let current = Url::parse(current_url).ok()?;
    let current_category_root = category_root(&current)?;
    let document = Html::parse_document(html);
    let next_selector = Selector::parse(".nav-previous a").ok()?;
    let href = document
        .select(&next_selector)
        .next()
        .and_then(|node| node.value().attr("href"))?;

    let next = current.join(href).ok()?;
    if next.domain() != current.domain() {
        return None;
    }
    if category_root(&next)? != current_category_root {
        return None;
    }

    Some(next.to_string())
}

pub fn collect_video_items_from_pages(pages: Vec<String>) -> Vec<EpisodeItem> {
    let mut seen = HashSet::new();
    let mut merged = Vec::new();

    for html in pages {
        for item in parse_video_items(&html) {
            let key = format!("{}\u{0}{}", item.title, item.api_req);
            if seen.insert(key) {
                merged.push(item);
            }
        }
    }

    sort_episode_items(merged)
}

pub async fn fetch_category_items(client: &reqwest::Client, start_url: &str) -> Result<Vec<EpisodeItem>, String> {
    let mut visited = HashSet::new();
    let mut pages = Vec::new();
    let mut current_url = normalize_url(start_url)?;

    for _ in 0..MAX_CATEGORY_PAGES {
        if !visited.insert(current_url.clone()) {
            break;
        }

        let html = fetch_page(client, &current_url).await?;
        let next_page = parse_next_page_url(&current_url, &html);
        pages.push(html);

        match next_page {
            Some(next) if !visited.contains(&next) => current_url = next,
            _ => break,
        }
    }

    Ok(collect_video_items_from_pages(pages))
}

pub fn build_client() -> Result<reqwest::Client, String> {
    let mut headers = HeaderMap::new();
    headers.insert(USER_AGENT, HeaderValue::from_static(USER_AGENT_VALUE));
    headers.insert(REFERER, HeaderValue::from_static(REFERER_VALUE));

    let mut builder = reqwest::Client::builder().default_headers(headers);

    if let Ok(proxy) = std::env::var("FAN_DOWNLOAD_HTTP_PROXY").or_else(|_| std::env::var("HTTP_PROXY")) {
        builder = builder.proxy(reqwest::Proxy::http(&proxy).map_err(|err| err.to_string())?);
    }
    if let Ok(proxy) = std::env::var("FAN_DOWNLOAD_HTTPS_PROXY").or_else(|_| std::env::var("HTTPS_PROXY")) {
        builder = builder.proxy(reqwest::Proxy::https(&proxy).map_err(|err| err.to_string())?);
    }

    builder.build().map_err(|err| err.to_string())
}

pub async fn fetch_page(client: &reqwest::Client, url: &str) -> Result<String, String> {
    let normalized = normalize_url(url)?;
    let response = client.get(normalized).send().await.map_err(|err| err.to_string())?;
    response.text().await.map_err(|err| err.to_string())
}

pub async fn resolve_download_url(client: &reqwest::Client, api_req: &str) -> Result<(String, String), String> {
    let response = client
        .post(API_URL)
        .form(&[("d", api_req)])
        .send()
        .await
        .map_err(|err| err.to_string())?;

    let headers = response.headers().clone();
    let body: ApiResponse = response.json().await.map_err(|err| err.to_string())?;
    let src = body
        .s
        .first()
        .map(|item| item.src.clone())
        .ok_or_else(|| "未获取到下载地址".to_string())?;

    let cookie = headers
        .get_all(reqwest::header::SET_COOKIE)
        .iter()
        .filter_map(|value| value.to_str().ok())
        .map(|value| value.split(';').next().unwrap_or_default().to_string())
        .filter(|value| !value.is_empty())
        .collect::<Vec<_>>()
        .join("; ");

    if src.starts_with("http") {
        Ok((src, cookie))
    } else {
        Ok((format!("https:{}", src), cookie))
    }
}

fn category_root(url: &Url) -> Option<String> {
    let mut segments = url.path_segments()?.collect::<Vec<_>>();
    if segments.len() >= 2 && segments[segments.len() - 2] == "page" && segments.last()?.chars().all(|ch| ch.is_ascii_digit()) {
        segments.truncate(segments.len() - 2);
    }
    let path = format!("/{}", segments.join("/"));
    Some(path.trim_end_matches('/').to_string())
}

fn sort_episode_items(items: Vec<EpisodeItem>) -> Vec<EpisodeItem> {
    let mut enumerated = items.into_iter().enumerate().collect::<Vec<_>>();
    enumerated.sort_by(|(left_index, left_item), (right_index, right_item)| {
        match (episode_number(&left_item.title), episode_number(&right_item.title)) {
            (Some(left_number), Some(right_number)) => left_number.cmp(&right_number),
            (Some(_), None) => std::cmp::Ordering::Less,
            (None, Some(_)) => std::cmp::Ordering::Greater,
            (None, None) => left_index.cmp(right_index),
        }
    });
    enumerated.into_iter().map(|(_, item)| item).collect()
}

fn episode_number(title: &str) -> Option<u32> {
    let trimmed = title.trim();
    let start = trimmed.rfind('[')?;
    if !trimmed.ends_with(']') {
        return None;
    }
    trimmed[start + 1..trimmed.len() - 1].parse::<u32>().ok()
}

