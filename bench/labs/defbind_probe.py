"""One call per shape, so the TEMP-PROBE eprintln lines identify the route."""


def probe_exact(a, b):
    pass


def probe_default(a, b=1):
    pass


def probe_all_default(a=1, b=2):
    pass


def probe_wide(a, b=1, c=2, d=3):
    pass


probe_exact(1, 2)
probe_default(1)
probe_default(1, 2)
probe_all_default()
probe_wide(1)
print("probe calls done")
