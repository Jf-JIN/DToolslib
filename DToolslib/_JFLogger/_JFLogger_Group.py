
import queue
import sys
import os
import threading
from datetime import datetime
import typing
import zipfile
import time
import atexit
from DToolslib import EventSignal
from DToolslib.Color_Text import *
from ._LogEnum import LogLevel, _ColorMap, _Log_Default
from ._JFLogger import JFLogger
from ._Compressed_Thread import _CompressThread


class JFLoggerGroup(object):
    """
    This class is used to manage a group of loggers. It can collect the log message of all or some loggers and write them to a specific file.
    It is Singleton.

    - Args:
        - root_dir(str): The root directory of the log group.
        - root_folder_name(str): The name of the root folder of the log group.
        - limit_single_file_size_kB(int): The maximum size of a single log file, in kilobytes. Default is no limit.
        - limit_files_count(int): The maximum number of log files. Default is no limit.
        - limit_files_days(int): The maximum number of days to keep log files. Default is no limit.
        - enableDailySplit(bool): Whether to split the log files daily. Default is False.
        - enableFileOutput(bool): Whether to output the log files. Default is True.

    - Signals:
        - signal_format: formatted log messages
        - signal_colorized: formatted log messages with color
        - signal_message: log messages without color and format

        parameter of slot function: 
            - level_str(str): `LogLevel.TRACE`, `LogLevel.DEBUG`, `LogLevel.INFO`, `LogLevel.WARNING`, `LogLevel.ERROR`, `LogLevel.CRITICAL`
            - message(str)

    - methods:
        - set_root_dir(root_dir): Set the root directory for the log files.
        - set_root_folder_name(root_folder_name): Set the root folder name for the log files.
        - set_enable_daily_split(enable): Set whether to split the log files daily.
        - set_enable_file_output(enable): Set whether to output log files.
        - set_enable_runtime_zip(enable): Set whether to zip the log files at runtime.
        - set_enable_startup_zip(enable): Set whether to zip the log files at startup.
        - set_file_size_limit_kB(size_limit): Set the file size limit for the log files in kB.
        - set_file_count_limit(count_limit): Set the file count limit for the log files.
        - set_file_days_limit(days_limit): Set the file days limit for the log files.
        - set_log_group(log_group): Set the log group list.
        - append_log(log_obj): Append a log object to the log group.
        - remove_log(log_obj): Remove a log object from the log group.
        - clear(): Clear all log objects from the log group.

    - Example:

    Log = JFLogger('test')

    Log_2 = JFLogger('test_2')

    Log_gp = JFLoggerGroup()

    Then Log_gp can get the log information of Log and Log_2
    """
    __instance = None
    __lock__ = threading.Lock()
    signal_format = EventSignal(int, str)
    signal_colorized = EventSignal(int, str)
    signal_message = EventSignal(int, str)

    def __new__(cls, *args, **kwargs):
        if not cls.__instance:
            with cls.__lock__:
                if not cls.__instance:
                    cls.__instance = super().__new__(cls)
                    cls.__instance.__isInitialized = False
        return cls.__instance

    def __init__(
        self,
        root_dir: str = '',
        root_folder_name: str = '',
        log_group: list = [],
        exclude_logs: list = [],
        limit_single_file_size_kB: int = -1,  # KB
        limit_files_count: int = -1,
        limit_files_days: int = -1,
        enableDailySplit: bool = False,
        enableFileOutput: bool = True,
    ) -> None:
        if self.__isInitialized:
            # sys.stdout.write(f'\x1B[93m <Warning> {self.__class__.__name__} initialization is already complete. Reinitialization is invalid.\x1B[0m\n')
            return
        self.__isInitialized = True
        self.__enableFileOutput = enableFileOutput
        self.__enableDailySplit = enableDailySplit
        self.__start_time: datetime = datetime.now()
        self.__root_folder_name = root_folder_name if root_folder_name else _Log_Default.ROOT_FOLDER_NAME
        if not isinstance(root_dir, str):
            raise ValueError(f'<WARNING> {self.__class__.__name__} root dir "{root_dir}" is not a string.')
        self.__root_dir: str = root_dir
        self.__root_path: str = os.path.join(self.__root_dir, self.__root_folder_name) if self.__root_dir else ''
        self.__isExistsPath = False
        if root_dir and os.path.exists(root_dir):
            self.__isExistsPath = True
        elif root_dir:
            raise FileNotFoundError(f'{self.__class__.__name__} root dir "{root_dir}" does not exist, create it.')
        else:
            warning_text = (
                ansi_color_text('< WARNING > No File Output from', _ColorMap.LIGHTYELLOW.ANSI_TXT) +
                ansi_color_text(f'{self.__class__.__name__}\n   ', _ColorMap.LIGHTYELLOW.ANSI_TXT, _ColorMap.GRAY.ANSI_BG) +
                ansi_color_text(
                    f'- No log file will be recorded because the log root path is not specified. The current root path input is "{self.__root_path}". Type: {type(self.__root_path)}', txt_color=_ColorMap.YELLOW.ANSI_TXT)
            )
            if sys.stdout:
                sys.stdout.write(warning_text)
        self.__isNewFile = True
        self.__limit_single_file_size_Bytes: int = limit_single_file_size_kB * 1000 if isinstance(limit_single_file_size_kB, int) else -1
        self.__limit_files_count = limit_files_count if isinstance(limit_files_count, int) else -1
        self.__limit_files_days = limit_files_days if isinstance(limit_files_days, int) else -1
        self.__log_dir = os.path.join(self.__root_path, _Log_Default.GROUP_FOLDER_NAME)
        self.__current_size = 0
        self.__current_day = datetime.today().date()
        self.__log_group = []
        self.__exclude_logs = exclude_logs if isinstance(exclude_logs, list) else []
        self.__isInitializationFinished = False
        self.__thread_lock = threading.Lock()
        self.__thread_compress_lock = threading.Lock()
        self.__log_file_path_last_queue = queue.Queue()
        self.__compression_thread_pool = set()
        self.__enableRuntimeZip = False
        self.__enableStartupZip = False
        self.__hasWrittenFirstFile = False
        self.__isStrictLimit = False
        self.__zip_file_path = ''
        self.set_log_group(log_group)
        atexit.register(self.__compress_current_old_log_end)
        self.__isInitializationFinished = True

    def set_root_dir(self, root_dir: str) -> typing.Self:
        """ 
        Set the root directory for the log files

        - Args:
            - root_dir(str): the root directory
        """
        self.__root_dir = root_dir
        self.__root_path: str = os.path.join(self.__root_dir, self.__root_folder_name) if self.__root_dir else ''
        self.__log_dir = os.path.join(self.__root_path, _Log_Default.GROUP_FOLDER_NAME)
        if self.__root_dir and os.path.exists(self.__root_dir):
            self.__isExistsPath = True
        else:
            self.__isExistsPath = False
        return self

    def set_root_folder_name(self, root_folder_name: str) -> typing.Self:
        """ 
        Set the root folder name for the log files

        - Args:
            - root_folder_name(str): the root folder name
        """
        if not root_folder_name:
            self.__root_folder_name = _Log_Default.ROOT_FOLDER_NAME
        else:
            self.__root_folder_name = root_folder_name
        self.__root_path: str = os.path.join(self.__root_dir, self.__root_folder_name) if self.__root_dir else ''
        self.__log_dir = os.path.join(self.__root_path, _Log_Default.GROUP_FOLDER_NAME)
        return self

    def set_enable_daily_split(self, enable: bool) -> typing.Self:
        """ 
        Set whether to split the log files daily.

        - Args:
            - enable(bool): whether to split the log files daily        
        """
        self.__enableDailySplit: bool = enable
        return self

    def set_enable_file_output(self, enable: bool) -> typing.Self:
        """ 
        Set whether to output log files.

        - Args:
            - enable(bool): whether to output log files
        """
        self.__enableFileOutput: bool = enable
        return self

    def set_enable_runtime_zip(self, enable: bool) -> typing.Self:
        """ 
        Set whether to zip the log files at runtime

        - Args:
            - enable(bool): whether to zip the log files at runtime
        """
        self.__enableRuntimeZip: bool = enable
        return self

    # def set_enable_startup_zip(self, enable: bool) -> typing.Self:
    #     """
    #     Set whether to zip the log files at startup.

    #     - Args:
    #       - enable(bool): whether to zip the log files at startup
    #     """
    #     self.__enableStartupZip = enable
    #     return self

    def set_file_size_limit_kB(self, size_limit: typing.Union[int, float]) -> typing.Self:
        """ 
        Set the file size limit for the log files in kB.

        This setting does not limit the length of a single message. If a single message exceeds the set value, in order to ensure the integrity of the message, even if the size exceeds the limit, it will be written to the log file. Therefore, the current file size will exceed the limit.

        - Args:
            - size_limit(int | float): the single file size limit for the log files in kB
        """
        if not isinstance(size_limit, (int, float)):
            raise TypeError("size_limit must be int")
        self.__limit_single_file_size_Bytes: typing.Union[int, float] = size_limit * 1000
        return self

    def set_file_count_limit(self, count_limit: int, isStict: bool = False) -> typing.Self:
        """ 
        Set the file count limit for the log files.

        - Args:
            - count_limit(int): the file count limit for the log files
        """
        if not isinstance(count_limit, int):
            raise TypeError("count_limit must be int")
        self.__limit_files_count: int = count_limit
        if isStict:
            self.__isStrictLimit = True
        else:
            self.__isStrictLimit = False
        self.__clear_files()
        return self

    def set_file_days_limit(self, days_limit: int, isStict: bool = False) -> typing.Self:
        """ 
        Set the file days limit for the log files.

        - Args:
            - days_limit(int): the file days limit for the log files
        """
        if not isinstance(days_limit, int):
            raise TypeError("days_limit must be int")
        self.__limit_files_days: int = days_limit
        if isStict:
            self.__isStrictLimit = True
        else:
            self.__isStrictLimit = False
        self.__clear_files()
        return self

    def set_log_group(self, log_group: list) -> typing.Self:
        """ 
        Set the log group list.

        - Args:
            - log_group(list): the log group list
        """
        if not isinstance(log_group, list):
            raise TypeError('log_group must be list')
        if self.__log_group == log_group and self.__isInitializationFinished:
            return
        self.__log_group = log_group
        self.__disconnect(log_group)
        if log_group:
            self.__disconnect_all()
            self.__connection()
        else:
            self.__connect_all()
        return self

    def append_log(self, log_obj: typing.Union[JFLogger, list]) -> typing.Self:
        """ 
        Append a log object to the log group

        - Args:
            - log_obj(JFLogger or list): the log object or the log object list
        """
        if isinstance(log_obj, (list, tuple)):
            self.__log_group += list(log_obj)
            for log in list(log_obj):
                self.__connect_single(log)
        elif isinstance(log_obj, JFLogger):
            self.__log_group.append(log_obj)
            self.__connect_single(log_obj)
        else:
            raise TypeError(f'log_obj must be list or JFLogger, but got {type(log_obj)}')
        return self

    def remove_log(self, log_obj: JFLogger) -> typing.Self:
        """ 
        Remove a log object from the log group

        - Args:
            - log_obj: JFLogger object to be removed
        """
        if not isinstance(log_obj, JFLogger):
            raise TypeError(f'log_obj must be JFLogger, but got {type(log_obj)}')
        if log_obj in self.__log_group:
            self.__log_group.remove(log_obj)
            self.__disconnect_single(log_obj)
        if len(self.__log_group) == 0:
            self.__connect_all()
        return self

    def clear(self) -> None:
        """ Clear all log objects from the log group """
        self.__disconnect_all()
        self.__log_group: list = []
        self.__connect_all()

    def __connect_all(self) -> None:
        for log_obj in JFLogger.__instance_list__:
            log_obj: JFLogger
            if log_obj in self.__exclude_logs:
                continue
            self.__connect_single(log_obj)

    def __disconnect_all(self) -> None:
        for log_obj in JFLogger.__instance_list__:
            log_obj: JFLogger
            self.__disconnect_single(log_obj)

    def __connection(self) -> None:
        if not self.__log_group:
            return
        for log_obj in self.__log_group:
            log_obj: JFLogger
            if log_obj in self.__exclude_logs:
                continue
            self.__connect_single(log_obj)

    def __disconnect(self, log_group) -> None:
        for log_obj in self.__log_group:
            log_obj: JFLogger
            if log_obj in log_group:
                self.__disconnect_single(log_obj)

    def __set_log_file_path(self) -> None:
        # Support: {}[];'',.!~@#$%^&()_+-=
        if not self.__enableFileOutput or self.__isExistsPath is False:
            return
        if not self.__hasWrittenFirstFile:  # First time to write file
            self.__start_time_format: str = self.__start_time.strftime("%Y%m%d_%H%M%S")
            self.__log_dir: str = os.path.join(self.__root_path, _Log_Default.GROUP_FOLDER_NAME)
            if not os.path.exists(self.__log_dir):
                os.makedirs(self.__log_dir)
            self.__log_file_path: str = os.path.join(self.__log_dir, f'Global_Log-[{self.__start_time_format}]--0.log')
            if os.path.exists(self.__log_file_path):
                index = 1
                while True:
                    self.__log_file_path = os.path.join(self.__log_dir, f'Global_Log-[{self.__start_time_format}]_{index}--0.log')
                    if not os.path.exists(self.__log_file_path):
                        break
                    index += 1
            str_list = os.path.splitext(os.path.basename(self.__log_file_path))[0].split('--')
        else:
            self.__log_file_path_last_queue.put(self.__log_file_path)
            file_name: str = os.path.splitext(os.path.basename(self.__log_file_path))[0]
            str_list = file_name.split('--')
            self.__log_file_path = os.path.join(self.__log_dir, f'{str_list[0]}--{int(str_list[-1]) + 1}.log')
        if not self.__zip_file_path:
            self.__zip_file_path = os.path.join(self.__log_dir, f'{str_list[0]}--Compressed.zip')

    def __clear_files(self) -> None:
        """
        The function is used to clear the log files in the log directory.
        """
        if self.__isExistsPath is False:
            return
        if not (isinstance(self.__limit_files_count, int) and self.__limit_files_count < 0) and not (isinstance(self.__limit_files_days, int) and self.__limit_files_days <= 0):
            return
        current_folder_path = os.path.join(self.__root_path, _Log_Default.GROUP_FOLDER_NAME)
        if not os.path.exists(current_folder_path):
            return
        current_file_list = []
        for file in os.listdir(current_folder_path):
            fp = os.path.join(current_folder_path, file)
            if file.endswith('.log') and os.path.isfile(fp):
                current_file_list.append(fp)
        length_file_list = len(current_file_list)
        # clear files by count
        if (isinstance(self.__limit_files_count, int) and self.__limit_files_count >= 0) and length_file_list > self.__limit_files_count:
            sorted_files = sorted(current_file_list, key=os.path.getctime)
            for file_path in sorted_files[:length_file_list - self.__limit_files_count]:
                os.remove(file_path)
        # clear file by days
        elif isinstance(self.__limit_files_days, int) and self.__limit_files_days > 0:
            for file_path in current_file_list:
                if (datetime.today() - datetime.fromtimestamp(os.path.getctime(file_path))).days > self.__limit_files_days:
                    os.remove(file_path)

    def __compress_current_old_log(self) -> None:
        """ Compress the old logs currently rotated (not the historical log before startup) """
        with self.__thread_compress_lock:
            if not self.__log_file_path_last_queue.empty():
                last_log_file_path = self.__log_file_path_last_queue.get()
                try:
                    with zipfile.ZipFile(self.__zip_file_path, 'a', zipfile.ZIP_DEFLATED) as zipf:
                        arcname = os.path.basename(last_log_file_path)
                        if arcname in zipf.namelist():
                            return
                        zipf.write(last_log_file_path, arcname=arcname)
                    os.remove(last_log_file_path)
                except Exception as e:
                    pass  # TODO

    def __run_async_rotated_log_compression(self):
        if self.__log_file_path_last_queue.empty() or not self.__enableRuntimeZip:
            return
        zip_dir = os.path.dirname(self.__zip_file_path)
        if not os.path.exists(zip_dir):
            os.makedirs(zip_dir)
        t = _CompressThread(name=f'RotatedLogCompressThread<{self.__class__.__name__}>-{len(self.__compression_thread_pool)}', func=self.__compress_current_old_log)
        t.finished.connect(self.__compress_current_old_log_finished)
        self.__compression_thread_pool.add(t)
        t.start()

    def __compress_current_old_log_finished(self, thread_obj: _CompressThread):
        self.__compression_thread_pool.discard(thread_obj)

    def __compress_current_old_log_end(self):
        if not self.__enableRuntimeZip:
            return
        try:
            self.__log_file_path_last_queue.put(self.__log_file_path)
            self.__compress_current_old_log()
            time.sleep(0.5)
        except:
            pass

    def __write(self, message: str) -> None:
        with self.__thread_lock:
            if not self.__enableFileOutput or self.__isExistsPath is False:
                return
            if self.__limit_single_file_size_Bytes and self.__limit_single_file_size_Bytes > 0:
                # Size limit
                writting_size = len(message.encode('utf-8'))
                self.__current_size += writting_size
                if self.__current_size >= self.__limit_single_file_size_Bytes:
                    self.__isNewFile = True
            if self.__enableDailySplit:
                # Split by day
                if datetime.today().date() != self.__current_day:
                    self.__isNewFile = True
            if self.__isNewFile:
                # Create a new file
                self.__isNewFile = False
                self.__set_log_file_path()
                self.__current_day = datetime.today().date()
                file_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                start_time = self.__start_time.strftime('%Y-%m-%d %H:%M:%S')
                message = f"""{'#'*66}\n# <start time> This Program is started at\t {start_time}.\n# <file time> This log file is created at\t {file_time}.\n{'#'*66}\n\n{message}"""
                self.__current_size = len(message.encode('utf-8'))
                self.__run_async_rotated_log_compression()
            if not os.path.exists(self.__root_dir):
                os.makedirs(self.__root_dir)
            if not os.path.exists(self.__log_dir):
                os.makedirs(self.__log_dir)
            if self.__isStrictLimit:
                self.__clear_files()
            with open(self.__log_file_path, 'a+', encoding='utf-8') as f:
                f.write(message)
            self.__hasWrittenFirstFile = True

    def __write_signal(self, level, message):
        if level >= LogLevel.NOTSET:
            self.__write(message)

    def __connect_single(self, log_obj: JFLogger) -> None:
        if log_obj in self.__log_group:
            return
        self.__log_group.append(log_obj)
        log_obj.signal_message.connect(self.signal_message)
        log_obj.signal_colorized.connect(self.signal_colorized)
        log_obj.signal_format.connect(self.signal_format)
        log_obj.signal_format.connect(self.__write_signal)

    def __disconnect_single(self, log_obj: JFLogger) -> None:
        if log_obj not in self.__log_group:
            return
        self.__log_group.remove(log_obj)
        log_obj.signal_message.disconnect(self.signal_message)
        log_obj.signal_colorized.disconnect(self.signal_colorized)
        log_obj.signal_format.disconnect(self.signal_format)
        log_obj.signal_format.disconnect(self.__write_signal)


class LoggerGroup(JFLoggerGroup):
    """ 
    The new LoggerGroup class is renamed to JFLoggerGroup.
    The old class name is kept for compatibility, 
    and it will be removed in the future.
    """
    pass


""" 
Example usage:

def handle_log_signal(level, message):
    print(f'{level}: {message}')

Log = Logger('Log', os.path.dirname(__file__), log_level='info')
Log.set_file_size_limit_kB(1024)
Log.set_enable_daily_split(True)
Log.set_listen_logging(level=LogLevel.INFO)
Log_1 = Logger('Log_1', os.path.dirname(__file__), log_sub_folder_name='test_folder', log_level=LogLevel.TRACE)
Log_1.set_file_size_limit_kB(1024)
Log_1.set_enable_daily_split(True)
Log.signal_format.connect(print)
Logger_group = LoggerGroup(os.path.dirname(__file__))

Log.trace('This is a trace message.')
Log.debug('This is a debug message.')
Log_1.debug('This is a debug message.')
Log.info('This is a info message.')
Log_1.warning('This is a warning message.')
Log.error('This is a error message.')
Log_1.critical('This is a critical message.')
"""
