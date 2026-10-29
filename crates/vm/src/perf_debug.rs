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

use std::sync::OnceLock;

pub(crate) const NEXT_FAST: u16 = 1;
pub(crate) const QUICKENED: u16 = 2;
pub(crate) const ZERO_ARG: u16 = 8;
pub(crate) const CLASS_CALL: u16 = 16;
pub(crate) const STR_METHOD: u16 = 32;
pub(crate) const STR_CREATE: u16 = 64;
pub(crate) const SPLIT: u16 = 128;
pub(crate) const SLICE_FAST: u16 = 256;

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
                    _ => 0,
                };
            }
        }
        mask
    });
    mask & bit != 0
}
