//! Runtime switches for bisecting performance changes.
//!
//! Set `LUNA_ABLATE` to a comma-separated list of names to restore the previous
//! behaviour of individual optimizations without rebuilding:
//!
//! * `next` - disable the one-argument `next()` call fast path
//! * `quickened` - restore the unconditional `quickened` atomic swap
//! * `zeroarg` - restore the reserved spare slot for zero-argument calls
//! * `classcall` - disable the no-`__init__` class-call fast path
//! * `strmethod` - disable the exact-str method kernels
//! * `strcreate` - stage string creation through a temporary buffer
//! * `split` - disable the single-byte-separator split fast path
//! * `slicefast` - disable the direct str slicing fast path
//! * `join` - disable the single-allocation ASCII join path
//! * `lazydict` - create instance dicts eagerly again
//! * `excctor` - disable the direct builtin-exception constructor
//! * `genclose` - resume the frame with GeneratorExit on close()
//! * `notail` - call the callee recursively instead of via the TailCall trampoline
//! * `stubcall` - return None from an exact-args Python call without running the callee
//! * `rangeint` - allocate a fresh int for every `for i in range(n)` step instead
//!   of folding the step into the loop variable's own object
//! * `exitclone` - clone a frame's return value on every exit instead of only
//!   when a trace or profile observer is waiting for it
//! * `rangeiter` - allocate a fresh `range_iterator` for every outer loop instead
//!   of recycling a husk from the type's freelist
//! * `excfuse` - run an `except` clause's `CHECK_EXC_MATCH` and its
//!   `POP_JUMP_IF_FALSE` as two instructions, and validate every clause target
//!   through the MRO instead of answering an identical class with one compare
//! * `kwfast` - bind a keyword call through `FuncArgs` instead of scattering its
//!   values into the callee's fastlocals slots
//!
//! `LUNA_STUB_BODY=<qualname prefix>` is a second, complementary instrument: the
//! matching functions answer `None` before their first instruction, and
//! `stubcall` combined with it skips the frame entirely. Run a probe with the
//! variable set and unset on one binary to split a call's cost into dispatch,
//! frame entry and the callee's own instructions.

use std::sync::OnceLock;

pub(crate) const NEXT_FAST: u32 = 1;
pub(crate) const QUICKENED: u32 = 2;
/// Ablating this routes the exact-args Python call fast path back through a
/// materialized FrameObject (`prepare_exact_args_frame` + `run_frame`) instead
/// of the frameless `invoke_exact_args_slots`, so the two can be compared
/// inside one binary and one profile.
pub(crate) const FRAMELESS: u32 = 4;
/// Ablating this keeps `CallPyExactArgs` on the recursive route (invoke the
/// callee from the caller's instruction loop) instead of handing the prepared
/// callee frame to the TailCall trampoline, so the two can be compared inside
/// one binary and one profile.
pub(crate) const NO_TAILCALL: u32 = 16384;
/// Measurement only: return `None` from the exact-args invoke without running
/// the callee, which isolates CALL dispatch and argument moves from everything
/// the callee costs. Breaks program semantics, so it is reachable only through
/// an explicit `LUNA_ABLATE=stubcall`.
pub(crate) const STUB_CALL: u32 = 512;
pub(crate) const ZERO_ARG: u32 = 8;
pub(crate) const CLASS_CALL: u32 = 16;
pub(crate) const STR_METHOD: u32 = 32;
pub(crate) const STR_CREATE: u32 = 64;
pub(crate) const SPLIT: u32 = 128;
pub(crate) const SLICE_FAST: u32 = 256;
pub(crate) const JOIN: u32 = 1024;
pub(crate) const LAZY_DICT: u32 = 2048;
pub(crate) const EXC_CTOR: u32 = 4096;
pub(crate) const GEN_CLOSE: u32 = 8192;
/// Ablating this makes a `for i in range(n)` loop allocate a fresh int at every
/// step again, instead of folding the step into the object the previous
/// iteration handed out, so the two can be compared inside one binary.
pub(crate) const RANGE_INT: u32 = 32768;
/// Ablating this clones the frame's return value on every exit, whether or not
/// anyone is watching for a `'return'` trace event, which is what the exit path
/// did before the clone was moved behind the `exit_event_wanted` test.
pub(crate) const EXIT_CLONE: u32 = 65536;
/// Ablating this makes every `iter(range(...))` go to the allocator again
/// instead of reusing a `range_iterator` husk, which is what a nested range loop
/// paid per outer step before the type got a freelist.
pub(crate) const RANGE_ITER: u32 = 131072;
/// Ablating this routes a keyword call back through `FuncArgs` (argument `Vec`,
/// a heap copy of every keyword name and a keyword map) instead of scattering
/// its values straight into the callee's fastlocals slots, which is what such a
/// call did before the shape was recognized.
pub(crate) const KW_FAST: u32 = 524288;
/// Ablating this splits an `except` clause back into `CHECK_EXC_MATCH` +
/// `POP_JUMP_IF_FALSE` and routes every single-class target through the MRO
/// validation, which is what the clause test did before the pair was fused and
/// the identical-class compare was added.
pub(crate) const EXC_FUSE: u32 = 262144;

/// Measurement only: the qualified-name prefix whose function bodies are
/// skipped, so one call splits into "dispatch, argument binding, frame entry
/// and exit" on one side and the callee's own instructions on the other.
///
/// Matching on the qualname instead of the file keeps the probe runnable: the
/// module-level code object of the very same file still executes. Unset, the
/// normal case, it costs one cached load per frame entry.
pub(crate) fn stub_body_fragment() -> Option<&'static str> {
    static FRAGMENT: OnceLock<Option<&'static str>> = OnceLock::new();
    *FRAGMENT.get_or_init(|| {
        std::env::var("LUNA_STUB_BODY")
            .ok()
            .filter(|value| !value.is_empty())
            .map(|value| &*Box::leak(value.into_boxed_str()))
    })
}

/// Whether this frame's body is the instrument's to skip.
///
/// A prefix test rather than a substring search, because the answer is computed
/// on every frame entry: an unset fragment costs one cached load and a set one
/// costs a length compare plus the prefix bytes. Anything that scans the whole
/// qualname would measure itself instead of the callee.
pub(crate) fn body_stubbed(qualname: &str) -> bool {
    stub_body_fragment().is_some_and(|fragment| qualname.starts_with(fragment))
}

/// True when the named optimization is ablated through `LUNA_ABLATE`.
pub(crate) fn ablated(bit: u32) -> bool {
    static MASK: OnceLock<u32> = OnceLock::new();
    let mask = *MASK.get_or_init(|| {
        let mut mask = 0u32;
        if let Some(value) = std::env::var_os("LUNA_ABLATE") {
            for part in value.to_string_lossy().split(',') {
                mask |= match part.trim() {
                    "next" => NEXT_FAST,
                    "quickened" => QUICKENED,
                    "zeroarg" => ZERO_ARG,
                    "classcall" => CLASS_CALL,
                    "strmethod" => STR_METHOD,
                    "strcreate" => STR_CREATE,
                    "split" => SPLIT,
                    "slicefast" => SLICE_FAST,
                    "join" => JOIN,
                    "lazydict" => LAZY_DICT,
                    "excctor" => EXC_CTOR,
                    "genclose" => GEN_CLOSE,
                    "frameless" => FRAMELESS,
                    "notail" => NO_TAILCALL,
                    "stubcall" => STUB_CALL,
                    "rangeint" => RANGE_INT,
                    "exitclone" => EXIT_CLONE,
                    "rangeiter" => RANGE_ITER,
                    "excfuse" => EXC_FUSE,
                    "kwfast" => KW_FAST,
                    _ => 0,
                };
            }
        }
        mask
    });
    mask & bit != 0
}
