"""gpu/vk/par_scale.h, the small-PC rule: the parallel replay's workers and the descriptor prefetch, sized from the logical
processors the process may run on, when the switches say nothing. The rule is compiled alone here and its mapping checked, so a
4-core machine can never be given workers it does not have (that is what the rule exists to avoid), and a 12-core one always
gets three, without anyone setting a variable.

Run with: python -I tests/test_parallel_workers.py [--cxx g++]
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VK = ROOT / "gpu" / "vk"

MAIN = r'''
#include <cstdio>
#include "par_scale.h"
int main() {
    const unsigned cpus[] = {0, 1, 2, 4, 5, 6, 8, 10, 12, 16, 24, 32, 64};
    for (unsigned c : cpus)
        std::printf("%u %d %d\n", c, mkwvk::par::workers(c), mkwvk::par::prefetch(c) ? 1 : 0);
    return 0;
}
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cxx", default="g++")
    a = p.parse_args()
    # (the rule as it is: the checks below are the intended mapping, not a restatement of the implementation)
    want = {
        0: (0, 0), 1: (0, 0), 2: (0, 0), 4: (0, 0), 5: (0, 0),
        6: (1, 1), 8: (2, 1), 10: (2, 1), 12: (3, 1), 16: (4, 1),
        24: (4, 1), 32: (4, 1), 64: (4, 1),
    }
    with tempfile.TemporaryDirectory(prefix="par-scale-") as tmp:
        cpp = Path(tmp) / "fixture.cpp"
        exe = Path(tmp) / "fixture"
        cpp.write_text(MAIN, encoding="utf-8")
        subprocess.run([a.cxx, "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror", "-I", str(VK), str(cpp), "-o", str(exe)],
                       check=True)
        out = subprocess.run([str(exe)], check=True, capture_output=True, text=True).stdout
    seen = {}
    for line in out.splitlines():
        c, w, pf = line.split()
        seen[int(c)] = (int(w), int(pf))
    for cpus, expect in want.items():
        got = seen.get(cpus)
        if got != expect:
            raise SystemExit("FAIL: %u logical processors -> %r workers/prefetch, wanted %r" % (cpus, got, expect))
    # (monotonic: more processors never mean fewer workers, and never more than four)
    last = 0
    for cpus in sorted(seen):
        w = seen[cpus][0]
        if w < last or w > 4:
            raise SystemExit("FAIL: %u processors -> %d workers (not monotonic, or over four)" % (cpus, w))
        last = w
    print("PASS: the rule: 4 cores -> none (the game keeps them), 6 -> 1, 8 -> 2, 12 -> 3, 16 and more -> 4; prefetch from 6")


if __name__ == "__main__":
    main()
