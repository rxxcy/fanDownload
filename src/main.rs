use fan_download::anime::{build_client, fetch_page, parse_video_items, resolve_download_url};
use fan_download::download::{download_selected_items, download_video, DownloadError, DownloadFn, Printer, ProgressCallback, StopFlag, DEFAULT_MAX_WORKERS};
use fan_download::model::EpisodeItem;
use fan_download::selection::{parse_selection_input, render_episode_list};
use std::io::{self, Write};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};

fn prompt(message: &str) -> io::Result<String> {
    print!("{}", message);
    io::stdout().flush()?;
    let mut input = String::new();
    io::stdin().read_line(&mut input)?;
    Ok(input.trim().to_string())
}

fn print_episode_lines(items: &[EpisodeItem]) {
    println!("页面内可下载的视频：");
    for line in render_episode_list(items) {
        println!("{}", line);
    }
}

fn runtime_downloader(client: reqwest::Client) -> DownloadFn {
    Arc::new(move |item: EpisodeItem, progress_callback: Option<ProgressCallback>, printer: Printer, stop_flag: StopFlag| {
        let client = client.clone();
        Box::pin(async move {
            printer(format!("获取 {} 真实下载地址", item.title));
            let (src, cookie) = resolve_download_url(&client, &item.api_req)
                .await
                .map_err(DownloadError::Other)?;
            download_video(client.clone(), src, item.title.clone(), cookie, progress_callback, stop_flag).await
        })
    })
}

#[tokio::main]
async fn main() {
    let stop_flag = Arc::new(AtomicBool::new(false));
    let stop_handler = Arc::clone(&stop_flag);
    ctrlc::set_handler(move || {
        if !stop_handler.swap(true, Ordering::SeqCst) {
            println!("\n正在停止下载，请稍候...");
        }
    })
    .expect("failed to install ctrl+c handler");

    let page_url = loop {
        match prompt("页面链接：") {
            Ok(input) if !input.is_empty() => break input,
            Ok(_) => println!("请输入页面链接："),
            Err(error) => {
                eprintln!("读取输入失败: {}", error);
                return;
            }
        }
    };

    let client = match build_client() {
        Ok(client) => client,
        Err(error) => {
            eprintln!("初始化客户端失败: {}", error);
            return;
        }
    };

    let html = match fetch_page(&client, &page_url).await {
        Ok(html) => html,
        Err(error) => {
            eprintln!("获取页面失败: {}", error);
            return;
        }
    };

    let items = parse_video_items(&html);
    if items.is_empty() {
        println!("页面内未找到可下载视频");
        return;
    }

    print_episode_lines(&items);
    let selected_items = loop {
        match prompt("\n输入索引（空格分隔，回车默认全部）：") {
            Ok(input) => match parse_selection_input(&input, &items) {
                Ok(selected) => break selected,
                Err(error) => println!("{}", error),
            },
            Err(error) => {
                eprintln!("读取输入失败: {}", error);
                return;
            }
        }
    };

    let printer: Printer = Arc::new(|line: String| println!("{}", line));
    let summary = download_selected_items(
        selected_items,
        DEFAULT_MAX_WORKERS,
        runtime_downloader(client),
        printer,
        true,
        Arc::clone(&stop_flag),
    )
    .await;

    if stop_flag.load(Ordering::SeqCst) && (!summary.successes.is_empty() || !summary.cancelled.is_empty()) {
        println!("已取消下载，程序退出");
    }
}
