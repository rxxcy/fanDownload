use crate::model::EpisodeItem;
use reqwest::header::{HeaderMap, HeaderValue, REFERER, USER_AGENT};
use scraper::{Html, Selector};
use serde::Deserialize;
use url::Url;

const API_URL: &str = "https://v.anime1.me/api";
const REFERER_VALUE: &str = "https://v.anime1.me/";
const USER_AGENT_VALUE: &str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36";

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
