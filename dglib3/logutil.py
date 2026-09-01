# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import logging


class LogTimeContext(object):
    """
    统计一些语句的执行时间

    示例：
        with LogTimeContext('test001', min_sec=10):
            test('001')
    """

    def __init__(self, name, min_sec=0):
        import logging
        self.name = name
        self.min_sec = min_sec
        self.log = logging.getLogger()
        self.tick_start = 0

    def __enter__(self):
        self.tick_start = time.clock()

    def __exit__(self, exc_type, exc_val, exc_tb):
        dt = time.clock() - self.tick_start
        if not self.min_sec or dt >= self.min_sec:
            self.log.debug('%s cost: %.2fms', self.name, dt * 1000)


def log_time(min_sec=0):
    """
    返回一个装饰器，用来统计被装饰的方法的执行时间。

    参数：
        min_sec 超过多少秒才记录到日志，默认0表示不限。

    示例：
        @log_time(min_sec=10)
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
            if not min_sec or dt >= min_sec:
                logger.debug('%s() cost: %.2fms', func.__name__, dt)

        return wrapped

    return decorator



class ThroughputReporter:
    """高吞吐网络 QPS 及带宽（吞吐量）监控统计工具类"""

    MODE_RECV = "recv"  # 仅统计接收 (RX)
    MODE_SEND = "send"  # 仅统计发送 (TX)
    MODE_BOTH = "both"  # 统计接收与发送 (RX & TX)

    def __init__(
        self,
        log: logging.Logger,
        mode: str = MODE_BOTH,
        interval: float = 1.0,
        level: int = logging.INFO,
    ):
        """
        :param log: 传入的 logging.Logger 实例
        :param mode: 统计模式: 'recv' (仅接收), 'send' (仅发送), 'both' (两者都统计)
        :param interval: 汇报时间间隔（秒），默认 1.0 秒
        :param level: 输出日志的级别，默认 logging.INFO
        """
        self.log = log
        self.mode = mode.lower()
        self.interval = interval
        self.level = level

        # 接收统计
        self._rx_bytes = 0
        self._rx_msgs = 0

        # 发送统计
        self._tx_bytes = 0
        self._tx_msgs = 0

        # 记录起始时间 (使用单调时钟，避免系统时间修改影响)
        self._last_time = time.monotonic()

    def record_recv(self, byte_count: int, msg_count: int = 1) -> None:
        """记录一次（或多条）接收数据并自动检查是否触发输出"""
        self._rx_bytes += byte_count
        self._rx_msgs += msg_count
        self._check_and_report()

    def record_send(self, byte_count: int, msg_count: int = 1) -> None:
        """记录一次（或多条）发送数据并自动检查是否触发输出"""
        self._tx_bytes += byte_count
        self._tx_msgs += msg_count
        self._check_and_report()

    def _check_and_report(self) -> None:
        """检查是否到达统计周期，若是则输出日志并重置计数器"""
        now = time.monotonic()
        elapsed = now - self._last_time

        if elapsed < self.interval:
            return

        # 若当前日志级别未开启，直接跳过计算与格式化
        if not self.log.isEnabledFor(self.level):
            self._reset(now)
            return

        if self.mode == self.MODE_RECV:
            rx_qps = self._rx_msgs / elapsed
            rx_speed = self._format_speed(self._rx_bytes / elapsed)
            self.log.log(self.level, "RX: %0.1f msg/s (%s)", rx_qps, rx_speed)

        elif self.mode == self.MODE_SEND:
            tx_qps = self._tx_msgs / elapsed
            tx_speed = self._format_speed(self._tx_bytes / elapsed)
            self.log.log(self.level, "TX: %0.1f msg/s (%s)", tx_qps, tx_speed)

        else:  # MODE_BOTH
            rx_qps = self._rx_msgs / elapsed
            rx_speed = self._format_speed(self._rx_bytes / elapsed)
            tx_qps = self._tx_msgs / elapsed
            tx_speed = self._format_speed(self._tx_bytes / elapsed)
            self.log.log(
                self.level,
                "RX: %0.1f msg/s (%s) | TX: %0.1f msg/s (%s)",
                rx_qps,
                rx_speed,
                tx_qps,
                tx_speed,
            )

        self._reset(now)

    def _reset(self, now: float) -> None:
        """重置计数器与时间戳"""
        self._rx_bytes = 0
        self._rx_msgs = 0
        self._tx_bytes = 0
        self._tx_msgs = 0
        self._last_time = now

    @staticmethod
    def _format_speed(bytes_per_sec: float) -> str:
        """格式化为易读的 B/s, KB/s, MB/s, GB/s"""
        speed = bytes_per_sec
        for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
            if speed < 1024.0:
                return f"{speed:.2f} {unit}"
            speed /= 1024.0
        return f"{speed:.2f} TB/s"