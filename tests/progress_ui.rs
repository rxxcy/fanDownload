use fan_download::progress_ui::{ProgressEvent, ProgressPanelState, SlotStatus};

#[test]
fn panel_state_updates_slot_progress_and_reuses_completed_slot() {
    let mut state = ProgressPanelState::new(3, 5);

    state.apply(ProgressEvent::Assigned { slot: 0, title: "Episode 1".to_string() });
    state.apply(ProgressEvent::Started { slot: 0 });
    state.apply(ProgressEvent::Progress {
        slot: 0,
        downloaded: 50 * 1024 * 1024,
        total_size: Some(100 * 1024 * 1024),
        speed_mb_per_sec: 3.25,
    });

    let running_line = state.slot_line(0);
    assert!(running_line.contains("Episode 1"));
    assert!(running_line.contains("50%"));
    assert!(running_line.contains("3.25 MB/s"));

    state.apply(ProgressEvent::Completed { slot: 0 });
    assert_eq!("并发 3 | 总进度 1/5 | 成功 1 | 失败 0 | 取消 0", state.summary_line());

    state.apply(ProgressEvent::Assigned { slot: 0, title: "Episode 4".to_string() });
    let reassigned_line = state.slot_line(0);
    assert!(reassigned_line.contains("Episode 4"));
    assert!(reassigned_line.contains("Pending"));
}

#[test]
fn panel_state_tracks_failures_and_cancellations() {
    let mut state = ProgressPanelState::new(2, 4);

    state.apply(ProgressEvent::Assigned { slot: 0, title: "Episode 1".to_string() });
    state.apply(ProgressEvent::Failed { slot: 0, error: "network error".to_string() });
    state.apply(ProgressEvent::Assigned { slot: 1, title: "Episode 2".to_string() });
    state.apply(ProgressEvent::Cancelled { slot: 1 });

    assert_eq!("并发 2 | 总进度 2/4 | 成功 0 | 失败 1 | 取消 1", state.summary_line());
    assert!(matches!(state.slot_state(0).unwrap().status, SlotStatus::Failed(_)));
    assert!(matches!(state.slot_state(1).unwrap().status, SlotStatus::Cancelled));
}
