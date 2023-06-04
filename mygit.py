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

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers()

args = parser.parse_args()
if hasattr(args, 'handler'):
    args.handler(args)