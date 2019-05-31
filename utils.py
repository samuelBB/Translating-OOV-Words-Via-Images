"""
misc utility functions
"""

import re
import os
import errno
import pickle
import random
import logging
import argparse

import datetime as dt


RANDOM_SEED = 2018


### logging

class UpToLevel(object):
    def __init__(self, lvl=logging.FATAL):
        self.lvl = lvl

    def filter(self, record):
        return record.levelno <= self.lvl


ROOT = '*'


def init_logging(file=None, stdout=False, stderr=False,
                 lo_lvl=logging.DEBUG, hi_lvl=logging.FATAL,
                 file_lo_lvl=None, stdout_lo_lvl=None, stderr_lo_lvl=None,
                 file_hi_lvl=None, stdout_hi_lvl=None, stderr_hi_lvl=None,
                 fmt='[%(asctime)s|%(levelname)s|%(module)s'
                     '.%(funcName)s:%(lineno)d] %(message)s',
                 datefmt='%Y-%m-%d_%H:%M:%S',
                 mode='w'):
    logger = logging.getLogger(ROOT)
    if is_(lo_lvl):
        logger.setLevel(lo_lvl)
    if is_(hi_lvl):
        logger.addFilter(UpToLevel(hi_lvl))

    for name, obj, args, prefix in [
        ('stdout', stdout,  [logging.sys.stdout], 'Stream'),
        ('stderr', stderr,                    (), 'Stream'),
        (  'file',   file,          (file, mode),   'File')
    ]:
        if obj:
            handler = getattr(logging, prefix + 'Handler')(*args)
            handler.setFormatter(logging.Formatter(fmt, datefmt))
            lo, hi = locals()[name+'_lo_lvl'], locals()[name+'_hi_lvl']
            if is_(lo):
                handler.setLevel(lo)
            if is_(hi):
                handler.addFilter(UpToLevel(hi))
            logger.addHandler(handler)
            if name == 'file':
                return handler



def main_module_name(name, ext=True):
    if name == '__main__':
        try:
            main_file = __import__(name).__file__
            name_and_ext = main_file[main_file.rfind('/')+1:]
            if ext:
                return name_and_ext[:name_and_ext.rfind('.')]
            return name_and_ext
        except:
            pass
    return name


def get_logger(name, main=False):
    name = main_module_name(name) if main else name
    return logging.getLogger(ROOT + '.' + name)


### timing

def time_stamp(fmt='%Y-%-m-%-d_%-H-%-M-%-S'):
    return dt.datetime.now().strftime(fmt)


### io

def write_lines(iterable, path):
    with open(path, 'w') as io:
        for item in iterable:
            print(item, file=io)


def read_lines(path):
    with open(path) as io:
        return [line.strip() for line in io]


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def get_path_elems_unix(path, i, j='', delim='_'):
    elems = re.sub('//+', '/', path).strip('/').split('/')
    return elems[i] if j == '' or i == j else delim.join(elems[i:j])


def load(path, method=pickle):
    with open(path, 'rb') as f:
        return method.load(f)


def dump(obj, path, method=pickle, **kw):
    if not kw and method.__name__ in ('pickle', 'dill'):
        kw = dict(protocol=-1)
    with open(path, 'wb') as f:
        method.dump(obj, f, **kw)


def scandir_r(path):
    for entry in os.scandir(path):
        if entry.is_dir(follow_symlinks=False):
            yield from scandir_r(entry.path)
        else: yield entry


def mapread(path, f):
    with open(path) as io:
        yield from map(f, io) if f else io


### convenience

def is_(x):
    return x is not None


def dedupe(it):
    s = set()
    for el in it:
        if el not in s:
            s.add(el)
            yield el


### parsing

def arg(*ar, **kw):
    return ar, kw


def strip_attrs(opts, *attrs):
    for attr in attrs:
        yield getattr(opts, attr)
        delattr(opts, attr)


def parse_args(*args, strip=None):
    parser = argparse.ArgumentParser()
    for ar, kw in args:
        parser.add_argument(*ar, **kw)
    opts = parser.parse_args()
    if is_(strip):
        return (opts, *strip_attrs(opts, *strip))
    return opts


### sampling

_RNG = random.Random(RANDOM_SEED)


def sample(lst, n=None):
    return _RNG.sample(lst, n or len(lst))