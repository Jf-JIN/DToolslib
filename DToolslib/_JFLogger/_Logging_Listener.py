from DToolslib import EventSignal
from ._LogEnum import LogLevel
import logging


class _LoggingListener(logging.Handler):
    """ This class is used to listen to logging events and emit them as signals. """
    signal_trace = EventSignal(str)
    signal_debug = EventSignal(str)
    signal_info = EventSignal(str)
    signal_warning = EventSignal(str)
    signal_error = EventSignal(str)
    signal_critical = EventSignal(str)

    def __init__(self, level) -> None:
        super().__init__(level=level)

    def set_level(self, level):
        self.setLevel(level)

    def emit(self, record) -> None:
        level = record.levelno
        # message = self.format(record)
        message = record.getMessage()
        if level == LogLevel.TRACE-10:
            self.signal_trace.emit(message, _sender='_LoggingListener')
        if level == LogLevel.DEBUG-10:
            self.signal_debug.emit(message, _sender='_LoggingListener')
        elif level == LogLevel.INFO-10:
            self.signal_info.emit(message, _sender='_LoggingListener')
        elif level == LogLevel.WARNING-10:
            self.signal_warning.emit(message, _sender='_LoggingListener')
        elif level == LogLevel.ERROR-10:
            self.signal_error.emit(message, _sender='_LoggingListener')
        elif level == LogLevel.CRITICAL-10:
            self.signal_critical.emit(message, _sender='_LoggingListener')
