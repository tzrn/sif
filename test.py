from pathlib import Path
import subprocess as sp
import os

os._posix_spawn = True


def test(f):
    result = sp.run(["python3", "main.py", f], capture_output=True)
    with open(f, "r") as file:
        expected = eval(file.readline()[1:-2])
    if result.stderr:
        return False

    with open("/tmp/test.sif", "w") as file:
        file.write(result.stdout.decode("utf-8"))
    result = sp.run(["fasm", "/tmp/test.sif", "/tmp/out"], capture_output=True)
    if result.stderr:
        return False
    return True


directory = Path("tests")
for f in directory.iterdir():
    if f.is_file():
        print(str(f.name), "passed" if test(f) else "failed")
