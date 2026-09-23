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

    def __init__(self, filename='', mode='w', encoding='', nocache=False):
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
        if isinstance(s, str):
            s = s.encode(self.encoding or SYS_ENCODING, errors=self.errors)
        self.underlying_stream.write(s)

    def flush(self):
        self.underlying_stream.flush()


class ScreenLogger(object):
    """
    可将屏幕输出的内容同时保存到一个日志文件。
    用法：
    sys.stdout = sys.stderr = ScreenLogger("日志文件名")
    """

    def __init__(self, filename='', encoding=None, append=False, showtime=False, logfile=None):
        self.filename = filename
        self.append = append
        self.showtime = showtime
        self.logfile = logfile
        self.lastlogtime = 0
        self.encoding = encoding
        self.stdout = sys.__stdout__

    def create_file(self, filename, append):
        if append and os.path.exists(filename):
            logfile = codecs.open(filename, 'a', self.encoding)
        else:
            makesure_dirpathexists(filename)
            logfile = codecs.open(filename, 'w', self.encoding)
        return logfile

    def write(self, s):
        if self.showtime:
            now = int(time.time())
            if self.lastlogtime != now:
                self.lastlogtime = now
                s = '\n'.join([time.strftime('\n%Y-%m-%d %H:%M:%S'), s])

        # 回显到真正的控制台（self.stdout 是 __init__ 时捕获的 __stdout__，
        # 避免 sys.stdout 被替换成自身后无限递归）。
        unicode_safe_write(self.stdout, s)

        if not self.logfile and self.filename:
            try:
                self.logfile = self.create_file(self.filename, self.append)
            except:
                pass
        if self.logfile:
            try:
                self.logfile.write(s)
            except Exception:
                pass

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

    def flush(self):
        for hdlr in self.logger.handlers:
            hdlr.flush()


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
    return '/dev/null' if platform.system() == 'Linux' else 'nul'


def unicode_safe_write(f, s, encoding=None, safe_stuff=None):
    """
    写入流时自动适配流类型与内容类型；文本流编码失败时做有损清洗后重写。
    - 文本流 + str：直接写；编码失败按流自身编码（缺省 SYS_ENCODING）清洗后重写。
    - 二进制流 + bytes：直接写。
    - 二进制流 + str：按 encoding 编码成 bytes 写入（py2 版即有此行为）。
    - 文本流 + bytes：按 encoding 解码成 str 写入。
    :param f: 有write方法的对象。
    :param s: 要写的内容，str 或 bytes。
    :param encoding: 类型适配或清洗时采用的编码，缺省优先取流自身 encoding，否则 SYS_ENCODING。
    :param safe_stuff: 发生 UnicodeError 时写入这个，如果为None的话才会去做清洗，多个同类型流输出时可提高效率。
    :return: 发生 UnicodeError 时返回清洗后的str，否则返回None。
    """
    try:
        f.write(s)
    except UnicodeError:
        # 文本流编码失败：优先用目标流自身的编码清洗（如控制台代码页），否则可能清洗后依然无法写出。
        if not encoding:
            encoding = getattr(f, 'encoding', None) or SYS_ENCODING
        safe_stuff = safe_coding(s, encoding)
        f.write(safe_stuff)
    except TypeError:
        # py2 中流类型与内容类型不匹配时 file.write 同样抛 UnicodeError 走上面的分支，
        # py3 拆分后改为 TypeError，这里做等价适配：
        # 二进制流 + str -> 编码后写入；文本流 + bytes -> 解码后写入。
        # 仅对 str/bytes 做适配，其余 TypeError 照常抛出，避免掩盖调用方错误。
        if not isinstance(s, (str, bytes)):
            raise
        if not encoding:
            encoding = getattr(f, 'encoding', None) or SYS_ENCODING
        if isinstance(s, str):
            s = s.encode(encoding, errors='replace')
        else:
            s = s.decode(encoding, errors='replace')
        f.write(s)
    return safe_stuff


def safe_coding(s, encoding=None, safe_stuff=None, errors='replace'):
    """py3：bytes 按 encoding 解码为 str；str 中按 encoding 无法编码的字符按 errors 策略替换，
    保证返回值可以安全写入文本流。"""
    if not encoding:
        encoding = SYS_ENCODING
    if isinstance(s, bytes):
        if safe_stuff is None:
            safe_stuff = s.decode(encoding, errors=errors)
    elif safe_stuff is None:
        safe_stuff = s.encode(encoding, errors=errors).decode(encoding, errors=errors)
    return safe_stuff
