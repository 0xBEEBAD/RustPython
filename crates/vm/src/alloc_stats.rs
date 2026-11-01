//! Feature-gated allocation counters, for deciding where allocation volume is
//! before spending a refactor on it.
//!
//! Built with `--features alloc-stats`, which wraps the mimalloc global
//! allocator in `src/main.rs` and publishes `sys._alloc_stats()` /
//! `sys._reset_alloc_stats()`. A default build contains none of this code, so
//! no measurement cost can leak into a benchmark binary.

use std::alloc::Layout;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};

/// Size-class resolution: `counts[i]` counts requests rounding up to
/// `i * BUCKET_GRAIN` bytes, and the final entry is everything above
/// `BUCKETS * BUCKET_GRAIN`.
pub const BUCKET_GRAIN: usize = 16;
pub const BUCKETS: usize = 64;

static ALLOCS: AtomicU64 = AtomicU64::new(0);
static FREES: AtomicU64 = AtomicU64::new(0);
static BYTES: AtomicU64 = AtomicU64::new(0);
static SIZES: [AtomicUsize; BUCKETS + 1] = [const { AtomicUsize::new(0) }; BUCKETS + 1];

#[inline]
pub fn record_alloc(layout: &Layout) {
    ALLOCS.fetch_add(1, Ordering::Relaxed);
    BYTES.fetch_add(layout.size() as u64, Ordering::Relaxed);
    SIZES[bucket(layout.size())].fetch_add(1, Ordering::Relaxed);
}

#[inline]
pub fn record_free(_layout: &Layout) {
    FREES.fetch_add(1, Ordering::Relaxed);
}

fn bucket(size: usize) -> usize {
    size.div_ceil(BUCKET_GRAIN).min(BUCKETS)
}

pub struct Stats {
    pub allocs: u64,
    pub frees: u64,
    pub bytes: u64,
    pub counts: Vec<usize>,
}

impl Stats {
    pub fn snapshot() -> Self {
        Self {
            allocs: ALLOCS.load(Ordering::Relaxed),
            frees: FREES.load(Ordering::Relaxed),
            bytes: BYTES.load(Ordering::Relaxed),
            counts: SIZES.iter().map(|c| c.load(Ordering::Relaxed)).collect(),
        }
    }

    /// Returns what was counted before the reset, so one call can both read
    /// and arm the next measurement window.
    pub fn reset() -> Self {
        let before = Self::snapshot();
        ALLOCS.store(0, Ordering::Relaxed);
        FREES.store(0, Ordering::Relaxed);
        BYTES.store(0, Ordering::Relaxed);
        for c in SIZES.iter() {
            c.store(0, Ordering::Relaxed);
        }
        before
    }
}
