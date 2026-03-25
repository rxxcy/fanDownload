#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EpisodeItem {
    pub title: String,
    pub api_req: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct DownloadFailure {
    pub title: String,
    pub error: String,
}

#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct DownloadSummary {
    pub successes: Vec<String>,
    pub failures: Vec<DownloadFailure>,
    pub cancelled: Vec<String>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum DownloadTaskResult {
    Success(String),
    Failed(DownloadFailure),
    Cancelled(String),
}
