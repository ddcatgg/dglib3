# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import logging


class LogTimeContext(object):
    """
    统计一些语句的执行时间

    示例：
        with LogTimeContext('test001', min_ms=10):
            test('001')
    """

    def __init__(self, name, min_ms=0):
        import logging
        self.name = name
        self.min_ms = min_ms
        self.log = logging.getLogger()
        self.tick_start = 0

    def __enter__(self):
        self.tick_start = time.clock()

    def __exit__(self, exc_type, exc_val, exc_tb):
        dt = time.clock() - self.tick_start
        if not self.min_ms or dt >= self.min_ms:
            self.log.debug('%s cost: %.2fms', self.name, dt * 1000)


def log_time(log_min_ms=0):
    """
    返回一个装饰器，用来统计被装饰的方法的执行时间。

    参数：
        log_min_ms 超过多少毫秒才记录到日志，默认0表示不限。

    示例：
        @log_time(log_min_ms=10)
        def _make_title(self):
            title = util.make_random_title()
            if self.cfg.html_use_encode:
                title = util.transform_string_to_ncr_dec(title)
            elif self.cfg.html_use_xencode:
                title = util.transform_string_to_ncr_hex(title)
            self.content, c = R_TITLE.subn(title, self.content)
            self.log.debug('完成了 %d 处替换。', c)
            return c
    """

    def decorator(func):
        def wrapped(self):
            logger = logging.getLogger()
            t = time.clock()
            func(self)
            dt = (time.clock() - t) * 1000
            if not log_min_ms or dt >= log_min_ms:
                logger.debug('%s() cost: %.2fms', func.__name__, dt)

        return wrapped

    return decorator
