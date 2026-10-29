//! Runtime switches for bisecting performance changes.
//!
//! Set `LUNA_ABLATE` to a comma-separated list of names to restore the previous
//! behaviour of individual optimizations without rebuilding:
//!
//! * `next` - disable the one-argument `next()` call fast path
//! * `quickened` - restore the unconditional `quickened` atomic swap
//! * `zeroarg` - restore the reserved spare slot for zero-argument calls

use std::sync::OnceLock;

pub(crate) const NEXT_FAST: u8 = 1;
pub(crate) const QUICKENED: u8 = 2;
pub(crate) const ZERO_ARG: u8 = 8;

/// True when the named optimization is ablated through `LUNA_ABLATE`.
pub(crate) fn ablated(bit: u8) -> bool {
    static MASK: OnceLock<u8> = OnceLock::new();
    let mask = *MASK.get_or_init(|| {
        let mut mask = 0u8;
        if let Some(value) = std::env::var_os("LUNA_ABLATE") {
            for part in value.to_string_lossy().split(',') {
                mask |= match part.trim() {
                    "next" => NEXT_FAST,
                    "quickened" => QUICKENED,
                    "zeroarg" => ZERO_ARG,
                    _ => 0,
                };
            }
        }
        mask
    });
    mask & bit != 0
}
