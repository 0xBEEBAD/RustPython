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

use std::sync::OnceLock;

pub(crate) const NEXT_FAST: u16 = 1;
pub(crate) const QUICKENED: u16 = 2;
/// Ablating this routes the exact-args Python call fast path back through a
/// materialized FrameObject (`prepare_exact_args_frame` + `run_frame`) instead
/// of the frameless `invoke_exact_args_slots`, so the two can be compared
/// inside one binary and one profile.
pub(crate) const FRAMELESS: u16 = 4;
/// Ablating this keeps `CallPyExactArgs` on the recursive route (invoke the
/// callee from the caller's instruction loop) instead of handing the prepared
/// callee frame to the TailCall trampoline, so the two can be compared inside
/// one binary and one profile.
pub(crate) const NO_TAILCALL: u16 = 16384;
/// Measurement only: return `None` from the exact-args invoke without running
/// the callee, which isolates CALL dispatch and argument moves from everything
/// the callee costs. Breaks program semantics, so it is reachable only through
/// an explicit `LUNA_ABLATE=stubcall`.
pub(crate) const STUB_CALL: u16 = 512;
pub(crate) const ZERO_ARG: u16 = 8;
pub(crate) const CLASS_CALL: u16 = 16;
pub(crate) const STR_METHOD: u16 = 32;
pub(crate) const STR_CREATE: u16 = 64;
pub(crate) const SPLIT: u16 = 128;
pub(crate) const SLICE_FAST: u16 = 256;
pub(crate) const JOIN: u16 = 1024;
pub(crate) const LAZY_DICT: u16 = 2048;
pub(crate) const EXC_CTOR: u16 = 4096;
pub(crate) const GEN_CLOSE: u16 = 8192;

/// True when the named optimization is ablated through `LUNA_ABLATE`.
pub(crate) fn ablated(bit: u16) -> bool {
    static MASK: OnceLock<u16> = OnceLock::new();
    let mask = *MASK.get_or_init(|| {
        let mut mask = 0u16;
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
                    _ => 0,
                };
            }
        }
        mask
    });
    mask & bit != 0
}
