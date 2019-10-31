import os
import tempfile

with tempfile.TemporaryDirectory() as scratch:
    os.chdir(scratch)
    print(os.getcwd())
    with open("test.txt", "wt") as fp:
        fp.write("hello world")
    print(" ".join(os.listdir(".")))
