from pathlib import Path
import subprocess as sp
import os

os._posix_spawn = True

tmp = "/tmp/out"
sp.run(["touch", tmp])
sp.run(["chmod", "+x", tmp])


def test(f):
    result = sp.run(["./run", f], capture_output=True)
    if result.returncode != 0:
        return False
    with open(f, "r") as file:
        expected = str(eval(file.readline()[1:-2]))

    out = result.stdout.decode("utf-8").replace("\x00", "")
    return out == expected


directory = Path("tests")
for f in directory.iterdir():
    if f.is_file():
        print(f"{str(f.name):20}", end=" ")
        print("\033[42mpassed" if test(f) else "\033[41mfailed", "\033[0m", sep="")
