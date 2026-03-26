use crossterm::cursor::{Hide, MoveTo, Show};
use crossterm::terminal::{Clear, ClearType, EnterAlternateScreen, LeaveAlternateScreen};
use crossterm::{execute, queue};
use std::fmt::Write as _;
use std::io::{stdout, Stdout, Write};
use tokio::sync::mpsc;
use tokio::time::{self, Duration};

#[derive(Clone, Debug, PartialEq)]
pub enum ProgressEvent {
    Assigned { slot: usize, title: String },
    Started { slot: usize },
    Progress {
        slot: usize,
        downloaded: u64,
        total_size: Option<u64>,
        speed_mb_per_sec: f64,
    },
    Completed { slot: usize },
    Failed { slot: usize, error: String },
    Cancelled { slot: usize },
}

#[derive(Clone, Debug, PartialEq)]
pub enum SlotStatus {
    Idle,
    Pending,
    Running,
    Completed,
    Failed(String),
    Cancelled,
}

#[derive(Clone, Debug, PartialEq)]
pub struct SlotState {
    pub title: String,
    pub status: SlotStatus,
    pub downloaded: u64,
    pub total_size: Option<u64>,
    pub speed_mb_per_sec: f64,
}

#[derive(Clone, Debug, PartialEq)]
pub struct ProgressPanelState {
    total_tasks: usize,
    success_count: usize,
    failure_count: usize,
    cancelled_count: usize,
    slots: Vec<Option<SlotState>>,
}

impl ProgressPanelState {
    pub fn new(slot_count: usize, total_tasks: usize) -> Self {
        Self {
            total_tasks,
            success_count: 0,
            failure_count: 0,
            cancelled_count: 0,
            slots: vec![None; slot_count],
        }
    }

    pub fn apply(&mut self, event: ProgressEvent) {
        match event {
            ProgressEvent::Assigned { slot, title } => {
                self.slots[slot] = Some(SlotState {
                    title,
                    status: SlotStatus::Pending,
                    downloaded: 0,
                    total_size: None,
                    speed_mb_per_sec: 0.0,
                });
            }
            ProgressEvent::Started { slot } => {
                if let Some(state) = self.slots.get_mut(slot).and_then(Option::as_mut) {
                    state.status = SlotStatus::Running;
                }
            }
            ProgressEvent::Progress { slot, downloaded, total_size, speed_mb_per_sec } => {
                if let Some(state) = self.slots.get_mut(slot).and_then(Option::as_mut) {
                    state.downloaded = downloaded;
                    state.total_size = total_size;
                    state.speed_mb_per_sec = speed_mb_per_sec;
                    if !matches!(state.status, SlotStatus::Completed | SlotStatus::Failed(_) | SlotStatus::Cancelled) {
                        state.status = SlotStatus::Running;
                    }
                }
            }
            ProgressEvent::Completed { slot } => {
                if let Some(state) = self.slots.get_mut(slot).and_then(Option::as_mut) {
                    state.status = SlotStatus::Completed;
                    self.success_count += 1;
                }
            }
            ProgressEvent::Failed { slot, error } => {
                if let Some(state) = self.slots.get_mut(slot).and_then(Option::as_mut) {
                    state.status = SlotStatus::Failed(error);
                    self.failure_count += 1;
                }
            }
            ProgressEvent::Cancelled { slot } => {
                if let Some(state) = self.slots.get_mut(slot).and_then(Option::as_mut) {
                    state.status = SlotStatus::Cancelled;
                    self.cancelled_count += 1;
                }
            }
        }
    }

    pub fn slot_state(&self, slot: usize) -> Option<&SlotState> {
        self.slots.get(slot).and_then(|entry| entry.as_ref())
    }

    pub fn summary_line(&self) -> String {
        let finished = self.success_count + self.failure_count + self.cancelled_count;
        format!(
            "并发 {} | 总进度 {}/{} | 成功 {} | 失败 {} | 取消 {}",
            self.slots.len(),
            finished,
            self.total_tasks,
            self.success_count,
            self.failure_count,
            self.cancelled_count
        )
    }

    pub fn slot_line(&self, slot: usize) -> String {
        match self.slots.get(slot).and_then(|item| item.as_ref()) {
            None => format!("[{}] Idle", slot + 1),
            Some(state) => {
                let status = match &state.status {
                    SlotStatus::Idle => "Idle".to_string(),
                    SlotStatus::Pending => "Pending".to_string(),
                    SlotStatus::Running => "Running".to_string(),
                    SlotStatus::Completed => "Done".to_string(),
                    SlotStatus::Failed(_) => "Failed".to_string(),
                    SlotStatus::Cancelled => "Cancelled".to_string(),
                };
                let progress = format_progress(state.downloaded, state.total_size);
                format!(
                    "[{}] {:<9} {:<28} {} {:.2} MB/s",
                    slot + 1,
                    status,
                    truncate_title(&state.title, 28),
                    progress,
                    state.speed_mb_per_sec
                )
            }
        }
    }

    pub fn render_lines(&self) -> Vec<String> {
        let mut lines = Vec::with_capacity(self.slots.len() + 2);
        lines.push(self.summary_line());
        for index in 0..self.slots.len() {
            lines.push(self.slot_line(index));
        }
        lines.push("Ctrl+C 可取消全部下载".to_string());
        lines
    }
}

pub async fn run_progress_panel(
    mut receiver: mpsc::UnboundedReceiver<ProgressEvent>,
    slot_count: usize,
    total_tasks: usize,
) -> Result<(), String> {
    let mut terminal = TerminalSession::new().map_err(|err| err.to_string())?;
    let mut state = ProgressPanelState::new(slot_count, total_tasks);
    let mut ticker = time::interval(Duration::from_millis(100));
    let mut dirty = true;

    loop {
        tokio::select! {
            maybe_event = receiver.recv() => {
                match maybe_event {
                    Some(event) => {
                        state.apply(event);
                        dirty = true;
                    }
                    None => {
                        if dirty {
                            terminal.draw(&state).map_err(|err| err.to_string())?;
                        }
                        break;
                    }
                }
            }
            _ = ticker.tick() => {
                if dirty {
                    terminal.draw(&state).map_err(|err| err.to_string())?;
                    dirty = false;
                }
            }
        }
    }

    terminal.finish().map_err(|err| err.to_string())
}

struct TerminalSession {
    stdout: Stdout,
    finished: bool,
}

impl TerminalSession {
    fn new() -> std::io::Result<Self> {
        let mut stdout = stdout();
        execute!(stdout, EnterAlternateScreen, Hide)?;
        Ok(Self { stdout, finished: false })
    }

    fn draw(&mut self, state: &ProgressPanelState) -> std::io::Result<()> {
        let mut buffer = String::new();
        for line in state.render_lines() {
            let _ = writeln!(&mut buffer, "{}", line);
        }

        queue!(self.stdout, MoveTo(0, 0), Clear(ClearType::All))?;
        self.stdout.write_all(buffer.as_bytes())?;
        self.stdout.flush()
    }

    fn finish(&mut self) -> std::io::Result<()> {
        if !self.finished {
            execute!(self.stdout, Show, LeaveAlternateScreen)?;
            self.finished = true;
        }
        Ok(())
    }
}

impl Drop for TerminalSession {
    fn drop(&mut self) {
        let _ = self.finish();
    }
}

fn truncate_title(title: &str, max_chars: usize) -> String {
    let count = title.chars().count();
    if count <= max_chars {
        return title.to_string();
    }

    let truncated: String = title.chars().take(max_chars.saturating_sub(1)).collect();
    format!("{}…", truncated)
}

fn format_progress(downloaded: u64, total_size: Option<u64>) -> String {
    let downloaded_mb = downloaded as f64 / 1024.0 / 1024.0;
    match total_size {
        Some(total) if total > 0 => {
            let total_mb = total as f64 / 1024.0 / 1024.0;
            let percent = ((downloaded as f64 / total as f64) * 100.0).round() as u64;
            format!("{:>3}% {:>6.1}/{:<6.1} MB", percent.min(100), downloaded_mb, total_mb)
        }
        _ => format!(" --% {:>6.1}/stream MB", downloaded_mb),
    }
}
