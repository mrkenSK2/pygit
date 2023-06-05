import os
import argparse
import configparser
import hashlib
import zlib
import struct
import datetime

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
    index_path = repo_find(os.getcwd()) + "/.git/index"
    if os.path.exists(index_path):
        with open(index_path, "rb") as f:
            data = f.read()
    else:
        path = [path]
        write_index(path)
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

def commit_tree(tree_hash, message):
    conf_path = os.path.join(repo_find(os.getcwd()), ".git/config") 
    config = configparser.ConfigParser()
    config.read(conf_path)
    _author = config.get("user", "name")
    email = config.get("user", "email")
    author = "author {} <{}> {} + 0900".format(_author, email, datetime.datetime.now())
    committer = "committer " + author[7:]
    
    commit_content = b""
    head_commit = read_head()

    if head_commit is not None:
        if tree_hash != cat_commit_tree(head_commit):
            parent = "parent {}".format(head_commit)
            content = "tree {}\n{}\n{}\n{}\n\n{}\n".format(tree_hash, parent, author, committer, message)
        else:
            print("Nothing to commit")
            return None
    else:
        content = "tree {}\n{}\n{}\n\n{}\n".format(tree_hash, author, committer, message)
    commit_content = b"commit " + str(len(content)).encode() + b"\0" + content.encode()

    # Compress the content
    compressed = zlib.compress(commit_content)

    # Calculate the hash
    sha = hashlib.sha1(commit_content).hexdigest()
    object_path = repo_find(os.getcwd()) + "/.git/objects/" + sha[0:2] + "/" + sha[2:]
    dir = os.path.dirname(object_path)

    if not os.path.isdir(dir):
        os.makedirs(dir)

    with open(object_path, "wb") as f:
        f.write(compressed)

    return sha

def read_head():
    HEAD_path = os.path.join(repo_find(os.getcwd()), ".git/HEAD")
    if not os.path.exists(HEAD_path):
        raise Exception("no HEAD")
    with open(HEAD_path, "r") as file:
        ref = file.read().strip()
    
    prefix_path = ref.split(" ")
    
    # ref is branch
    if "/" in prefix_path[1]:
        branch_path = os.path.join(os.getcwd(), ".git", prefix_path[1].replace("\n", ""))
        if not os.path.exists(branch_path):
            return None
        with open(branch_path, "r") as f:
            hash = f.read().strip()
            return hash.replace("\n", "")
    
    return prefix_path[1].replace("\n", "")

def cat_commit_tree(commit_hash):
    dir_path = commit_hash[0:2]
    file_path = commit_hash[2:]
    object_path = os.path.join(os.getcwd(), ".git/objects", dir_path, file_path)

    if not os.path.exists(object_path):
        raise Exception("commit doesn't exist")
    with open(object_path, "rb") as f:
        data = f.read()
    r_data = zlib.decompress(data)
    tree_start = r_data.find(b"\0")
    tree_hash = r_data[tree_start + 6 : tree_start + 46]
    return tree_hash.decode()

def update_ref(commit_hash):
    path = os.path.join(os.getcwd(), ".git/HEAD")
    with open(path, "r+") as f:
        ref = f.read().strip()

    prefix_path = ref.split(' ')

    if "/" in prefix_path[1]:
        branch_path = os.path.join(os.getcwd(), ".git", prefix_path[1].replace("\n", ""))
        with open(branch_path, "w") as f:
            f.write(commit_hash + "\n")

    # 直接ハッシュ値が格納されていたHEADに直接書き込み
    # head_content = "{}".format(commit_hash)
    # with open(path, "r+") as f:
    # f.truncate(0)
    # f.seek(0)
    # f.write(head_content + "\n")

    return None

def cmd_add(args):
    if not args.files:
        parser_add.error('Nothing specified, nothing added.')
    for filename in args.files:
        write_blob(filename)
        update_index(filename)
    return

def cmd_commit(args):
    tree_hash = write_tree()
    hash = commit_tree(tree_hash, args.m)
    if hash != None:
        update_ref(hash)
    return

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers()

parser_add = subparsers.add_parser('add', help='Add file contents to the index')
parser_add.add_argument('files', nargs='*')
parser_add.set_defaults(handler=cmd_add)

parser_commit = subparsers.add_parser('commit', help='Record changes to the repository')
parser_commit.add_argument('-m', metavar='msg', required=True, help='commit message')
parser_commit.set_defaults(handler=cmd_commit)

args = parser.parse_args()
if hasattr(args, 'handler'):
    args.handler(args)
