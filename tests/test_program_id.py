"""make_game --check reads the program (the title, main.npdm's ACID) and not only the build: the OcaDim setup refuses
another game before it compiles or creates anything. Authored bytes only: no game, no compiler, no network.

    python -I -B tests/test_program_id.py
"""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import struct
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("make_game_under_test", ROOT / "nx2" / "make_game.py")
make_game = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make_game)

GOOD = 0x0400486024DEC000
OTHER = 0x0100000000010000


def npdm(program_id):
    """The META/ACI0 shape main.npdm has (nx2/dump.py reads the same offsets)"""
    blob = bytearray(0x100)
    blob[:4] = b"META"
    aoff = 0x80
    struct.pack_into("<II", blob, 0x70, aoff, 0x40)
    blob[aoff:aoff + 4] = b"ACI0"
    struct.pack_into("<Q", blob, aoff + 0x10, program_id)
    return bytes(blob)


def main_module(build_id=make_game.BUILD_ID):
    head = bytearray(0x60)
    head[:4] = b"NSO0"
    head[0x40:0x44] = bytes.fromhex(build_id)
    return bytes(head) + b"authored module"


def check(exefs):
    """make_game.check with the compiler preflight and the nup extraction out of the way: what it says, and its code"""
    make_game.PREPARE = True
    make_game.check_windows_sdk = lambda work=None: None
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = make_game.check(types.SimpleNamespace(nup=None, exefs=str(exefs)), str(exefs))
    return code, out.getvalue().splitlines()


def run():
    with tempfile.TemporaryDirectory(prefix="ocadim-program-id-") as d:
        exefs = Path(d) / "exefs"
        exefs.mkdir()
        (exefs / "main").write_bytes(main_module())

        (exefs / "main.npdm").write_bytes(npdm(GOOD))
        assert make_game.program_id(str(exefs)) == GOOD
        code, lines = check(exefs)
        assert code == 0, lines
        assert lines == ["check ok This is the version Longshot supports (program 0400486024DEC000, build e0f3ccfa)."], lines

        (exefs / "main.npdm").write_bytes(npdm(OTHER))
        assert make_game.program_id(str(exefs)) == OTHER
        code, lines = check(exefs)
        assert code == 1, lines
        assert lines == ["check bad This is program 0100000000010000. Longshot supports program 0400486024DEC000."], lines

        (exefs / "main.npdm").write_bytes(b"not an npdm at all")
        assert make_game.program_id(str(exefs)) is None
        code, lines = check(exefs)
        assert code == 1, lines
        assert lines == ["check bad This copy has no program id (main.npdm). Longshot supports program 0400486024DEC000."], lines

        (exefs / "main.npdm").unlink()
        code, lines = check(exefs)
        assert code == 1, lines
        assert lines == ["check bad This copy has no program id (main.npdm). Longshot supports program 0400486024DEC000."], lines

        (exefs / "main.npdm").write_bytes(npdm(GOOD))
        (exefs / "main").write_bytes(main_module("01234567"))
        code, lines = check(exefs)
        assert code == 1, lines
        assert lines == ["check bad This is build 01234567. Longshot supports build e0f3ccfa."], lines

        (exefs / "main").unlink()
        code, lines = check(exefs)
        assert code == 1, lines
        assert lines == ["check bad This copy has no main module."], lines

    print("PASS: the program and the build are both read, and another game is refused in plain words")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    run()
