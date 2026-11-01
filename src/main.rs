use rustpython::{InterpreterBuilder, InterpreterBuilderExt};
#[cfg(feature = "alloc-stats")]
use std::alloc::{GlobalAlloc, Layout};

// mimalloc global allocator: Python workloads are allocation-heavy
// (every object is a heap allocation); mimalloc's per-thread arenas and
// size-class bins outperform the Windows HeapAlloc default by 10-30%
// on allocation-dense benchmarks.
#[cfg(not(feature = "alloc-stats"))]
#[global_allocator]
static GLOBAL_ALLOCATOR: mimalloc::MiMalloc = mimalloc::MiMalloc;

// The same allocator with counters in front of it, so a measurement build can
// answer "how many blocks does this operation allocate" without a profiler.
// Only `--features alloc-stats` compiles it; a benchmark build has no wrapper.
#[cfg(feature = "alloc-stats")]
#[global_allocator]
static GLOBAL_ALLOCATOR: Counted = Counted;

#[cfg(feature = "alloc-stats")]
struct Counted;

#[cfg(feature = "alloc-stats")]
unsafe impl GlobalAlloc for Counted {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        rustpython_vm::alloc_stats::record_alloc(&layout);
        unsafe { mimalloc::MiMalloc.alloc(layout) }
    }

    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        rustpython_vm::alloc_stats::record_free(&layout);
        unsafe { mimalloc::MiMalloc.dealloc(ptr, layout) }
    }

    unsafe fn realloc(&self, ptr: *mut u8, layout: Layout, new_size: usize) -> *mut u8 {
        if let Ok(new_layout) = Layout::from_size_align(new_size, layout.align()) {
            rustpython_vm::alloc_stats::record_alloc(&new_layout);
            rustpython_vm::alloc_stats::record_free(&layout);
        }
        unsafe { mimalloc::MiMalloc.realloc(ptr, layout, new_size) }
    }
}

pub fn main() -> std::process::ExitCode {
    let mut config = InterpreterBuilder::new();
    #[cfg(feature = "stdlib")]
    {
        config = config.init_stdlib();
    }
    rustpython::run(config)
}
