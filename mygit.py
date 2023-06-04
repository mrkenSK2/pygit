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

def update_index(path):
    abspath = os.path.abspath(path)
    index_path = repo_find(os.getcwd()) + "/.git/index"
    if os.path.exists(index_path):
        with open(index_path, "rb") as f:
            data = f.read()
    else:
        write_index(abspath)
        return
    
    paths = []
    entry_num = struct.unpack(">i", data[8:12])[0]
    start = 12
    for _ in range(entry_num):
        filename_size = struct.unpack(">h", data[start + 60: start + 62])[0]
        filename = data[start + 62: start + 62 + filename_size].decode()
        padding = cal_padding(filename_size)
        paths.append(filename)
        start += 62 + filename_size + padding
    
    if path not in paths:
        paths.append(path)
    paths.sort()
    write_index(paths)

def write_tree():
    cwd = os.getcwd()
    index_path = repo_find(cwd) + "/.git/index"
    with open(index_path, "rb") as f:
        data = f.read()
    entry_num = struct.unpack(">i", data[8:12])[0]
    entries = b""
    start = 12
    for _ in range(entry_num):
        mode = struct.unpack(">i", data[start + 24: start + 28])[0]
        hash = data[start + 40: start + 60]
        filename_size = struct.unpack(">h", data[start + 60: start + 62])[0]
        filename = data[start + 62: start + 62 + filename_size]
        padding = cal_padding(filename_size)
        
        entries += format(mode, "06o").encode() +  b" " + filename + b"\0" + hash
        
        start += 62 + filename_size + padding

    tree_object = b"tree " + str(len(entries)).encode() + b"\0" + entries

    # Compute hash
    sha = hashlib.sha1(tree_object).hexdigest()

    object_path = repo_find(cwd) + "/.git/objects/" + sha[0:2] + "/" + sha[2:]
    dir = os.path.dirname(object_path)

    if not os.path.isdir(dir):
        os.makedirs(dir)
    with open(object_path, 'wb') as f:
        # Compress and write
        f.write(zlib.compress(tree_object))
    return sha

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers()

args = parser.parse_args()
if hasattr(args, 'handler'):
    args.handler(args)
