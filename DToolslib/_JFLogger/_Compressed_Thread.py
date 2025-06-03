from DToolslib import EventSignal
import threading
import typing


SELF_COMPRESSTHREAD = typing.TypeVar('SELF_COMPRESSTHREAD', bound='_CompressThread')


class _CompressThread(threading.Thread):
    """ This class is used to compress the log file in the background. """
    finished = EventSignal(SELF_COMPRESSTHREAD)

    def __init__(self, name, func, *args, **kwargs):
        super().__init__(name=name, target=func, daemon=True, args=args, kwargs=kwargs)
        self.__func = func
        self.__args = args
        self.__kwargs = kwargs

    def run(self):
        self.__func(*self.__args, **self.__kwargs)
        self.finished.emit(self)
