import pprint
import queue
import sys
import os
import inspect
import re
import traceback
import logging
import threading
from datetime import datetime
import typing
import zipfile
import time
import atexit
import psutil
import multiprocessing
from DToolslib import EventSignal
from DToolslib.Color_Text import *
from ._LogEnum import LogLevel, LogHighlightType, _ColorMap, _Log_Default, _LogMessageItem
from ._Logging_Listener import _LoggingListener
from ._Compressed_Thread import _CompressThread


try:
    from PyQt5.QtCore import QThread
except:
    QThread = None

if QThread is None:
    try:
        from PyQt6.QtCore import QThread
    except:
        QThread = None

if QThread is None:
    try:
        from PySide6.QtCore import QThread
    except:
        QThread = None


def _get_current_process_name() -> str:
    """ 
    This function returns the name of the current process.
    """
    python_process_name = multiprocessing.current_process().name
    try:
        pid_int = os.getpid()
        process_obj = psutil.Process(pid_int)
        exe_name = process_obj.name()
        return f'{exe_name}({python_process_name})'
    except:
        return python_process_name


class JFLogger(object):
    """ 
    The main class of the logger.

    - Args:
        - log_name(str): The unique name of the log file.
        - root_dir(str): The root directory of the log file, default is no path then JFLogger will not write log file.
        - root_folder_name(str): The root folder name of the log file, default is 'Logs'.
        - log_folder_name(str): The subfolder name of the log file, default is '',
            if it is empty, the subfolder name will be the log name.
        - log_level(str): The log level, default is `LogLevel.INFO`.
        - enableConsoleOutput(bool): Whether to enable console output, default is True.
        - enableFileOutput(bool): Whether to enable file output, default is True.
        - **kwargs: Customize parameters used in the log message format, How to use it please refer to the example.

    - Signals:
        - signal_format: formatted log messages
        - signal_colorized: formatted log messages with color
        - signal_message: log messages without color and format

        parameter of slot function: 
            - level_str(str): `LogLevel.TRACE`, `LogLevel.DEBUG`, `LogLevel.INFO`, `LogLevel.WARNING`, `LogLevel.ERROR`, `LogLevel.CRITICAL`
            - message(str)

    - Attributes:
        - name: The name of the log
        - root_dir: The root directory of the log file
        - log_dir: The directory of the log file
        - current_log_file_path: The current log file path
        - zip_file_path: The zip file path
        - enableConsoleOutput: Whether to enable console output
        - enableFileOutput: Whether to enable file output
        - enableDailySplit: Whether to enable daily split
        - enableRuntimeZip: Whether to enable runtime zip
        - isStrictLimit: Whether to enable strict limit. If True, the log file will be deleted when the limit is reached, If false, the log file will be deleted by the startup time
        - enableQThreadtracking: Whether to enable QThread tracking
        - log_level: The log level
        - limit_single_file_size_Bytes: The limit size of a single log file
        - limit_files_count: The limit count of log files
        - limit_files_days: The limit days of log files
        - message_format: The format of the log message
        - highlight_type: The highlight type of the log message
        - exclude_functions: The functions to exclude from logging
        - exclude_classes: The classes to exclude from logging
        - exclude_modules: The modules to exclude from logging

    - methods:
        - trace(*message): Output trace information, support multiple parameters
        - debug(*message): Output debug information, support multiple parameters
        - info(*message): Output info information, support multiple parameters
        - warning(*message): Output warning information, support multiple parameters
        - error(*message): Output error information, support multiple parameters
        - critical(*message): Output critical information, support multiple parameters
        - exception(*message, level=LogLevel.ERROR): Output exception information, support multiple parameters
        - set_listen_logging(logger_name, level): Set the level of the logger to be monitored
        - remove_listen_logging(): Remove the monitored logger
        - set_exclude_funcs(funcs_list): Set the functions to be excluded
        - set_exclude_classes(classes_list): Set the classes to be excluded
        - set_exclude_modules(modules_list): Set the modules to be excluded
        - add_exclude_func(func_name): Add the functions to be excluded
        - add_exclude_class(cls_name): Add the classes to be excluded
        - add_exclude_module(module_name): Add the modules to be excluded
        - remove_exclude_func(func_name): Remove the functions to be excluded
        - remove_exclude_class(cls_name): Remove the classes to be excluded
        - remove_exclude_module(module_name): Remove the modules to be excluded
        - set_root_dir(root_dir): Set the root directory for the log files
        - set_root_folder_name(root_folder_name): Set the root folder name
        - set_log_folder_name(log_folder_name): Set the log folder name
        - set_level(log_level): Set the log level
        - set_enable_daily_split(enable): Set whether to enable daily splitting
        - set_enable_console_output(enable): Set whether to enable console output
        - set_enable_file_output(enable): Set whether to enable file output
        - set_enable_runtime_zip(enable): Set whether to enable runtime compression
        - set_enable_startup_zip(enable): Set whether to enable startup compression
        - set_file_size_limit_kB(size_limit): Set the file size limit in KB
        - set_file_count_limit(count_limit): Set the file count limit
        - set_file_days_limit(days_limit): Set the file days limit
        - set_message_format(message_format): Set the message format
        - set_highlight_type(highlight_type): Set the highlight type
        - set_enable_QThread_tracking(enable): Set whether to enable QThread tracking

    Example:
    1. Usually call:

        logger = JFLogger(log_name='test', root_dir='D:/test')

        logger.debug('debug message')
    2. About the setting of the format:

    - The default format parameters provided are:
        - `asctime` Current time
        - `processName` Process name
        - `threadName` Thread name
        - `moduleName` Module name
        - `functionName` Function name
        - `className` Class name
        - `levelName` Level name
        - `lineNum` Code line number
        - `message` Log message
        - `scriptName` python script name
        - `scriptPath` python script path
        - `consoleLine` console line with link to the code

    - You can add custom parameters in the initialization, and you can assign values to the corresponding attributes later

    logger = JFLogger(log_name='test', root_dir='D:/test', happyNewYear=False)

    logger.set_message_format('%(asctime)s-%(levelName)s -%(message)s -%(happyNewYear)s')

    logger.happyNewYear = True

    logger.debug('debug message')

    You will get: `2025-01-01 06:30:00-INFO -debug message -True`
    """
    signal_format = EventSignal(int, str)
    signal_colorized = EventSignal(int, str)
    signal_message = EventSignal(int, str)
    __instance_list__ = []
    __logger_name_list__ = []
    __log_folder_name_list__ = []

    @property
    def name(self) -> str:
        return self.__log_name

    @property
    def root_dir(self) -> str:
        return self.__root_dir

    @property
    def log_dir(self) -> str:
        return self.__log_dir

    @property
    def current_log_file_path(self) -> str:
        return self.__log_file_path

    @property
    def zip_file_path(self) -> str:
        return self.__zip_file_path

    @property
    def enableConsoleOutput(self) -> bool:
        return self.__enableConsoleOutput

    @property
    def enableFileOutput(self) -> bool:
        return self.__enableFileOutput

    @property
    def enableDailySplit(self) -> bool:
        return self.__enableDailySplit

    @property
    def enableRuntimeZip(self) -> bool:
        return self.__enableRuntimeZip

    @property
    def isStrictLimit(self) -> bool:
        return self.__isStrictLimit

    @property
    def enableQThreadtracking(self) -> bool:
        return self.__enableQThreadtracking

    @property
    def log_level(self) -> int:
        return self.__log_level

    @property
    def limit_single_file_size_Bytes(self) -> int:
        return self.__limit_single_file_size_Bytes

    @property
    def limit_files_count(self) -> int:
        return self.__limit_files_count

    @property
    def limit_files_days(self) -> int:
        return self.__limit_files_days

    @property
    def message_format(self) -> str:
        return self.__message_format

    @property
    def highlight_type(self) -> str:
        return self.__highlight_type

    @property
    def exclude_functions(self) -> list:
        return list(self.__exclude_funcs)

    @property
    def exclude_classes(self) -> list:
        return list(self.__exclude_classes)

    @property
    def exclude_modules(self) -> list:
        return list(self.__exclude_modules)

    def __new__(cls, log_name, *args, **kwargs):
        instance = super().__new__(cls)
        if log_name in cls.__logger_name_list__:
            raise ValueError(f'JFLogger "{log_name}" already exists.')
        cls.__logger_name_list__.append(log_name)
        cls.__instance_list__.append(instance)
        return instance

    def __init__(
        self,
        log_name: str,
        root_dir: str = '',
        root_folder_name: str = '',
        log_folder_name: str = '',
        log_level: typing.Union[str, int] = LogLevel.INFO,
        enableConsoleOutput: bool = True,
        enableFileOutput: bool = True,
        ** kwargs,
    ) -> None:
        self.__log_name = log_name
        self.__root_folder_name = root_folder_name if root_folder_name else _Log_Default.ROOT_FOLDER_NAME
        if not isinstance(root_dir, str):
            raise ValueError(f'<WARNING> Log root dir "{root_dir}" is not a string.')
        self.__root_dir: str = root_dir
        self.__root_path: str = os.path.join(self.__root_dir, self.__root_folder_name) if self.__root_dir else ''
        self.__isExistsPath = False
        if self.__root_dir and os.path.exists(self.__root_dir):
            self.__isExistsPath = True
        elif self.__root_dir:
            raise FileNotFoundError(f'Log root dir "{self.__root_dir}" does not exist, create it.')
        else:
            warning_text = (
                ansi_color_text('< WARNING > No File Output from', _ColorMap.LIGHTYELLOW.ANSI_TXT) +
                ansi_color_text(self.__log_name+'\n   ', _ColorMap.LIGHTYELLOW.ANSI_TXT, _ColorMap.GRAY.ANSI_BG) +
                ansi_color_text(
                    f'- No log file will be recorded because the log root path is not specified. The current root path input is "{self.__root_path}". Type: {type(self.__root_path)}', txt_color=_ColorMap.YELLOW.ANSI_TXT)
            )
            if sys.stdout:
                sys.stdout.write(warning_text)
        self.__log_folder_name = log_folder_name if isinstance(log_folder_name, str) and log_folder_name else self.__log_name
        self.__log_dir = os.path.join(self.__root_path, self.__log_folder_name)
        if self.__log_folder_name in self.__class__.__log_folder_name_list__:
            raise ValueError(f'<WARNING> Log folder name "{self.__log_folder_name}" is already in use.')
        self.__class__.__log_folder_name_list__.append(self.__log_folder_name)
        self.__log_level: LogLevel = LogLevel._normalize_log_level(log_level)
        self.__enableConsoleOutput: bool = enableConsoleOutput if isinstance(enableConsoleOutput, bool) else True
        self.__enableFileOutput: bool = enableFileOutput if isinstance(enableFileOutput, bool) else True
        self.__enableQThreadtracking: bool = False
        self.__enableContinueWithLastFile = False
        self.__last_log_file_path = ''
        self.__kwargs: dict = kwargs
        self.__init_params()
        self.__clear_files()

    def __del__(self):
        try:
            JFLogger.__instance_list__.remove(self)
        except:
            pass

        if hasattr(JFLogger, f'_{self.__class__.__name__}__log_folder_name'):
            try:
                JFLogger.__log_folder_name_list__.remove(self.__log_folder_name)
            except:
                pass

        if hasattr(JFLogger, f'_{self.__class__.__name__}__log_name'):
            try:
                JFLogger.__logger_name_list__.remove(self.__log_name)
            except:
                pass

    def __repr__(self):
        return f'{self.__class__.__name__}<"{self.__log_name}"> with level <{self.__log_level}"{self.__level_color_dict[self.__log_level].text}"> at 0x{id(self):016x}'

    def __init_params(self) -> None:
        atexit.register(self.__compress_current_old_log_end)
        self.__thread_write_log_lock = threading.Lock()
        self.__thread_compress_lock = threading.Lock()
        self.__log_file_path_last_queue = queue.Queue()
        self.__compression_thread_pool = set()
        self.__limit_single_file_size_Bytes = -1
        self.__limit_files_count = -1
        self.__limit_files_days = -1
        self.__message_format = _Log_Default.MESSAGE_FORMAT
        self.__highlight_type = LogHighlightType.NONE
        self.__dict__.update(self.__kwargs)
        self.__message_queue = queue.Queue()
        self.__enableDailySplit = False
        self.__enableRuntimeZip = False
        self.__enableStartupZip = False
        self.__isStrictLimit = False
        self.__hasWrittenFirstFile = False
        self.__isWriting = False
        self.__self_module_name: str = os.path.splitext(os.path.basename(__file__))[0]
        self.__start_time_log = datetime.now()
        self.__zip_file_path = ''
        self.__var_dict: dict = {
            'logName': _LogMessageItem('logName', font_color=_ColorMap.CYAN, highlight_type=self.__highlight_type),
            'asctime': _LogMessageItem('asctime', font_color=_ColorMap.GREEN, highlight_type=self.__highlight_type, bold=True),
            'processName': _LogMessageItem('processName', font_color=_ColorMap.YELLOW, highlight_type=self.__highlight_type),
            'threadName': _LogMessageItem('threadName', font_color=_ColorMap.YELLOW, highlight_type=self.__highlight_type),
            'moduleName': _LogMessageItem('moduleName', font_color=_ColorMap.CYAN, highlight_type=self.__highlight_type),
            'functionName': _LogMessageItem('functionName', font_color=_ColorMap.CYAN, highlight_type=self.__highlight_type),
            'className': _LogMessageItem('className', font_color=_ColorMap.CYAN, highlight_type=self.__highlight_type),
            'levelName': _LogMessageItem('levelName', font_color=_ColorMap.CYAN, highlight_type=self.__highlight_type),
            'lineNum': _LogMessageItem('lineNum', font_color=_ColorMap.CYAN, highlight_type=self.__highlight_type),
            'message': _LogMessageItem('message'),
            'scriptName': _LogMessageItem('scriptName', font_color=_ColorMap.CYAN, highlight_type=self.__highlight_type),
            'scriptPath': _LogMessageItem('scriptPath', font_color=_ColorMap.CYAN, highlight_type=self.__highlight_type),
            'consoleLine': _LogMessageItem('consoleLine', font_color=_ColorMap.RED, highlight_type=self.__highlight_type, italic=True),
        }
        for key, value in self.__kwargs.items():
            if key not in self.__var_dict:
                self.__var_dict[key] = _LogMessageItem(key, font_color=_ColorMap.CYAN)
            self.__var_dict[key].set_text(value)
        self.__exclude_funcs = set()  # To storage the function names to be ignored in __find_caller
        self.__exclude_funcs.update(self.__class__.__dict__.keys())
        self.__exclude_funcs.difference_update(dir(object))
        self.__exclude_classes: set = {
            self.__class__.__name__,
            '_LoggingListener',
            '_LogSignal',
            '_BoundSignal',
            'RootLogger',
        }
        self.__exclude_modules = set()
        # self.__exclude_modules.add(self.__self_module_name)
        self.__current_size = 0
        self.__current_day = datetime.today().date()
        self.__isNewFile = True
        self.__level_color_dict: dict = {
            LogLevel.NOTSET: _LogMessageItem('levelName', text='NOTSET', font_color=_ColorMap.LIGHTBLUE, highlight_type=self.__highlight_type),
            LogLevel.TRACE: _LogMessageItem('levelName', text='TRACE', font_color=_ColorMap.LIGHTGREEN, highlight_type=self.__highlight_type),
            LogLevel.DEBUG: _LogMessageItem('levelName', text='DEBUG', font_color=_ColorMap.BLACK, background_color=_ColorMap.LIGHTGREEN, highlight_type=self.__highlight_type),
            LogLevel.INFO: _LogMessageItem('levelName', text='INFO', font_color=_ColorMap.BLUE, highlight_type=self.__highlight_type),
            LogLevel.WARNING: _LogMessageItem('levelName', text='WARNING', font_color=_ColorMap.LIGHTYELLOW, highlight_type=self.__highlight_type, bold=True),
            LogLevel.ERROR: _LogMessageItem('levelName', text='ERROR', font_color=_ColorMap.WHITE, background_color=_ColorMap.LIGHTRED, highlight_type=self.__highlight_type, bold=True),
            LogLevel.CRITICAL: _LogMessageItem('levelName', text='CRITICAL', font_color=_ColorMap.LIGHTYELLOW, background_color=_ColorMap.RED, highlight_type=self.__highlight_type, bold=True, blink=True),
        }
        self.__log_level_translation_dict: dict = {
            LogLevel.NOTSET: LogLevel.NOTSET,
            LogLevel.TRACE: LogLevel.NOTSET,
            LogLevel.DEBUG: LogLevel.TRACE,
            LogLevel.INFO: LogLevel.DEBUG,
            LogLevel.WARNING: LogLevel.INFO,
            LogLevel.ERROR: LogLevel.WARNING,
            LogLevel.CRITICAL: LogLevel.ERROR,
            LogLevel.NOOUT: LogLevel.ERROR
        }

    def __set_log_file_path(self) -> None:
        """ Set log file path """
        # Supported {}[];'',.!~@#$%^&()_+-=
        if not self.__enableFileOutput or self.__isExistsPath is False:
            return
        if not self.__hasWrittenFirstFile:  # first time to write file
            self.__start_time_format = self.__start_time_log.strftime("%Y%m%d_%H%M%S")
            if not os.path.exists(self.__log_dir):
                os.makedirs(self.__log_dir)
            self.__log_file_path = os.path.join(self.__log_dir, f'{self.__log_name}-[{self.__start_time_format}]--0.log')
            if os.path.exists(self.__log_file_path):
                index = 1
                while True:
                    self.__log_file_path = os.path.join(self.__log_dir, f'{self.__log_name}-[{self.__start_time_format}]_{index}--0.log')
                    if not os.path.exists(self.__log_file_path):
                        break
                    index += 1
            str_list = os.path.splitext(os.path.basename(self.__log_file_path))[0].split('--')
        else:
            self.__log_file_path_last_queue.put(self.__log_file_path)
            file_name = os.path.splitext(os.path.basename(self.__log_file_path))[0]
            str_list = file_name.split('--')
            self.__log_file_path = os.path.join(self.__log_dir, f'{str_list[0]}--{int(str_list[-1]) + 1}.log')
        if not self.__zip_file_path:
            self.__zip_file_path = os.path.join(self.__log_dir, f'{str_list[0]}--Compressed.zip')

    def __setattr__(self, name: str, value) -> None:
        if hasattr(self, f'_{self.__class__.__name__}__kwargs') and name != f'_{self.__class__.__name__}__kwargs' and name in self.__kwargs:
            self.__kwargs[name] = value
            if name not in self.__var_dict:
                self.__var_dict[name] = _LogMessageItem(name, _ColorMap.CYAN)
            self.__var_dict[name].set_text(value)
        if hasattr(self, f'_{self.__class__.__name__}__kwargs') and (not name.startswith(f'_{self.__class__.__name__}__') and name not in ['__signals__', '__class_signals__'] and name not in self.__dict__):
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
        super().__setattr__(name, value)

    def __clear_files(self) -> None:
        if self.__isExistsPath is False:
            return
        if (not isinstance(self.__limit_files_count, int) and self.__limit_files_count < 0) or (not isinstance(self.__limit_files_days, int) and self.__limit_files_days <= 0):
            return
        self.__log_dir = os.path.join(self.__root_path, self.__log_folder_name)
        if not os.path.exists(self.__log_dir):
            return
        current_file_list = []
        for file in os.listdir(self.__log_dir):
            fp = os.path.join(self.__log_dir, file)
            if file.endswith('.log') and os.path.isfile(fp):
                current_file_list.append(fp)
        length_file_list = len(current_file_list)
        # clear files by count
        sorted_files = sorted(current_file_list, key=os.path.getctime)
        if (isinstance(self.__limit_files_count, int) and self.__limit_files_count >= 0) and length_file_list > self.__limit_files_count:
            sorted_files = sorted(current_file_list, key=os.path.getctime)
            for file_path in sorted_files[:length_file_list - self.__limit_files_count]:
                os.remove(file_path)
        # clear files by days
        elif isinstance(self.__limit_files_days, int) and self.__limit_files_days > 0:
            for file_path in current_file_list:
                if (datetime.today() - datetime.fromtimestamp(os.path.getctime(file_path))).days > self.__limit_files_days:
                    os.remove(file_path)
        self.__last_log_file_path = current_file_list[-1] if current_file_list else None

    def __find_caller(self) -> dict:
        """ Positioning the caller """
        # stack = inspect.stack()
        stack = inspect.currentframe()
        # caller_name = ''
        # class_name = ''
        # linenum = -1
        module_name = ''
        script_name = ''
        script_path = ''
        if self.__enableQThreadtracking and QThread is not None:
            thread_name = QThread.currentThread().objectName() or str(QThread.currentThread())
        else:
            thread_name = threading.current_thread().name
        process_name = _get_current_process_name()
        # func = None
        # for idx, fn in enumerate(stack):
        #     unprefix_variable = fn.function.lstrip('__')
        #     temp_class_name = fn.frame.f_locals.get('self', None).__class__.__name__ if 'self' in fn.frame.f_locals else ''
        #     temp_module_name = os.path.splitext(os.path.basename(fn.filename))[0]
        #     class_func_name = f'{temp_class_name}.{fn.function}'
        #     module_class_name = f'{temp_module_name}.{temp_class_name}'
        #     if (
        #         fn.function not in self.__exclude_funcs
        #         and class_func_name not in self.__exclude_funcs
        #         and f'_{self.__class__.__name__}__{unprefix_variable}' not in self.__exclude_funcs
        #         and temp_class_name not in self.__exclude_classes
        #         and module_class_name not in self.__exclude_classes
        #         and temp_module_name not in self.__exclude_modules
        #     ):  # Not in the exclusion list, but also exclude private methods in the current class
        #         caller_name = fn.function
        #         class_name = temp_class_name
        #         linenum = fn.lineno
        #         module_name = temp_module_name
        #         script_name = os.path.basename(fn.filename)
        #         script_path = fn.filename
        #         func = fn
        #         break
        # if not class_name:
        #     class_name = '<module>'
        # return {
        #     'caller': func,
        #     'caller_name': caller_name,
        #     'class_name': class_name,
        #     'line_num': linenum,
        #     'module_name': module_name,
        #     'script_name': script_name,
        #     'script_path': script_path,
        #     'thread_name': thread_name,
        #     'process_name': process_name,
        # }
        caller_frame = stack.f_back
        caller_info = None

        while caller_frame is not None:
            code = caller_frame.f_code
            function_name = code.co_name

            # Fast path: skip known logging functions immediately
            if function_name in self.__exclude_funcs:
                caller_frame = caller_frame.f_back
                continue

            # 提取类名
            self_obj = caller_frame.f_locals.get('self', None)
            temp_class_name = self_obj.__class__.__name__ if self_obj is not None else ''

            # 检查类级排除
            class_func_name = f"{temp_class_name}.{function_name}"
            if (class_func_name in self.__exclude_funcs or
                    temp_class_name in self.__exclude_classes):
                caller_frame = caller_frame.f_back
                continue

            # Compute module-related info only when needed
            filename = code.co_filename
            script_path = filename
            script_name = os.path.basename(filename)
            module_name = os.path.splitext(script_name)[0]

            # 检查模块级排除
            module_class_name = f"{module_name}.{temp_class_name}"
            if (module_class_name in self.__exclude_classes or
                    module_name in self.__exclude_modules):
                caller_frame = caller_frame.f_back
                continue

            # 检查私有方法排除
            unprefix = function_name.lstrip('__')
            private_check = f"_{self.__class__.__name__}__{unprefix}"
            if private_check in self.__exclude_funcs:
                caller_frame = caller_frame.f_back
                continue

            # Found valid caller
            caller_info = {
                'caller': caller_frame,
                'caller_name': function_name,
                'class_name': temp_class_name or '<module>',
                'line_num': caller_frame.f_lineno,
                'module_name': module_name,
                'script_name': script_name,
                'script_path': script_path,
            }
            break

            caller_frame = caller_frame.f_back

        # Fallback if no caller found
        if caller_info is None:
            caller_frame = inspect.currentframe().f_back
            code = caller_frame.f_code
            filename = code.co_filename
            caller_info = {
                'caller': caller_frame,
                'caller_name': code.co_name,
                'class_name': '<module>',
                'line_num': caller_frame.f_lineno,
                'module_name': os.path.splitext(os.path.basename(filename))[0],
                'script_name': os.path.basename(filename),
                'script_path': filename,
            }

        # Add thread/process info
        caller_info.update({
            'thread_name': thread_name,
            'process_name': process_name,
        })

        return caller_info

    def __format(self, log_level: int, *args) -> tuple:
        """ Format log message """
        msg_list = []
        for arg in args:
            if isinstance(arg, (dict, list, tuple)):
                msg_list.append(pprint.pformat(arg))
            else:
                msg_list.append(str(arg))
        msg = ' '.join(message for message in msg_list)
        caller_info = self.__find_caller()
        script_path = caller_info['script_path']
        line_num = caller_info['line_num']
        self.__var_dict['logName'].set_text(self.__log_name)
        self.__var_dict['asctime'].set_text(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        self.__var_dict['processName'].set_text(caller_info['process_name'])
        self.__var_dict['threadName'].set_text(caller_info['thread_name'])
        self.__var_dict['moduleName'].set_text(caller_info['module_name'])
        self.__var_dict['scriptName'].set_text(caller_info['script_name'])
        self.__var_dict['scriptPath'].set_text(caller_info['script_path'])
        self.__var_dict['functionName'].set_text(caller_info['caller_name'])
        self.__var_dict['className'].set_text(caller_info['class_name'])
        self.__var_dict['levelName'].set_text(log_level)
        self.__var_dict['lineNum'].set_text(caller_info['line_num'])
        self.__var_dict['message'].set_text(msg)
        self.__var_dict['consoleLine'].set_text(f'File "{script_path}", line {line_num}')
        pattern = r'%\((.*?)\)(\.\d+)?([sdfxXobeEgGc%])'
        used_var_names = re.findall(pattern, self.__message_format)
        used_messages = {}
        used_messages_console = {}
        used_messages_color = {}
        for tuple_item in used_var_names:
            name: str = tuple_item[0]
            if name not in self.__var_dict:
                continue
            item: _LogMessageItem = self.__var_dict[name]
            if name == 'levelName':
                used_messages[name] = self.__level_color_dict[item.text].text
                used_messages_color[name] = self.__level_color_dict[item.text].text_color
                used_messages_console[name] = self.__level_color_dict[item.text].text_console
                continue
            used_messages[name] = item.text
            used_messages_color[name] = item.text_color
            used_messages_console[name] = item.text_console
        text = self.__message_format % used_messages + '\n'
        text_console = self.__message_format % used_messages_console + '\n'
        text_color = self.__message_format % used_messages_color + '\n'
        if self.__highlight_type == LogHighlightType.HTML:
            text_color = text_color.replace('\n', '<br>')
        return text, text_console, text_color, msg

    def __printf(self, message: str) -> None:
        """ Print log message """
        if not self.__enableConsoleOutput:
            return
        if sys.stdout:
            sys.stdout.write(message)

    def __compress_current_old_log(self) -> None:
        """Compress the old logs currently rotated (not the historical log before startup)"""
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
                    self.__output(level=LogLevel.CRITICAL, message=f"Failed to compress log data. {last_log_file_path}: {e}")

    def __run_async_rotated_log_compression(self):
        if self.__log_file_path_last_queue.empty() or not self.__enableRuntimeZip:
            return
        zip_dir = os.path.dirname(self.__zip_file_path)
        if not os.path.exists(zip_dir):
            os.makedirs(zip_dir)
        t = _CompressThread(name=f'RotatedLogCompressThread-{self.name}', func=self.__compress_current_old_log)
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
        """ Write log to file """
        if not self.__enableFileOutput or self.__isExistsPath is False:
            return
        with self.__thread_write_log_lock:  # Avoid multi-threading creation and writing files
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
                start_time = self.__start_time_log.strftime('%Y-%m-%d %H:%M:%S')
                message = f"""{'#'*66}\n# <start time> This Program is started at\t {start_time}.\n# <file time> This log file is created at\t {file_time}.\n{'#'*66}\n\n{message}"""
                self.__current_size = len(message.encode('utf-8'))
                self.__run_async_rotated_log_compression()
            # Prevent folders from being deleted accidentally before writing
            if not os.path.exists(self.__log_dir):
                os.makedirs(self.__log_dir)
            # Clean old log files
            if self.__isStrictLimit:
                self.__clear_files()
            # Write to new log file
            with open(self.__log_file_path, 'a+', encoding='utf-8') as f:
                f.write(message)
            self.__hasWrittenFirstFile = True

    def __output(self, level, *args, **kwargs) -> tuple:
        res = self.__format(level, *args)
        text, text_console, text_color, msg = res
        self.__message_queue.put(res)
        if not self.__isWriting:
            self.__isWriting = True
            self.__write_and_broadcast()
        return text, text_console, text_color, msg

    def __write_and_broadcast(self) -> None:
        while not self.__message_queue.empty():
            text, text_console, text_color, msg = self.__message_queue.get()
            self.__write(text)
            self.__printf(text_console)
        self.__isWriting = False

    def _trace(self, *args, _sender=None, **kwargs) -> None:
        # This method is mainly used to separate the _sender parameter and prevent external misinformation.
        if self.__log_level > LogLevel.TRACE and _sender != '_LoggingListener':
            return
        text, text_console, text_color, msg = self.__output(LogLevel.TRACE, *args, **kwargs)
        self.signal_format.emit(LogLevel.TRACE, text)
        self.signal_colorized.emit(LogLevel.TRACE, text_color)
        self.signal_message.emit(LogLevel.TRACE, msg)

    def _debug(self, *args, _sender=None, **kwargs) -> None:
        # This method is mainly used to separate the _sender parameter and prevent external misinformation.
        if self.__log_level > LogLevel.DEBUG and _sender != '_LoggingListener':
            return
        text, text_console, text_color, msg = self.__output(LogLevel.DEBUG, *args, **kwargs)
        self.signal_format.emit(LogLevel.DEBUG, text)
        self.signal_colorized.emit(LogLevel.DEBUG, text_color)
        self.signal_message.emit(LogLevel.DEBUG, msg)

    def _info(self, *args, _sender=None, **kwargs) -> None:
        # This method is mainly used to separate the _sender parameter and prevent external misinformation.
        if self.__log_level > LogLevel.INFO and _sender != '_LoggingListener':
            return
        text, text_console, text_color, msg = self.__output(LogLevel.INFO, *args, **kwargs)
        self.signal_format.emit(LogLevel.INFO, text)
        self.signal_colorized.emit(LogLevel.INFO, text_color)
        self.signal_message.emit(LogLevel.INFO, msg)

    def _warning(self, *args, _sender=None, **kwargs) -> None:
        # This method is mainly used to separate the _sender parameter and prevent external misinformation.
        if self.__log_level > LogLevel.WARNING and _sender != '_LoggingListener':
            return
        text, text_console, text_color, msg = self.__output(LogLevel.WARNING, *args, **kwargs)
        self.signal_format.emit(LogLevel.WARNING, text)
        self.signal_colorized.emit(LogLevel.WARNING, text_color)
        self.signal_message.emit(LogLevel.WARNING, msg)

    def _error(self, *args, _sender=None, **kwargs) -> None:
        # This method is mainly used to separate the _sender parameter and prevent external misinformation.
        if self.__log_level > LogLevel.ERROR and _sender != '_LoggingListener':
            return
        text, text_console, text_color, msg = self.__output(LogLevel.ERROR, *args, **kwargs)
        self.signal_format.emit(LogLevel.ERROR, text)
        self.signal_colorized.emit(LogLevel.ERROR, text_color)
        self.signal_message.emit(LogLevel.ERROR, msg)

    def _critical(self, *args, _sender=None, **kwargs) -> None:
        # This method is mainly used to separate the _sender parameter and prevent external misinformation.
        if self.__log_level > LogLevel.CRITICAL and _sender != '_LoggingListener':
            return
        text, text_console, text_color, msg = self.__output(LogLevel.CRITICAL, *args, **kwargs)
        self.signal_format.emit(LogLevel.CRITICAL, text)
        self.signal_colorized.emit(LogLevel.CRITICAL, text_color)
        self.signal_message.emit(LogLevel.CRITICAL, msg)

    def trace(self, *args, **kwargs) -> None:
        self._trace(*args, **kwargs)

    def debug(self, *args, **kwargs) -> None:
        self._debug(*args, **kwargs)

    def info(self, *args, **kwargs) -> None:
        self._info(*args, **kwargs)

    def warning(self, *args, **kwargs) -> None:
        self._warning(*args, **kwargs)

    def error(self, *args, **kwargs) -> None:
        self._error(*args, **kwargs)

    def critical(self, *args, **kwargs) -> None:
        self._critical(*args, **kwargs)

    def exception(self, *args, level: str | int = LogLevel.ERROR, **kwargs) -> None:
        """
        Log an exception.

        In this method, traceback is automatically added to the log message.

        Format: `traceback_message` + `message`

        You can specify the log level of the exception message, default is ERROR.        
        """
        exception_str = traceback.format_exc()
        if exception_str == f'{type(None).__name__}: {None}\n':
            return
        exception_str += '\n'
        level = LogLevel._normalize_log_level(level)
        if level == LogLevel.TRACE:
            self.trace(exception_str, *args, **kwargs)
        elif level == LogLevel.DEBUG:
            self.debug(exception_str, *args, **kwargs)
        elif level == LogLevel.INFO:
            self.info(exception_str, *args, **kwargs)
        elif level == LogLevel.WARNING:
            self.warning(exception_str, *args, **kwargs)
        elif level == LogLevel.CRITICAL:
            self.critical(exception_str, *args, **kwargs)
        else:
            self.error(exception_str, *args, **kwargs)

    def set_listen_logging(self, logger_name: str = '', level: LogLevel = LogLevel.NOTSET) -> typing.Self:
        """ 
        Set logging listener

        -Args:
            - logger_name: The name of the logger to be listened
            - level: The level of the listener
        """
        if not (hasattr(self, f'_{self.__class__.__name__}__logging_listener_handler') and hasattr(self, f'_{self.__class__.__name__}__logging_listener')):
            self.__logging_listener_handler = _LoggingListener(self.__log_level_translation_dict[level])
            self.__logging_listener: logging.Logger = logging.getLogger(logger_name)
            self.__logging_listener_handler.signal_trace.connect(self._trace)
            self.__logging_listener_handler.signal_debug.connect(self._debug)
            self.__logging_listener_handler.signal_info.connect(self._info)
            self.__logging_listener_handler.signal_warning.connect(self._warning)
            self.__logging_listener_handler.signal_error.connect(self._error)
            self.__logging_listener_handler.signal_critical.connect(self._critical)
            self.__logging_listener.addHandler(self.__logging_listener_handler)
        else:
            self.__logging_listener_handler.set_level(self.__log_level_translation_dict[level])
        self.__logging_listener.setLevel(self.__log_level_translation_dict[level])

    def remove_listen_logging(self) -> typing.Self:
        if hasattr(self, f'_{self.__class__.__name__}__logging_listener_handler') and hasattr(self, f'_{self.__class__.__name__}__logging_listener'):
            self.__logging_listener.removeHandler(self.__logging_listener_handler)
        return self

    def set_exclude_funcs(self, funcs_list: list) -> typing.Self:
        """ 
        Set the functions to be excluded

        - Args:
            - funcs_list (list[str]): A list of function names (as strings) to exclude.
        """
        self.__exclude_funcs.clear()
        self.__exclude_funcs.update(self.__class__.__dict__.keys())
        self.__exclude_funcs.difference_update(dir(object))
        for item in funcs_list:
            self.__exclude_funcs.add(item)
        return self

    def set_exclude_classes(self, classes_list: list) -> typing.Self:
        """ 
        Set the classes to be excluded

        - Args:
            - classes_list(list[str]): A list of class names (as strings) to exclude.
        """
        self.__exclude_classes: set = {
            self.__class__.__name__,
            '_LoggingListener',
            '_LogSignal',
            '_BoundSignal',
            'RootLogger',
        }
        for item in classes_list:
            self.__exclude_classes.add(item)
        return self

    def set_exclude_modules(self, modules_list: list) -> typing.Self:
        """ 
        Set the modules to be excluded

        - Args:
            - modules_list(list[str]): A list of module names (as strings) to exclude.
        """
        self.__exclude_modules.clear()
        # self.__exclude_modules.add(self.__self_module_name)
        for item in modules_list:
            self.__exclude_modules.add(item)
        return self

    def add_exclude_func(self, func_name: str) -> typing.Self:
        """ 
        Add the function to be excluded

        - Args:
            - func_name(str): The function name (as strings) to exclude.
        """
        self.__exclude_funcs.add(func_name)
        return self

    def add_exclude_class(self, cls_name: str) -> typing.Self:
        """ 
        Add the class to be excluded

        - Args:
            - cls_name(str): The class name (as strings) to exclude.
        """
        self.__exclude_classes.add(cls_name)
        return self

    def add_exclude_module(self, module_name: str) -> typing.Self:
        """ 
        Add the module to be excluded

        - Args:
            - module_name(str): The module name (as strings) to exclude.
        """
        self.__exclude_modules.add(module_name)
        return self

    def remove_exclude_func(self, func_name: str) -> typing.Self:
        """ 
        Remove the function to be excluded

        - Args:
            - func_name(str): The function name (as strings) to exclude
        """
        self.__exclude_funcs.discard(func_name)
        return self

    def remove_exclude_class(self, cls_name: str) -> typing.Self:
        """ 
        Remove the class to be excluded

        - Args:
            - cls_name(str): The class name (as strings) to exclude
        """
        self.__exclude_classes.discard(cls_name)
        return self

    def remove_exclude_module(self, module_name: str) -> typing.Self:
        """ 
        Remove the module to be excluded

        - Args:
            - module_name(str): The module name (as strings) to exclude
        """
        self.__exclude_modules.discard(module_name)
        return self

    def set_root_dir(self, root_dir: str) -> typing.Self:
        """ 
        Set the root directory for the log files

        - Args:
            - log_dir(str): log root dir path
        """
        self.__root_dir = root_dir
        self.__root_path: str = os.path.join(self.__root_dir, self.__root_folder_name) if self.__root_dir else ''
        self.__log_dir = os.path.join(self.__root_path, self.__log_folder_name)
        if self.__root_dir and os.path.exists(self.__root_dir):
            self.__isExistsPath = True
        else:
            self.__isExistsPath = False
        return self

    def set_root_folder_name(self, root_folder_name: str) -> typing.Self:
        """ 
        Set log root folder name

        - Args:
            - root_folder_name(str): log root folder name
        """
        if not root_folder_name:
            self.__root_folder_name = _Log_Default.ROOT_FOLDER_NAME
        else:
            self.__root_folder_name = root_folder_name
        self.__root_path: str = os.path.join(self.__root_dir, self.__root_folder_name) if self.__root_dir else ''
        self.__log_dir = os.path.join(self.__root_path, self.__log_folder_name)
        return self

    def set_log_folder_name(self, log_folder_name: str) -> typing.Self:
        """ 
        Set log folder name

        - Args:
            - log_folder_name(str): log folder name
        """
        if log_folder_name in _Log_Default.LIST_RESERVE_NAME:
            warning_text = (
                ansi_color_text(f'< WARNING > {log_folder_name} is a reserved name. Log folder name will set to {self.__log_name}', _ColorMap.LIGHTYELLOW.ANSI_TXT))
            if sys.stdout:
                sys.stdout.write(warning_text)
            self.__log_folder_name: str = self.__log_name
        elif not log_folder_name:
            self.__log_folder_name: str = self.__log_name
        else:
            self.__log_folder_name: str = log_folder_name
        self.__log_dir: str = os.path.join(self.__root_path, self.__log_folder_name)
        return self

    def set_level(self, log_level: LogLevel) -> typing.Self:
        """ 
        Set log level

        - Args:
            - log_level(LogLevel): log level
        """
        self.__log_level = LogLevel._normalize_log_level(log_level)
        return self

    def set_enable_daily_split(self, enable: bool) -> typing.Self:
        """ 
        Set whether to enable daily split log

        - Args:
            - enable(bool): whether to enable daily split log
        """
        self.__enableDailySplit = enable
        return self

    def set_enable_console_output(self, enable: bool) -> typing.Self:
        """ 
        Set whether to enable console output

        - Args:
            - enable(bool): Whether to enable console output
        """
        self.__enableConsoleOutput = enable
        return self

    def set_enable_file_output(self, enable: bool) -> typing.Self:
        """ 
        Set whether to enable file output

        - Args:
            - enable(bool): Whether to enable file output
        """
        self.__enableFileOutput = enable
        return self

    def set_enable_runtime_zip(self, enable: bool) -> typing.Self:
        """ 
        Set whether to compress log files at runtime

        - Args:
            - enable(bool): Whether to compress log files at runtime
        """
        self.__enableRuntimeZip: bool = enable
        return self

    # def set_enable_startup_zip(self, enable: bool) -> typing.Self:
    #     """
    #     Set whether to compress log files before running

    #     - Args:
    #       - enable(bool): Whether to compress log files before running
    #     """
    #     self.__enableStartupZip = enable
    #     return self

    def set_file_size_limit_kB(self, size_limit: typing.Union[int, float]) -> typing.Self:
        """ 
        Set a single log file size limit

        - Args:
            - size_limit(int | float): Single log file size limit, unit is KB
        """
        if not isinstance(size_limit, (int, float)):
            raise TypeError("size_limit must be int")
        self.__limit_single_file_size_Bytes: typing.Union[int, float] = size_limit * 1000
        return self

    def set_file_count_limit(self, count_limit: int, isStict: bool = False) -> typing.Self:
        """ 
        Set the limit on the number of log files in the folder

        - Args:
            - count_limit(int): Limit number of log files in folders
        """
        if not isinstance(count_limit, int):
            raise TypeError("count_limit must be int")
        if isStict:
            self.__isStrictLimit = True
        else:
            self.__isStrictLimit = False
        self.__limit_files_count: int = count_limit
        self.__clear_files()
        return self

    def set_file_days_limit(self, days_limit: int, isStict: bool = False) -> typing.Self:
        """ 
        Set the limit on the number of days of log files in the folder

        - Args:
            - days_limit(int): Day limit for log files in folders
        """
        if not isinstance(days_limit, int):
            raise TypeError("days_limit must be int")
        if isStict:
            self.__isStrictLimit = True
        else:
            self.__isStrictLimit = False
        self.__limit_files_days: int = days_limit
        self.__clear_files()
        return self

    def set_enable_continue_with_last_file(self, enable: bool) -> typing.Self:
        """ 
        Set whether to continue writing to the last log file

        - Args:
            - enable(bool): Whether to continue writing to the last log file
        """
        self.__enableContinueWithLastFile = enable
        if self.__enableContinueWithLastFile and self.__last_log_file_path:
            self.__log_file_path = self.__last_log_file_path
            self.__log_dir = os.path.dirname(self.__log_file_path)
            self.__root_path: str = os.path.dirname(self.__log_dir)
            self.__log_folder_name: str = os.path.basename(self.__log_dir)
            self.__hasWrittenFirstFile = True
            self.__isNewFile = False
        return self

    def set_message_format(self, message_format: str) -> typing.Self:
        """ 
        Set log message format

        - Args:
            - message_format(str): Log message format

        The default format parameters provided are:
        - `asctime` Current time
        - `threadName` Thread name
        - `moduleName` Module name
        - `functionName` Function name
        - `className` Class name
        - `levelName` Level name
        - `lineNum` Code line number
        - `message` Log message
        - `scriptName` python script name
        - `scriptPath` python script path
        - `consoleLine` console line with link to the code

        You can add custom parameters in the initialization, and you can assign values to the corresponding attributes later

        logger = JFLogger(log_name='test', root_dir='D:/test', happyNewYear=False)

        logger.set_message_format('%(asctime)s-%(levelName)s -%(message)s -%(happyNewYear)s')

        logger.happyNewYear = True

        logger.debug('debug message')

        You will get: `2025-01-01 06:30:00-INFO -debug message -True`

        """
        if not isinstance(message_format, str):
            raise TypeError("message_format must be str")
        if not message_format:
            self.__message_format = _Log_Default.MESSAGE_FORMAT
        else:
            self.__message_format: str = message_format
        return self

    def set_highlight_type(self, highlight_type: LogHighlightType) -> typing.Self:
        """ 
        Set log message highlighting type

        - Args:
            - highlight_type(LogHighlightType): Log message highlighting type
        """
        self.__highlight_type: LogHighlightType = highlight_type
        for item in self.__var_dict.values():
            item: _LogMessageItem
            item.set_highlight_type(highlight_type)
        return self

    def set_enable_QThread_tracking(self, enable: bool) -> typing.Self:
        """ 
        Set whether to use QThread.objectName() as the thread name for logging or tracking

        - Args:
            - enable(bool): If True, use QThread.objectName() to represent the thread name.
        """
        self.__enableQThreadtracking = enable
        return self


class Logger(JFLogger):
    """ 
    The new Logger class is renamed to JFLogger.
    The old class name is kept for compatibility, 
    and it will be removed in the future.
    """
    pass


""" 
Example usage:

import time

def handle_log_signal(level, message):
    print(f'{level}: {message}')

Log = JFLogger('Log', os.path.dirname(__file__), log_level='info')
Log.set_file_size_limit_kB(1024)
Log.set_enable_daily_split(True)
Log.set_listen_logging(level=LogLevel.INFO)
Log_1 = JFLogger('Log_1', os.path.dirname(__file__), log_folder_name='test_folder', log_level=LogLevel.TRACE)
Log_1.set_file_size_limit_kB(1024)
Log_1.set_enable_daily_split(True)
Log.signal_format.connect(handle_log_signal)
logging.debug('hello world from logging debug')  # logging 跟踪示例
logging.info('hello world from logging info')
logging.error("This is a error message from logging.")
logging.warning("This is a warning message from logging.")
logging.critical("This is a critical message from logging.")
Log.trace('This is a trace message.')
Log.debug('This is a debug message.')
for i in range(100):
    Log.info(f'This is a info message -- {i}.'*100000)
time.sleep(1)

Log_1.debug('This is a debug message.')
Log.info('This is a info message.')
Log_1.warning('This is a warning message.')
Log.error('This is a error message.')
Log_1.critical('This is a critical message.')
"""
