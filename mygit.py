import os
import collections
import sys
import argparse
import configparser
import hashlib
import re
import zlib
import struct
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
 
    # Compute hash
    sha = hashlib.sha1(result).hexdigest()

    object_path = repo_find(abs_path) + "/.git/objects/" + sha[0:2] + "/" + sha[2:]
    dir = os.path.dirname(object_path)

    if not os.path.isdir(dir):
        os.makedirs(dir)
    with open(object_path, 'wb') as f:
        # Compress and write
        f.write(zlib.compress(result))
    return sha


def create_entry(filename):
    path = os.path.abspath(filename)
    metadata = os.stat(path)


def create_entry(filename):
    path = os.path.abspath(filename)
    metadata = os.stat(path)

    ctime      = int(metadata.st_ctime)
    ctime_nsec = int(metadata.st_ctime_ns % (10 ** 9))
    mtime      = int(metadata.st_mtime)
    mtime_nsec = int(metadata.st_mtime_ns % (10 ** 9))
    dev        = int(metadata.st_dev)
    ino        = int(metadata.st_ino)
    mode       = int(metadata.st_mode)
    uid        = int(metadata.st_uid)
    gid        = int(metadata.st_gid)
    filesize   = int(metadata.st_size)

    with open(path, "rb") as f:
        data = f.read()

    blob = b"blob " + str(len(data)).encode() + b"\0" + data
    blob_hash = hashlib.sha1(blob).digest()

    filename_size = len(filename)

    padding_size = cal_padding(filename_size)
    padding = b'\0' * padding_size

    entry_meta = (
        ctime.to_bytes(4) +
        ctime_nsec.to_bytes(4) +
        mtime.to_bytes(4) +
        mtime_nsec.to_bytes(4) +
        dev.to_bytes(4) +
        ino.to_bytes(4) +
        mode.to_bytes(4) +
        uid.to_bytes(4) +
        gid.to_bytes(4) +
        filesize.to_bytes(4)
    )

    filemeta_data = (
        entry_meta +
        blob_hash +
        filename_size.to_bytes(2) +
        filename.encode() +
        padding
    )

    return filemeta_data

def cal_padding(size):
    # before filename 62 bytes
    return 8 - (size + 6) % 8

def write_index(filenames):
    content = b""
    index_header = b"DIRC"
    index_version = 2
    entry_num = len(filenames)

    for filename in filenames:
        entry = create_entry(filename)
        content += entry
    
    index_path = repo_find(os.getcwd()) + "/.git/index"
    with open(index_path, 'wb') as f:
        f.write(index_header + index_version.to_bytes(4) + entry_num.to_bytes(4) + content)
    return

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers()

args = parser.parse_args()
if hasattr(args, 'handler'):
    args.handler(args)
