use fan_download::download::{download_selected_items, write_chunks_for_test, DownloadError, DownloadFn, DEFAULT_MAX_WORKERS};
use fan_download::model::EpisodeItem;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use tempfile::tempdir;
use tokio::time::{sleep, Duration};

fn sample_items(count: usize) -> Vec<EpisodeItem> {
    (0..count)
        .map(|index| EpisodeItem {
            title: format!("Episode {}", index),
            api_req: format!("req-{}", index),
        })
        .collect()
}

#[tokio::test]
async fn downloads_limit_parallelism_to_three_workers() {
    let items = sample_items(5);
    let active = Arc::new(AtomicUsize::new(0));
    let max_active = Arc::new(AtomicUsize::new(0));
    let downloader: DownloadFn = {
        let active = Arc::clone(&active);
        let max_active = Arc::clone(&max_active);
        Arc::new(move |_item, _progress, _printer, _stop| {
            let active = Arc::clone(&active);
            let max_active = Arc::clone(&max_active);
            Box::pin(async move {
                let current = active.fetch_add(1, Ordering::SeqCst) + 1;
                max_active.fetch_max(current, Ordering::SeqCst);
                sleep(Duration::from_millis(50)).await;
                active.fetch_sub(1, Ordering::SeqCst);
                Ok(())
            })
        })
    };
    let summary = download_selected_items(
        items.clone(),
        DEFAULT_MAX_WORKERS,
        downloader,
        Arc::new(|_line| {}),
        false,
        Arc::new(AtomicBool::new(false)),
    )
    .await;
    assert_eq!(3, max_active.load(Ordering::SeqCst));
    assert_eq!(items.iter().map(|item| item.title.clone()).collect::<Vec<_>>(), summary.successes);
    assert!(summary.failures.is_empty());
}

#[tokio::test]
async fn downloads_collect_failures_without_stopping_other_tasks() {
    let items = sample_items(3);
    let downloader: DownloadFn = Arc::new(move |item, _progress, _printer, _stop| {
        Box::pin(async move {
            if item.title == "Episode 1" {
                Err(DownloadError::Other("network error".to_string()))
            } else {
                Ok(())
            }
        })
    });
    let summary = download_selected_items(
        items,
        DEFAULT_MAX_WORKERS,
        downloader,
        Arc::new(|_line| {}),
        false,
        Arc::new(AtomicBool::new(false)),
    )
    .await;
    assert_eq!(vec!["Episode 0".to_string(), "Episode 2".to_string()], summary.successes);
    assert_eq!(1, summary.failures.len());
    assert_eq!("Episode 1", summary.failures[0].title);
}

#[tokio::test]
async fn downloads_only_print_start_for_running_workers() {
    let items = sample_items(5);
    let logs = Arc::new(Mutex::new(Vec::new()));
    let started = Arc::new(AtomicUsize::new(0));
    let release = Arc::new(AtomicBool::new(false));
    let downloader: DownloadFn = {
        let started = Arc::clone(&started);
        let release = Arc::clone(&release);
        Arc::new(move |_item, _progress, _printer, _stop| {
            let started = Arc::clone(&started);
            let release = Arc::clone(&release);
            Box::pin(async move {
                started.fetch_add(1, Ordering::SeqCst);
                while !release.load(Ordering::SeqCst) {
                    sleep(Duration::from_millis(10)).await;
                }
                Ok(())
            })
        })
    };
    let printer = {
        let logs = Arc::clone(&logs);
        Arc::new(move |line: String| {
            logs.lock().unwrap().push(line);
        })
    };
    let task = tokio::spawn(download_selected_items(
        items,
        DEFAULT_MAX_WORKERS,
        downloader,
        printer,
        false,
        Arc::new(AtomicBool::new(false)),
    ));
    while started.load(Ordering::SeqCst) < 3 {
        sleep(Duration::from_millis(10)).await;
    }
    sleep(Duration::from_millis(50)).await;
    let start_logs = logs
        .lock()
        .unwrap()
        .iter()
        .filter(|line| line.starts_with("开始下载: "))
        .cloned()
        .collect::<Vec<_>>();
    assert_eq!(
        vec![
            "开始下载: Episode 0".to_string(),
            "开始下载: Episode 1".to_string(),
            "开始下载: Episode 2".to_string(),
        ],
        start_logs
    );
    release.store(true, Ordering::SeqCst);
    let _ = task.await.unwrap();
}

#[tokio::test]
async fn cancellation_removes_partial_file() {
    let dir = tempdir().unwrap();
    let file_path = dir.path().join("episode.mp4");
    let stop = Arc::new(AtomicBool::new(false));
    let result = write_chunks_for_test(
        &file_path,
        vec![vec![1; 4096], vec![2; 4096]],
        Some(8192),
        None,
        Arc::clone(&stop),
    )
    .await;
    assert!(result.is_ok());
    stop.store(true, Ordering::SeqCst);
    let second_path = dir.path().join("episode2.mp4");
    let cancelled = write_chunks_for_test(
        &second_path,
        vec![vec![1; 4096], vec![2; 4096]],
        Some(8192),
        None,
        Arc::clone(&stop),
    )
    .await;
    assert!(matches!(cancelled, Err(DownloadError::Cancelled)));
    assert!(!second_path.exists());
}

#[tokio::test]
async fn stop_signal_prevents_new_tasks_from_starting() {
    let items = sample_items(5);
    let stop = Arc::new(AtomicBool::new(false));
    let started = Arc::new(Mutex::new(Vec::new()));
    let downloader: DownloadFn = {
        let stop = Arc::clone(&stop);
        let started = Arc::clone(&started);
        Arc::new(move |item, _progress, _printer, _task_stop| {
            let stop = Arc::clone(&stop);
            let started = Arc::clone(&started);
            Box::pin(async move {
                started.lock().unwrap().push(item.title.clone());
                stop.store(true, Ordering::SeqCst);
                sleep(Duration::from_millis(20)).await;
                Ok(())
            })
        })
    };
    let summary = download_selected_items(
        items,
        DEFAULT_MAX_WORKERS,
        downloader,
        Arc::new(|_line| {}),
        false,
        Arc::clone(&stop),
    )
    .await;
    assert_eq!(vec!["Episode 0".to_string()], *started.lock().unwrap());
    assert_eq!(vec!["Episode 0".to_string()], summary.successes);
}

#[test]
fn create_output_path_uses_shared_series_directory_and_episode_file_name() {
    let path = fan_download::download::create_output_path("異世界的處置依社畜而定 [02]").unwrap();
    let normalized = path.to_string_lossy().replace('\\', "/");
    assert!(normalized.ends_with("video/異世界的處置依社畜而定/異世界的處置依社畜而定-02.mp4"));
}
