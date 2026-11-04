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
//! * `defbind` - bind a call that needs defaults through `FuncArgs` instead of
//!   writing the given values and the covering defaults into fastlocals
//! * `armguards` - skip the exact-args call kernel's eligibility checks
//!   (datastack space, recursion depth, tail-call shape); measurement-only, the
//!   checks are what keep a deep or wide call from overrunning the frame
//! * `armstage` - consume the caller's argument slots and answer `None` without
//!   building the callee frame, to price the staging loop and kernel entry; needs
//!   `LUNA_STUB_BODY` to name the functions it may stub, like `stubcall` does
//! * `argsslack` - size a call's drained argument vector by `collect()`'s growth
//!   steps instead of by the exact argument count
//! * `microinline` - build the callee's frame for every exact-args Python call,
//!   instead of answering a call whose body is one arithmetic expression over its
//!   own parameters from the caller's argument slots
//! * `mdstub` - measurement only: answer `None` from the specialized no-argument
//!   method-descriptor call without running the callee, which prices the dispatch
//!   arm - guards, argument vector, call context, stack moves - apart from the
//!   native function it calls; `LUNA_STUB_MD=isascii,split` names the methods it
//!   may stub, because startup needs the others to really run
//! * `mdctx` - run that same callee without installing the call context, which
//!   prices the two thread-local writes and two restores it costs every such call
//! * `mdarm` - consume the descriptor call's slots and answer `None` without
//!   building the argument vector; read against `mdstub`, the two price the
//!   owned-`Vec` packing separately from everything the callee does
//! * `encfast` - send every `str.encode()` through the codec registry again, even
//!   the utf-8/strict spellings whose answer is the string's own bytes
//! * `splreuse` - make a split that found no separator allocate its single piece
//!   again instead of handing back the receiver. That prices one object allocation
//!   plus its free inside one binary; `bench/labs/test_split_reuse.py` pins which
//!   shapes CPython reuses, and fails while this bit is set.
//!
//! `LUNA_STUB_BODY=<qualname prefix>` is a second, complementary instrument: the
//! matching functions answer `None` before their first instruction, and
//! `stubcall` combined with it skips the frame entirely. Run a probe with the
//! variable set and unset on one binary to split a call's cost into dispatch,
//! frame entry and the callee's own instructions.

use std::sync::OnceLock;

pub(crate) const NEXT_FAST: u64 = 1;
pub(crate) const QUICKENED: u64 = 2;
/// Ablating this routes the exact-args Python call fast path back through a
/// materialized FrameObject (`prepare_exact_args_frame` + `run_frame`) instead
/// of the frameless `invoke_exact_args_slots`, so the two can be compared
/// inside one binary and one profile.
pub(crate) const FRAMELESS: u64 = 4;
/// Ablating this keeps `CallPyExactArgs` on the recursive route (invoke the
/// callee from the caller's instruction loop) instead of handing the prepared
/// callee frame to the TailCall trampoline, so the two can be compared inside
/// one binary and one profile.
pub(crate) const NO_TAILCALL: u64 = 16384;
/// Measurement only: return `None` from the exact-args invoke without running
/// the callee, which isolates CALL dispatch and argument moves from everything
/// the callee costs. Breaks program semantics, so it is reachable only through
/// an explicit `LUNA_ABLATE=stubcall`.
pub(crate) const STUB_CALL: u64 = 512;
pub(crate) const ZERO_ARG: u64 = 8;
pub(crate) const CLASS_CALL: u64 = 16;
pub(crate) const STR_METHOD: u64 = 32;
pub(crate) const STR_CREATE: u64 = 64;
pub(crate) const SPLIT: u64 = 128;
pub(crate) const SLICE_FAST: u64 = 256;
pub(crate) const JOIN: u64 = 1024;
pub(crate) const LAZY_DICT: u64 = 2048;
pub(crate) const EXC_CTOR: u64 = 4096;
pub(crate) const GEN_CLOSE: u64 = 8192;
/// Ablating this makes a `for i in range(n)` loop allocate a fresh int at every
/// step again, instead of folding the step into the object the previous
/// iteration handed out, so the two can be compared inside one binary.
pub(crate) const RANGE_INT: u64 = 32768;
/// Ablating this clones the frame's return value on every exit, whether or not
/// anyone is watching for a `'return'` trace event, which is what the exit path
/// did before the clone was moved behind the `exit_event_wanted` test.
pub(crate) const EXIT_CLONE: u64 = 65536;
/// Ablating this makes every `iter(range(...))` go to the allocator again
/// instead of reusing a `range_iterator` husk, which is what a nested range loop
/// paid per outer step before the type got a freelist.
pub(crate) const RANGE_ITER: u64 = 131072;
/// Measurement only: build the callee's frame and bind its arguments, then
/// return without entering it. Together with `stubcall` (no frame at all) and
/// `LUNA_STUB_BODY` (frame entered, body skipped) the three levels split a
/// call into frame construction, frame enter/exit and the body's instructions.
/// Reachable only while `LUNA_STUB_BODY` names the functions to spare, so the
/// interpreter still boots.
pub(crate) const NO_ENTER: u64 = 1048576;
/// Ablating this routes a keyword call back through `FuncArgs` (argument `Vec`,
/// a heap copy of every keyword name and a keyword map) instead of scattering
/// its values straight into the callee's fastlocals slots, which is what such a
/// call did before the shape was recognized.
pub(crate) const KW_FAST: u64 = 524288;
/// Ablating this binds a call that leaves parameters to their `__defaults__`
/// through `FuncArgs` and the generic filler instead of writing the given
/// values and the covering defaults straight into fastlocals.
pub(crate) const DEF_BIND: u64 = 2097152;
/// Ablating this splits an `except` clause back into `CHECK_EXC_MATCH` +
/// `POP_JUMP_IF_FALSE` and routes every single-class target through the MRO
/// validation, which is what the clause test did before the pair was fused and
/// the identical-class compare was added.
pub(crate) const EXC_FUSE: u64 = 262144;
/// Measurement only: skip the eligibility checks the exact-args call kernel runs
/// before it stages the arguments (datastack space, recursion depth, tail-call
/// shape). Together with `armstage` this splits that kernel into guards, staging
/// and the callee entry. Never enable while running real code: the datastack and
/// depth checks are what keep a deep or wide call from overrunning the frame.
pub(crate) const ARM_GUARDS: u64 = 4194304;
/// Measurement only: consume the caller's argument slots and answer `None`
/// without building the callee's frame, so a probe can read the cost of the
/// staging loop and the kernel entry apart from everything below it. Like
/// `stubcall` it applies only to the functions `LUNA_STUB_BODY` names, since a
/// callee that never runs cannot produce the objects the interpreter boots on.
pub(crate) const ARM_STAGE: u64 = 8388608;
/// Drain call arguments out of the frame stack with `collect()` again, which
/// cannot see the iterator's length and so leaves capacity slack that a
/// downstream tuple buffer pays a second allocation (and a free) to shrink.
pub(crate) const ARGS_SLACK: u64 = 16777216;
/// Answer an exact-args Python call whose body is a single arithmetic expression
/// over its own parameters from the caller's argument slots, instead of building
/// the callee's frame.
pub(crate) const MICRO_INLINE: u64 = 33554432;
/// Read a small `BigInt`'s value through the generic `ToPrimitive` conversion
/// instead of the single-limb test that CPython's compact-long check mirrors.
pub(crate) const INT_COMPACT: u64 = 67108864;
/// Measurement only: skip the `__context__` chaining a raise performs when it
/// contextualizes an exception, so the cost of reading the in-flight exception
/// and writing the link can be read off one binary. Never enable while running
/// real code: `raise` inside an `except` clause would lose its context.
pub(crate) const EXC_CTX: u64 = 134217728;
/// Measurement only: skip the work a frame does on its way out when an exception
/// escapes it - the `PY_UNWIND` monitoring test and the `lasti` restore that
/// keeps `frame.f_lineno` equal to `tb_lineno` - so the cost of that tail can be
/// separated from the traceback entry and the block unwinding around it.
pub(crate) const EXC_UNWINDTAIL: u64 = 268435456;
/// Measurement only: leave a constructed exception's `args` empty instead of
/// boxing the argument tuple, which prices the tuple allocation and its GC
/// tracking that every `ValueError(x)` pays. Never enable while running real
/// code: `args` is what `str(exc)`, pickling and re-raising read.
pub(crate) const EXC_ARGS: u64 = 536870912;
/// Measurement only: add no traceback entry when an exception passes through a
/// frame, which prices both the entry object and the frame object it holds -
/// the frame object is what turns an unmaterialized frame into one that has to
/// be cleared on the way out. Never enable while running real code: tracebacks
/// and `sys.exc_info()` line numbers depend on it.
pub(crate) const EXC_TB: u64 = 1073741824;
/// Measurement only: answer `None` from the specialized no-argument
/// method-descriptor call without running the callee, which prices the dispatch
/// arm itself - guards, argument vector, call context, stack moves - against the
/// ~100 ns a builtin method call costs over a builtin function call. Never
/// enable while running real code: every such method silently returns `None`.
pub(crate) const MD_STUB: u64 = 2147483648;
/// Measurement only: call the no-argument method descriptor's native function
/// without installing the call context, which prices the pair of thread-local
/// writes and restores. Safe as a measurement because the arm's own guards
/// (exact class, exactly one argument, no keywords) already rule out every
/// binding error that reads the context; never enable in a real program, where a
/// nested call would report the wrong name.
pub(crate) const MD_CTX: u64 = 4294967296;
/// Measurement only: consume the descriptor call's slots and answer `None`
/// without building the argument vector at all. Read against `mdstub`, which
/// builds the vector and the `FuncArgs` but skips the callee, the difference is
/// exactly what packing the arguments into an owned `Vec` costs.
pub(crate) const MD_ARM: u64 = 8589934592;
/// Ablating this routes every `str.encode` back through the codec registry, so
/// the utf-8/strict fast path and the round trip it skips can be compared inside
/// one binary.
pub(crate) const ENC_FASTPATH: u64 = 17179869184;
/// Ablating this sends `bytes.decode()` and `bytearray.decode()` back through the
/// codec registry, so the utf-8/strict fast path can be priced against the round
/// trip it skips inside one binary.
pub(crate) const DEC_FASTPATH: u64 = 34359738368;
/// Ablating this makes `str.split`/`bytes.split` allocate a fresh piece for the
/// single element that CPython hands back as the receiver itself (see
/// `Objects/stringlib/split.h`, `count == 0 && STRINGLIB_CHECK_EXACT`), which
/// prices one object allocation plus its free inside one binary. It also
/// reproduces the identity difference the reuse rule fixes, so the parity probe
/// `bench/labs/test_split_reuse.py` fails while this bit is set.
pub(crate) const SPLIT_REUSE: u64 = 68719476736;

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

/// `LUNA_STUB_MD=<name,..>`: the method-descriptor names `mdstub` may stub.
///
/// The filter exists because the stub is not a no-op for the interpreter itself -
/// startup calls self-only builtin methods whose results it depends on, so an
/// unfiltered stub dies with "essential initialization failed". The list is
/// parsed once into `&'static str` slices, so an unset variable costs one cached
/// load and a set one a short linear compare over the names.
pub(crate) fn stub_md_name(name: &str) -> bool {
    static NAMES: OnceLock<Vec<&'static str>> = OnceLock::new();
    let names = NAMES.get_or_init(|| {
        let value = std::env::var("LUNA_STUB_MD").unwrap_or_default();
        let value: &'static str = Box::leak(value.into_boxed_str());
        value
            .split(',')
            .map(str::trim)
            .filter(|name| !name.is_empty())
            .collect()
    });
    names.iter().any(|stubbed| *stubbed == name)
}

/// True when the named optimization is ablated through `LUNA_ABLATE`.
pub(crate) fn ablated(bit: u64) -> bool {
    static MASK: OnceLock<u64> = OnceLock::new();
    let mask = *MASK.get_or_init(|| {
        let mut mask = 0u64;
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
                    "noenter" => NO_ENTER,
                    "defbind" => DEF_BIND,
                    "armguards" => ARM_GUARDS,
                    "armstage" => ARM_STAGE,
                    "argsslack" => ARGS_SLACK,
                    "microinline" => MICRO_INLINE,
                    "intcompact" => INT_COMPACT,
                    "excctx" => EXC_CTX,
                    "excunwindtail" => EXC_UNWINDTAIL,
                    "excargs" => EXC_ARGS,
                    "exctb" => EXC_TB,
                    "mdstub" => MD_STUB,
                    "mdctx" => MD_CTX,
                    "mdarm" => MD_ARM,
                    "encfast" => ENC_FASTPATH,
                    "decfast" => DEC_FASTPATH,
                    "splreuse" => SPLIT_REUSE,

                    // A bare number is accepted as the bit mask itself, so a
                    // probe can address a bit that has no alias here. Unknown
                    // text used to read as "no bits at all", which made an
                    // A/B of a freshly added gate look exactly like a null
                    // result instead of a missing alias - hence the warning.
                    other => match other.parse::<u64>() {
                        Ok(mask) => mask,
                        Err(_) => {
                            eprintln!("LUNA_ABLATE: unknown ablation {other:?}, ignored");
                            0
                        }
                    },
                };
            }
        }
        mask
    });
    mask & bit != 0
}
