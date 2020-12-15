# -*- coding: utf-8 -*-
import sys
import os
import re
import glob
import codecs
import datetime
import threading
import time
import logging.handlers

from .utils import module_path, isoformat_date, makesure_dirpathexists, SYS_ENCODING


class BlackHole(object):
    softspace = 0

    def write(self, text):
        pass

    def flush(self):
        pass


class CompositeFile(object):
    """
    复合文件对象，可通过add()方法加入多个文件对象一起输出。
    如：.add(sys.sysout)
    """

    def __init__(self, filename="", mode="w", encoding="", nocache=False):
        self.files = []
        self.encoding = encoding
        if filename:
            if encoding:
                f = codecs.open(filename, mode, encoding)
            else:
                f = open(filename, mode)
            self.files.append(f)
        self.nocache = nocache

    def add(self, f):
        if f not in self.files:
            self.files.append(f)

    def remove(self, f):
        if f in self.files:
            self.files.remove(f)

    def write(self, text):
        for f in self.files:
            unicode_safe_write(f, text, self.encoding)
        if self.nocache:
            self.flush()

    def flush(self):
        for f in self.files:
            if hasattr(f, 'flush'):
                f.flush()

    def close(self):
        for f in self.files:
            f.close()


class SafeOutStream(object):
    def __init__(self, underlying_stream, encoding=None, errors='replace'):
        self.underlying_stream = underlying_stream
        self.encoding = encoding
        self.errors = errors

    def write(self, s):
        if isinstance(s, unicode):
            s = s.encode(self.encoding, errors=self.errors)
        self.underlying_stream.write(s)

    def flush(self):
        self.underlying_stream.flush()


class ScreenLogger(object):
    """
    可将屏幕输出的内容同时保存到一个日志文件。
    用法：
    sys.stdout = sys.stderr = ScreenLogger("日志文件名")
    """

    def __init__(self, filename="", encoding=None, append=False, showtime=False, logfile=None):
        self.filename = filename
        self.append = append
        self.showtime = showtime
        self.logfile = logfile
        self.lastlogtime = 0
        self.encoding = encoding
        self.stdout = sys.__stdout__

    def create_file(self, filename, append):
        if append and os.path.exists(filename):
            logfile = codecs.open(filename, "a", self.encoding)
        else:
            makesure_dirpathexists(filename)
            logfile = codecs.open(filename, "w", self.encoding)
        return logfile

    def write(self, s):
        if self.showtime:
            now = int(time.time())
            if self.lastlogtime != now:
                self.lastlogtime = now
                s = "\n".join([time.strftime("\n%Y-%m-%d %H:%M:%S"), s])

        if not self.logfile and self.filename:
            try:
                self.logfile = self.create_file(self.filename, self.append)
            except:
                pass
        if self.logfile:
            self.logfile.write(s)

    def flush(self):
        self.stdout.flush()
        if self.logfile:
            try:
                self.logfile.flush()
            except:
                pass


class StreamToLogger(object):
    """
    Fake file-like stream object that redirects writes to a logger instance.
    http://www.electricmonk.nl/log/2011/08/14/redirect-stdout-and-stderr-to-a-logger-in-python/
    """

    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())


def redirect_stdout_stderr_tologger():
    logger_stdout = logging.getLogger('STDOUT')
    stdout = CompositeFile()  # 使用CompositeFile避免与py2exe.boot_common中的sys.stdout冲突。
    stdout.add(sys.stdout)
    stdout.add(StreamToLogger(logger_stdout, logging.INFO))
    sys.stdout = stdout

    logger_stderr = logging.getLogger('STDERR')
    stderr = CompositeFile()  # 使用CompositeFile避免与py2exe.boot_common中的sys.stderr冲突。
    stderr.add(sys.stderr)
    stderr.add(StreamToLogger(logger_stderr, logging.ERROR))
    sys.stderr = stderr


def nullfile():
    import platform
    return "/dev/null" if platform.system() == "Linux" else "nul"


def safe_coding(s, encoding=None, safe_stuff=None, errors='replace'):
    if not encoding:
        encoding = SYS_ENCODING
    if isinstance(s, unicode):
        if safe_stuff is None:
            safe_stuff = s.encode(encoding, errors=errors)
    else:
        if safe_stuff is None:
            safe_stuff = s.decode(encoding, errors=errors)
    return safe_stuff
