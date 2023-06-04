import os
import collections
import sys
import argparse
import configparser
import hashlib
import re
import zlib
import pygit2
from math import ceil

def repo_find(path):
    path = os.path.realpath(path)
    if os.path.isdir(os.path.join(path, ".git")):
        return path
    parent = os.path.realpath(os.path.join(path, ".."))
    if parent == "/":
        raise Exception("No git directory.")
    return repo_find(parent)

def write_blob(path):
    abs_path = path
    if path[0] != "/":
        cwd = os.getcwd()
        abs_path = os.path.join(cwd, path)
    with open(path, "rb") as f:
        data = f.read()
    result = b"blob " + str(len(data)).encode() + b"\0" + data
    
    if True:
         print(data)
    # Compute hash
    sha = hashlib.sha1(result).hexdigest()

    object_path = repo_find(abs_path) + "/.git/objects/" + sha[0:2] + "/" + sha[2:]
    print(object_path)
    dir = os.path.dirname(object_path)
    print(dir)
    if not os.path.isdir(dir):
        os.makedirs(dir)
    with open(object_path, 'wb') as f:
        # Compress and write
        f.write(zlib.compress(result))
    return sha

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers()

args = parser.parse_args()
if hasattr(args, 'handler'):
    args.handler(args)
