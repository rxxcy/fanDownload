use crate::model::{DownloadFailure, DownloadSummary, EpisodeItem};
use futures::StreamExt;
use std::collections::{HashMap, VecDeque};
use std::future::Future;
use std::io::{stdout, Write};
use std::path::{Path, PathBuf};
use std::pin::Pin;
use std::sync::{Arc, Mutex};
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Instant;
use tokio::fs::File;
use tokio::io::AsyncWriteExt;
use tokio::task::{yield_now, JoinSet};

pub const DEFAULT_MAX_WORKERS: usize = 3;
pub type StopFlag = Arc<AtomicBool>;
pub type Printer = Arc<dyn Fn(String) + Send + Sync>;
pub type ProgressCallback = Arc<dyn Fn(u64, Option<u64>, f64) + Send + Sync>;
pub type DownloadFuture = Pin<Box<dyn Future<Output = Result<(), DownloadError>> + Send>>;
pub type DownloadFn = Arc<dyn Fn(EpisodeItem, Option<ProgressCallback>, Printer, StopFlag) -> DownloadFuture + Send + Sync>;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum DownloadError {
    Cancelled,
    Other(String),
}

impl std::fmt::Display for DownloadError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Cancelled => write!(f, "download cancelled"),
            Self::Other(message) => write!(f, "{}", message),
        }
    }
}

impl std::error::Error for DownloadError {}

#[derive(Default)]
struct ProgressState {
    last_bucket: i32,
    started: bool,
}

pub struct ParallelProgressReporter {
    printer: Printer,
    percent_step: u64,
    state: Mutex<HashMap<String, ProgressState>>,
}

impl ParallelProgressReporter {
    pub fn new(printer: Printer, percent_step: u64) -> Self {
        Self {
            printer,
            percent_step,
            state: Mutex::new(HashMap::new()),
        }
    }

    pub fn make_callback(self: &Arc<Self>, title: &str) -> ProgressCallback {
        let title = title.to_string();
        self.state.lock().expect("progress state lock").insert(title.clone(), ProgressState::default());
        let reporter = Arc::clone(self);
        Arc::new(move |downloaded, total_size, speed| {
            reporter.report(&title, downloaded, total_size, speed);
        })
    }

    fn report(&self, title: &str, downloaded: u64, total_size: Option<u64>, speed: f64) {
        let mut state = self.state.lock().expect("progress state lock");
        let entry = state.entry(title.to_string()).or_default();
        match total_size {
            None => {
                if !entry.started {
                    entry.started = true;
                    (self.printer)(format!("[进度] {}: 已开始下载", title));
                }
            }
            Some(total_size) => {
                let percent_done = ((downloaded as f64 / total_size as f64) * 100.0) as u64;
                let percent_bucket = ((percent_done / self.percent_step) * self.percent_step).min(100);
                if percent_bucket == 0 && percent_done < 100 {
                    return;
                }
                if percent_bucket as i32 <= entry.last_bucket {
                    return;
                }
                entry.last_bucket = percent_bucket as i32;
                let downloaded_mb = downloaded as f64 / 1024.0 / 1024.0;
                let total_mb = total_size as f64 / 1024.0 / 1024.0;
                (self.printer)(format!(
                    "[进度] {}: {}% ({:.2}Mb/{:.2}Mb) {:.2}Mb/s",
                    title, percent_done, downloaded_mb, total_mb, speed
                ));
            }
        }
    }
}

pub async fn download_selected_items(
    items: Vec<EpisodeItem>,
    max_workers: usize,
    downloader: DownloadFn,
    printer: Printer,
    progress_enabled: bool,
    stop_flag: StopFlag,
) -> DownloadSummary {
    if items.is_empty() {
        return DownloadSummary::default();
    }

    let worker_count = max_workers.min(items.len()).max(1);
    let progress_reporter = if progress_enabled && items.len() > 1 {
        Some(Arc::new(ParallelProgressReporter::new(Arc::clone(&printer), 10)))
    } else {
        None
    };

    let mut queue: VecDeque<EpisodeItem> = items.iter().cloned().collect();
    let mut join_set: JoinSet<(EpisodeItem, Result<(), DownloadError>)> = JoinSet::new();
    let mut summary = DownloadSummary::default();

    if worker_count == 1 {
        let item = queue.pop_front().expect("single item exists");
        match downloader(item.clone(), None, Arc::clone(&printer), Arc::clone(&stop_flag)).await {
            Ok(()) => {
                (printer)(format!("下载完成: {}", item.title));
                summary.successes.push(item.title);
            }
            Err(DownloadError::Cancelled) => {
                (printer)(format!("下载已取消: {}", item.title));
                summary.cancelled.push(item.title);
            }
            Err(DownloadError::Other(error)) => {
                (printer)(format!("下载失败: {} - {}", item.title, error));
                summary.failures.push(DownloadFailure { title: item.title, error });
            }
        }
        (printer)(format!("下载汇总: 成功 {} 集, 失败 {} 集", summary.successes.len(), summary.failures.len()));
        return summary;
    }

    (printer)(format!("并行下载已启动，最大并发数: {}", worker_count));
    spawn_ready_tasks(
        &mut queue,
        &mut join_set,
        worker_count,
        Arc::clone(&downloader),
        Arc::clone(&printer),
        progress_reporter.as_ref().map(Arc::clone),
        Arc::clone(&stop_flag),
    )
    .await;

    while let Some(result) = join_set.join_next().await {
        let (item, outcome) = result.expect("download task panicked");
        match outcome {
            Ok(()) => {
                (printer)(format!("下载完成: {}", item.title));
                summary.successes.push(item.title);
            }
            Err(DownloadError::Cancelled) => {
                (printer)(format!("下载已取消: {}", item.title));
                summary.cancelled.push(item.title);
            }
            Err(DownloadError::Other(error)) => {
                (printer)(format!("下载失败: {} - {}", item.title, error));
                summary.failures.push(DownloadFailure { title: item.title, error });
            }
        }

        if stop_flag.load(Ordering::SeqCst) {
            continue;
        }

        spawn_ready_tasks(
            &mut queue,
            &mut join_set,
            worker_count,
            Arc::clone(&downloader),
            Arc::clone(&printer),
            progress_reporter.as_ref().map(Arc::clone),
            Arc::clone(&stop_flag),
        )
        .await;
    }

    (printer)(format!("下载汇总: 成功 {} 集, 失败 {} 集", summary.successes.len(), summary.failures.len()));
    summary
}

async fn spawn_ready_tasks(
    queue: &mut VecDeque<EpisodeItem>,
    join_set: &mut JoinSet<(EpisodeItem, Result<(), DownloadError>)>,
    worker_count: usize,
    downloader: DownloadFn,
    printer: Printer,
    progress_reporter: Option<Arc<ParallelProgressReporter>>,
    stop_flag: StopFlag,
) {
    while join_set.len() < worker_count && !queue.is_empty() && !stop_flag.load(Ordering::SeqCst) {
        let item = queue.pop_front().expect("queue item exists");
        let task_item = item.clone();
        let task_printer = Arc::clone(&printer);
        let task_stop = Arc::clone(&stop_flag);
        let task_downloader = Arc::clone(&downloader);
        let progress_callback = progress_reporter.as_ref().map(|reporter| reporter.make_callback(&task_item.title));
        join_set.spawn(async move {
            (task_printer)(format!("开始下载: {}", task_item.title));
            let result = task_downloader(task_item.clone(), progress_callback, task_printer, task_stop).await;
            (task_item, result)
        });
        yield_now().await;
    }
}

pub async fn download_video(
    client: reqwest::Client,
    src: String,
    title: String,
    cookie: String,
    progress_callback: Option<ProgressCallback>,
    stop_flag: StopFlag,
) -> Result<(), DownloadError> {
    let file_path = create_output_path(&title).map_err(DownloadError::Other)?;
    let mut request = client.get(src).header(reqwest::header::REFERER, "https://v.anime1.me/");
    if !cookie.is_empty() {
        request = request.header(reqwest::header::COOKIE, cookie);
    }

    let response = request.send().await.map_err(|err| DownloadError::Other(err.to_string()))?;
    let total_size = response.content_length();
    let mut stream = response.bytes_stream();
    let mut file = File::create(&file_path).await.map_err(|err| DownloadError::Other(err.to_string()))?;
    let mut downloaded: u64 = 0;
    let start = Instant::now();

    if progress_callback.is_none() {
        println!("下载中...");
    }

    while let Some(chunk) = stream.next().await {
        if stop_flag.load(Ordering::SeqCst) {
            cleanup_partial_file(&file_path).await;
            return Err(DownloadError::Cancelled);
        }
        let chunk = chunk.map_err(|err| DownloadError::Other(err.to_string()))?;
        file.write_all(&chunk).await.map_err(|err| DownloadError::Other(err.to_string()))?;
        downloaded += chunk.len() as u64;
        let elapsed = start.elapsed().as_secs_f64().max(0.001);
        let speed = downloaded as f64 / 1024.0 / 1024.0 / elapsed;
        if let Some(callback) = &progress_callback {
            callback(downloaded, total_size, speed);
        } else if let Some(total) = total_size {
            print_progress(downloaded, total, speed);
        }
    }

    file.flush().await.map_err(|err| DownloadError::Other(err.to_string()))?;
    if progress_callback.is_none() {
        println!();
        println!("{} 下载完成", title);
    }
    Ok(())
}

pub async fn write_chunks_for_test(
    file_path: &Path,
    chunks: Vec<Vec<u8>>,
    total_size: Option<u64>,
    progress_callback: Option<ProgressCallback>,
    stop_flag: StopFlag,
) -> Result<(), DownloadError> {
    let mut file = File::create(file_path).await.map_err(|err| DownloadError::Other(err.to_string()))?;
    let mut downloaded = 0u64;
    let start = Instant::now();
    for chunk in chunks {
        if stop_flag.load(Ordering::SeqCst) {
            cleanup_partial_file(file_path).await;
            return Err(DownloadError::Cancelled);
        }
        file.write_all(&chunk).await.map_err(|err| DownloadError::Other(err.to_string()))?;
        downloaded += chunk.len() as u64;
        let speed = downloaded as f64 / 1024.0 / 1024.0 / start.elapsed().as_secs_f64().max(0.001);
        if let Some(callback) = &progress_callback {
            callback(downloaded, total_size, speed);
        }
    }
    file.flush().await.map_err(|err| DownloadError::Other(err.to_string()))?;
    Ok(())
}

pub fn create_output_path(title: &str) -> Result<PathBuf, String> {
    let safe_title = sanitize_title(title);
    let dir = PathBuf::from("video").join(&safe_title);
    std::fs::create_dir_all(&dir).map_err(|err| err.to_string())?;
    Ok(dir.join(format!("{}.mp4", safe_title)))
}

pub fn sanitize_title(title: &str) -> String {
    let (base_title, episode_suffix) = split_episode_suffix(title);
    let cleaned_base: String = base_title
        .trim()
        .chars()
        .map(|ch| match ch {
            '\\' | '/' | ':' | '*' | '?' | '"' | '<' | '>' | '|' => '_',
            _ => ch,
        })
        .collect();

    match episode_suffix {
        Some(suffix) if !cleaned_base.is_empty() => format!("{}-{}", cleaned_base, suffix),
        _ => cleaned_base,
    }
}

fn split_episode_suffix(title: &str) -> (String, Option<String>) {
    let trimmed = title.trim();
    if let Some(start) = trimmed.rfind('[') {
        if trimmed.ends_with(']') {
            let number = &trimmed[start + 1..trimmed.len() - 1];
            if !number.is_empty() && number.chars().all(|ch| ch.is_ascii_digit()) {
                let base = trimmed[..start].trim_end().to_string();
                return (base, Some(number.to_string()));
            }
        }
    }
    (trimmed.to_string(), None)
}

async fn cleanup_partial_file(file_path: &Path) {
    let _ = tokio::fs::remove_file(file_path).await;
}

fn print_progress(downloaded: u64, total_size: u64, speed: f64) {
    let done = ((50 * downloaded) / total_size) as usize;
    let percent_done = ((100 * downloaded) / total_size) as usize;
    let downloaded_mb = downloaded as f64 / 1024.0 / 1024.0;
    let total_mb = total_size as f64 / 1024.0 / 1024.0;
    print!(
        "\r[{}{}] {}% ({:.2}Mb/{:.2}Mb) {:.2}Mb/s",
        "#".repeat(done),
        " ".repeat(50 - done),
        percent_done,
        downloaded_mb,
        total_mb,
        speed
    );
    let _ = stdout().flush();
}
