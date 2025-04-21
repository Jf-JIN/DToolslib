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


def get_current_process_name() -> str:
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


class _EnumBaseMeta(type):
    """ EnumBaseMeta is a metaclass for creating enumerations. """
    def __new__(mcs, name, bases, dct: dict):
        if len(bases) == 0:
            return super().__new__(mcs, name, bases, dct)
        dct['_members_'] = {}
        members = {key: value for key, value in dct.items() if not key.startswith('__')}
        cls = super().__new__(mcs, name, bases, dct)
        cls._members_['isAllowedSetValue'] = True
        for key, value in members.items():
            if key != 'isAllowedSetValue' or key != '_members_':
                cls._members_[key] = value
                setattr(cls, key, value)
        cls._members_['isAllowedSetValue'] = False
        return cls

    def __setattr__(cls, key, value) -> None:
        if key in cls._members_ and not cls._members_['isAllowedSetValue']:
            raise AttributeError(f'Disable external modification of enumeration items\t< {key} > = {cls._members_[key]}')
        super().__setattr__(key, value)

    def __contains__(self, item) -> bool:
        return item in self._members_.keys()


class _EnumBase(metaclass=_EnumBaseMeta):
    """ 
    _EnumBase is a base class for enumeration classes. 

    This class overrides the `in` operator so that it checks 
    whether a given key is the name of a defined enumeration member, 
    rather than its value.

    The class method `values` returns a list of all defined enumeration members.
    """
    @classmethod
    def values(cls):
        return cls._members_.values()


class _ColorMapItem(object):
    """ 
    This class represents a color map item, which contains the name. 
    The ANSI_TXT and ANSI_BG attributes are used to represent the color in ANSI format,
    and the HEX attribute is used to represent the color in hexadecimal format.
    """

    def __init__(self, name, ansi_txt, ansi_bg, hex):
        self.name = name
        self.ANSI_TXT = ansi_txt
        self.ANSI_BG = ansi_bg
        self.HEX = hex

    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise AttributeError(f'Disable external modification of enumeration items\t< {name} > = {self.__dict__[name]}')
        super().__setattr__(name, value)


class _Log_Default(_EnumBase):
    """ This class represents the default log level enumeration. """
    GROUP_FOLDER_NAME = '#Global_Log'
    HISTORY_FOLDER_NAME = '#History_Log'
    LIST_RESERVE_NAME = [GROUP_FOLDER_NAME, HISTORY_FOLDER_NAME]
    ROOT_FOLDER_NAME = 'Logs'

    # MESSAGE_FORMAT =  '%(consoleLine)s\n[%(asctime)s] [log: %(logName)s] [module: %(moduleName)s] [class: %(className)s] [function: %(functionName)s] [line: %(lineNum)s]- %(levelName)s\n%(message)s\n'

    # MESSAGE_FORMAT = '%(consoleLine)s\n[%(asctime)s] [log: %(logName)s] [thread: %(threadName)s] [%(moduleName)s::%(className)s.%(functionName)s] [line: %(lineNum)s] - %(levelName)s\n%(message)s\n'

    MESSAGE_FORMAT = '%(consoleLine)s\n[%(asctime)s] [%(logName)s] [ %(processName)s | %(threadName)s | %(moduleName)s::%(className)s.%(functionName)s] - %(levelName)s\n%(message)s\n'


class _ColorMap(_EnumBase):
    """ This class represents the color map enumeration. """
    BLACK = _ColorMapItem('BLACK', '30', '40', '#010101')
    RED = _ColorMapItem('RED', '31', '41', '#DE382B')
    GREEN = _ColorMapItem('GREEN', '32', '42', '#39B54A')
    YELLOW = _ColorMapItem('YELLOW', '33', '43', '#FFC706')
    BLUE = _ColorMapItem('BLUE', '34', '44', '#006FB8')
    PINK = _ColorMapItem('PINK', '35', '45', '#762671')
    CYAN = _ColorMapItem('CYAN', '36', '46', '#2CB5E9')
    WHITE = _ColorMapItem('WHITE', '37', '47', '#CCCCCC')
    GRAY = _ColorMapItem('GRAY', '90', '100', '#808080')
    LIGHTRED = _ColorMapItem('LIGHTRED', '91', '101', '#FF0000')
    LIGHTGREEN = _ColorMapItem('LIGHTGREEN', '92', '102', '#00FF00')
    LIGHTYELLOW = _ColorMapItem('LIGHTYELLOW', '93', '103', '#FFFF00')
    LIGHTBLUE = _ColorMapItem('LIGHTBLUE', '94', '104', '#0000FF')
    LIGHTPINK = _ColorMapItem('LIGHTPINK', '95', '105', '#FF00FF')
    LIGHTCYAN = _ColorMapItem('LIGHTCYAN', '96', '106', '#00FFFF')
    LIGHTWHITE = _ColorMapItem('LIGHTWHITE', '97', '107', '#FFFFFF')

    @staticmethod
    def asni_ct(
        text: str,
        txt_color: typing.Union[str, None] = None,
        bg_color: typing.Union[str, None] = None,
        dim: bool = False,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        blink: bool = False,
        *args, **kwargs
    ) -> str:
        """
        Generates ANSI escape sequences for terminal control.

        - Args:
            - text (str): The text to be escaped.
            - txt_color (str, optional): The text color. Defaults to None.
            - bg_color (str, optional): The background color. Defaults to None.
            - dim (bool, optional): Whether it is a dim color. Defaults to False.
            - bold (bool, optional): Whether it is a bold color. Defaults to False.
            - italic (bool, optional): Whether it is an italic color. Defaults to False.
            - underline (bool, optional): Whether it is an underline color. Defaults to False.
            - blink (bool, optional): Whether it is a blink color. Defaults to False.

        - Returns:
            - str: The escaped text.
        """
        style_list = []
        style_list.append('1') if bold else ''  # 粗体
        style_list.append('2') if dim else ''  # 暗色
        style_list.append('3') if italic else ''  # 斜体
        style_list.append('4') if underline else ''  # 下划线
        style_list.append('5') if blink else ''  # 闪烁
        style_list.append(getattr(getattr(_ColorMap, txt_color), 'ANSI_TXT')) if txt_color in _ColorMap else ''  # 字体颜色
        style_list.append(getattr(getattr(_ColorMap, bg_color), 'ANSI_BG')) if bg_color in _ColorMap else ''  # 背景颜色
        style_str = ';'.join(item for item in style_list if item)
        return f'\x1B[{style_str}m{text}\x1B[0m'

    @staticmethod
    def html_ct(
        text: str,
        txt_color: typing.Union[str, None] = None,
        bg_color: typing.Union[str, None] = None,
        dim: bool = False,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        blink: bool = False,
        *args, **kwargs
    ) -> str:
        """
        Generates an HTML color tag for the given text and style options.

        - Args:
            - text: The text to be styled.
            - txt_color: The text color.
            - bg_color: The background color.
            - dim: Whether the text should be dimmed.
            - bold: Whether the text should be bold.
            - italic: Whether the text should be italic.
            - underline: Whether the text should be underlined.
            - blink: Whether the text should be blinking.

        - Returns:
            - str: The HTML color tag for the given text and style options.
        """
        style_list = []
        style_list.append('color: '+getattr(getattr(_ColorMap, txt_color), 'HEX')) if txt_color in _ColorMap else ''
        style_list.append('background-color: '+getattr(getattr(_ColorMap, bg_color), 'HEX')) if bg_color in _ColorMap else ''
        style_list.append('font-weight: bold') if bold else ''
        style_list.append('font-style: italic') if italic else ''
        style_list.append('text-decoration: underline') if underline else ''
        style_list.append('opacity: 0.7;animation: blink 1s step-end infinite') if blink else ''
        style_str = ';'.join(item for item in style_list if item)+';'
        output_text = (f'<span style="{style_str}">{text}</span>').replace('\n', '<br>')
        pre_blick_text = '<style > @keyframes blink{50% {opacity: 50;}}</style>'
        output_text = pre_blick_text + output_text if blink else output_text
        return output_text


class LogLevel(_EnumBase):
    """ Log level enumeration class """
    NOTSET = 0
    TRACE = 10
    DEBUG = 20
    INFO = 30
    WARNING = 40
    ERROR = 50
    CRITICAL = 60
    NOOUT = 70

    Notset = NOTSET
    Trace = TRACE
    Debug = DEBUG
    Info = INFO
    Warning = WARNING
    Error = ERROR
    Critical = CRITICAL
    Noout = NOOUT

    @staticmethod
    def _normalize_log_level(log_level: typing.Union[str, int, 'LogLevel']) -> 'LogLevel':
        """ Normalize the log level to LogLevel enum """
        normalized_log_level = LogLevel.INFO
        if isinstance(log_level, str):
            if log_level.upper() in LogLevel:
                normalized_log_level = getattr(LogLevel, log_level.upper())
            else:
                raise ValueError(f'<ERROR> Log level "{log_level}" is not a valid log level.')
        elif isinstance(log_level, (int, float)):
            normalized_log_level = abs(log_level // 10 * 10)
        else:
            raise ValueError(f'<ERROR> Log level "{log_level}" is not a valid log level. It should be a string or a number.')
        return normalized_log_level


class LogHighlightType(_EnumBase):
    """ Highlight type enumeration class """
    ASNI = 'ASNI'
    HTML = 'HTML'
    NONE = None


class _BoundSignal:
    __name__: str = 'LogSignal'
    __qualname__: str = 'LogSignal'

    def __init__(self, types, owner, name, isClassSignal=False):
        if all([isinstance(typ, (type, tuple, typing.TypeVar)) for typ in types]):
            self.__types = types
        else:
            raise TypeError('types must be a tuple of types')
        self.__owner = owner
        self.__name = name
        self.__isClassSignal: bool = isClassSignal
        self.__slots = []

    def connect(self, slot):
        if callable(slot):
            if slot not in self.__slots:
                self.__slots.append(slot)
        elif isinstance(slot, _BoundSignal):
            self.__slots.append(slot.emit)
        else:
            raise ValueError('Slot must be callable')

    def disconnect(self, slot):
        if isinstance(slot, _BoundSignal):
            slot = slot.emit
        if slot in self.__slots:
            self.__slots.remove(slot)

    def emit(self, *args, **kwargs):
        required_types = self.__types
        required_types_count = len(self.__types)
        args_count = len(args)
        if required_types_count != args_count:
            raise TypeError(f'LogSignal "{self.__name}" requires {required_types_count} argument{"s" if required_types_count>1 else ""}, but {args_count} given.')
        for arg, (idx, required_type) in zip(args, enumerate(required_types)):
            if isinstance(required_type, typing.TypeVar):
                continue
            if not isinstance(arg, required_type):
                required_name = required_type.__name__
                actual_name = type(arg).__name__
                raise TypeError(f'LogSignal "{self.__name} {idx+1}th argument requires "{required_name}", got "{actual_name}" instead.')
        slots = self.__slots
        for slot in slots:
            slot(*args, **kwargs)

    def __str__(self) -> str:
        owner_repr = (
            f"class {self.__owner.__name__}"
            if self.__isClassSignal
            else f"{self.__owner.__class__.__name__} object"
        )
        return f'<Signal LogSignal(slots: {self.__name} of {owner_repr} at 0x{id(self.__owner):016X}>'

    def __repr__(self) -> str:
        return f"\n{self.__str__()}\n    - slots({len(self.__slots)}):{str(self.__slots).replace('_BoundSignal', 'LogSignal')}\n"

    def __del__(self) -> None:
        self.__slots.clear()


class _LogSignal:
    __qualname__: str = 'LogSignal'

    def __init__(self, *types, level='instance'):
        self.types = types
        self.__level = level

    def __get__(self, instance, instance_type) -> _BoundSignal:
        if instance is None:
            return self
        else:
            if self.__level == 'class':
                return self.__handle_class_signal(instance_type)
            else:
                return self.__handle_instance_signal(instance)

    def __set__(self, instance, value):
        raise AttributeError('LogSignal is read-only, cannot be set')

    def __set_name__(self, instance, name):
        self.__name = name

    def __handle_class_signal(self, instance_type) -> _BoundSignal:
        if not hasattr(instance_type, '__class_signals__'):
            instance_type.__class_signals__ = {}
        if self not in instance_type.__class_signals__:
            instance_type.__class_signals__[self] = _BoundSignal(
                self.types,
                instance_type,
                self.__name,
                isClassSignal=True
            )
        return instance_type.__class_signals__[self]

    def __handle_instance_signal(self, instance) -> _BoundSignal:
        if not hasattr(instance, '__signals__'):
            instance.__signals__ = {}
        if self not in instance.__signals__:
            instance.__signals__[self] = _BoundSignal(
                self.types,
                instance,
                self.__name
            )
        return instance.__signals__[self]


class _LoggingListener(logging.Handler):
    """ This class is used to listen to logging events and emit them as signals. """
    signal_trace = _LogSignal(str)
    signal_debug = _LogSignal(str)
    signal_info = _LogSignal(str)
    signal_warning = _LogSignal(str)
    signal_error = _LogSignal(str)
    signal_critical = _LogSignal(str)

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


class _LogMessageItem(object):
    """ This class is used to store the log message item. """

    def __init__(self, title, text='', font_color=None, background_color=None, dim=False, bold=False, italic=False, underline=False, blink=False, highlight_type=None) -> None:
        self.__title = title
        self.__color_font = font_color
        self.__color_background = background_color
        self.__dim = dim
        self.__bold = bold
        self.__italic = italic
        self.__underline = underline
        self.__blink = blink
        self.__highlight_type = highlight_type
        self.__text = text
        self.__text_color = ''
        self.__text_console = ''
        if self.__text:
            self.set_text(self.__text)

    @property
    def title(self) -> str:
        return self.__title

    @property
    def text(self) -> str:
        return self.__text

    @property
    def text_color(self) -> str:
        return self.__text_color

    @property
    def text_console(self) -> str:
        return self.__text_console

    def set_text(self, text) -> None:
        self.__text = text
        self.__text_color = self.__colorize_text(self.__text, self.__color_font, self.__color_background, self.__dim, self.__bold, self.__italic, self.__underline, self.__blink)
        self.__text_console = _ColorMap.asni_ct(text, self.__color_font, self.__color_background, self.__dim, self.__bold, self.__italic, self.__underline, self.__blink)

    def __colorize_text(self, text: str, *args, highlight_type=None, **kwargs) -> str:
        if highlight_type is None:
            highlight_type = self.__highlight_type
            if highlight_type is None:
                return text
        if highlight_type == LogHighlightType.ASNI:
            return _ColorMap.asni_ct(text, *args, **kwargs)
        elif highlight_type == LogHighlightType.HTML:
            return _ColorMap.html_ct(text, *args, **kwargs)
        return text

    def set_highlight_type(self, highlight_type: LogHighlightType) -> None:
        self.__highlight_type: LogHighlightType = highlight_type


SELF_COMPRESSTHREAD = typing.TypeVar('SELF_COMPRESSTHREAD', bound='CompressThread')


class CompressThread(threading.Thread):
    """ This class is used to compress the log file in the background. """
    finished = _LogSignal(SELF_COMPRESSTHREAD)

    def __init__(self, name, func, *args, **kwargs):
        super().__init__(name=name, target=func, daemon=True, args=args, kwargs=kwargs)
        self.__func = func
        self.__args = args
        self.__kwargs = kwargs

    def run(self):
        self.__func(*self.__args, **self.__kwargs)
        self.finished.emit(self)


SELF_LOGGER = typing.TypeVar('SELF_LOGGER', bound='JFLogger')
SELF_LOGGERGROUP = typing.TypeVar('SELF_LOGGERGROUP', bound='JFLoggerGroup')


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

    -Signals:
        - Explain:
            - xxx: formatted log messages
            - xxx_color: formatted log messages with color
            - xxx_console: formatted log messages for console
            - xxx_message: log messages without color and format
        - Signal for `all` log messages:
            - `signal_all` `signal_all_color` `signal_all_console` `signal_all_message`
        - Signal for `trace` level messages:
            - `signal_trace` `signal_trace_color` `signal_trace_console` `signal_trace_message`
        - Signal for `debug` level messages:
            - `signal_debug` `signal_debug_color` `signal_debug_console` `signal_debug_message`
        - Signal for `info` level messages:
            - `signal_info` `signal_info_color` `signal_info_console` `signal_info_message`
        - Signal for `warning` level messages:
            - `signal_warning` `signal_warning_color` `signal_warning_console` `signal_warning_message`
        - Signal for `error` level messages:
            - `signal_error` `signal_error_color` `signal_error_console` `signal_error_message`
        - Signal for `critical` level messages:
            - `signal_critical` `signal_critical_color` `signal_critical_console` `signal_critical_message`

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
    signal_all = _LogSignal(str)
    signal_all_color = _LogSignal(str)
    signal_all_console = _LogSignal(str)
    signal_all_message = _LogSignal(str)
    signal_trace = _LogSignal(str)
    signal_trace_color = _LogSignal(str)
    signal_trace_console = _LogSignal(str)
    signal_trace_message = _LogSignal(str)
    signal_debug = _LogSignal(str)
    signal_debug_color = _LogSignal(str)
    signal_debug_console = _LogSignal(str)
    signal_debug_message = _LogSignal(str)
    signal_info = _LogSignal(str)
    signal_info_color = _LogSignal(str)
    signal_info_console = _LogSignal(str)
    signal_info_message = _LogSignal(str)
    signal_warning = _LogSignal(str)
    signal_warning_color = _LogSignal(str)
    signal_warning_console = _LogSignal(str)
    signal_warning_message = _LogSignal(str)
    signal_error = _LogSignal(str)
    signal_error_color = _LogSignal(str)
    signal_error_console = _LogSignal(str)
    signal_error_message = _LogSignal(str)
    signal_critical = _LogSignal(str)
    signal_critical_color = _LogSignal(str)
    signal_critical_console = _LogSignal(str)
    signal_critical_message = _LogSignal(str)
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
                _ColorMap.asni_ct('< WARNING > No File Output from', _ColorMap.LIGHTYELLOW.ANSI_TXT) +
                _ColorMap.asni_ct(self.__log_name+'\n   ', _ColorMap.LIGHTYELLOW.ANSI_TXT, _ColorMap.GRAY.ANSI_BG) +
                _ColorMap.asni_ct(
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
            'logName': _LogMessageItem('logName', font_color=_ColorMap.CYAN.name, highlight_type=self.__highlight_type),
            'asctime': _LogMessageItem('asctime', font_color=_ColorMap.GREEN.name, highlight_type=self.__highlight_type, bold=True),
            'processName': _LogMessageItem('processName', font_color=_ColorMap.YELLOW.name, highlight_type=self.__highlight_type),
            'threadName': _LogMessageItem('threadName', font_color=_ColorMap.YELLOW.name, highlight_type=self.__highlight_type),
            'moduleName': _LogMessageItem('moduleName', font_color=_ColorMap.CYAN.name, highlight_type=self.__highlight_type),
            'functionName': _LogMessageItem('functionName', font_color=_ColorMap.CYAN.name, highlight_type=self.__highlight_type),
            'className': _LogMessageItem('className', font_color=_ColorMap.CYAN.name, highlight_type=self.__highlight_type),
            'levelName': _LogMessageItem('levelName', font_color=_ColorMap.CYAN.name, highlight_type=self.__highlight_type),
            'lineNum': _LogMessageItem('lineNum', font_color=_ColorMap.CYAN.name, highlight_type=self.__highlight_type),
            'message': _LogMessageItem('message'),
            'scriptName': _LogMessageItem('scriptName', font_color=_ColorMap.CYAN.name, highlight_type=self.__highlight_type),
            'scriptPath': _LogMessageItem('scriptPath', font_color=_ColorMap.CYAN.name, highlight_type=self.__highlight_type),
            'consoleLine': _LogMessageItem('consoleLine', font_color=_ColorMap.RED.name, highlight_type=self.__highlight_type, italic=True),
        }
        for key, value in self.__kwargs.items():
            if key not in self.__var_dict:
                self.__var_dict[key] = _LogMessageItem(key, font_color=_ColorMap.CYAN.name)
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
            LogLevel.NOTSET: _LogMessageItem('levelName', text='NOTSET', font_color=_ColorMap.LIGHTBLUE.name, highlight_type=self.__highlight_type),
            LogLevel.TRACE: _LogMessageItem('levelName', text='TRACE', font_color=_ColorMap.LIGHTGREEN.name, highlight_type=self.__highlight_type),
            LogLevel.DEBUG: _LogMessageItem('levelName', text='DEBUG', font_color=_ColorMap.BLACK.name, background_color=_ColorMap.LIGHTGREEN.name, highlight_type=self.__highlight_type),
            LogLevel.INFO: _LogMessageItem('levelName', text='INFO', font_color=_ColorMap.BLUE.name, highlight_type=self.__highlight_type),
            LogLevel.WARNING: _LogMessageItem('levelName', text='WARNING', font_color=_ColorMap.LIGHTYELLOW.name, highlight_type=self.__highlight_type, bold=True),
            LogLevel.ERROR: _LogMessageItem('levelName', text='ERROR', font_color=_ColorMap.WHITE.name, background_color=_ColorMap.LIGHTRED.name, highlight_type=self.__highlight_type, bold=True),
            LogLevel.CRITICAL: _LogMessageItem('levelName', text='CRITICAL', font_color=_ColorMap.LIGHTYELLOW.name, background_color=_ColorMap.RED.name, highlight_type=self.__highlight_type, bold=True, blink=True),
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
                self.__var_dict[name] = _LogMessageItem(name, _ColorMap.CYAN.name)
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
        if (isinstance(self.__limit_files_count, int) and self.__limit_files_count >= 0) and length_file_list > self.__limit_files_count:
            sorted_files = sorted(current_file_list, key=os.path.getctime)
            for file_path in sorted_files[:length_file_list - self.__limit_files_count]:
                os.remove(file_path)
        # clear files by days
        elif isinstance(self.__limit_files_days, int) and self.__limit_files_days > 0:
            for file_path in current_file_list:
                if (datetime.today() - datetime.fromtimestamp(os.path.getctime(file_path))).days > self.__limit_files_days:
                    os.remove(file_path)

    def __find_caller(self) -> dict:
        """ Positioning the caller """
        stack = inspect.stack()
        caller_name = ''
        class_name = ''
        linenum = -1
        module_name = ''
        script_name = ''
        script_path = ''
        if self.__enableQThreadtracking and QThread is not None:
            thread_name = QThread.currentThread().objectName() or str(QThread.currentThread())
        else:
            thread_name = threading.current_thread().name
        process_name = get_current_process_name()
        func = None
        for idx, fn in enumerate(stack):
            unprefix_variable = fn.function.lstrip('__')
            temp_class_name = fn.frame.f_locals.get('self', None).__class__.__name__ if 'self' in fn.frame.f_locals else ''
            temp_module_name = os.path.splitext(os.path.basename(fn.filename))[0]
            class_func_name = f'{temp_class_name}.{fn.function}'
            module_class_name = f'{temp_module_name}.{temp_class_name}'
            if (
                fn.function not in self.__exclude_funcs
                and class_func_name not in self.__exclude_funcs
                and f'_{self.__class__.__name__}__{unprefix_variable}' not in self.__exclude_funcs
                and temp_class_name not in self.__exclude_classes
                and module_class_name not in self.__exclude_classes
                and temp_module_name not in self.__exclude_modules
            ):  # Not in the exclusion list, but also exclude private methods in the current class
                caller_name = fn.function
                class_name = temp_class_name
                linenum = fn.lineno
                module_name = temp_module_name
                script_name = os.path.basename(fn.filename)
                script_path = fn.filename
                func = fn
                break
        if not class_name:
            class_name = '<module>'
        return {
            'caller': func,
            'caller_name': caller_name,
            'class_name': class_name,
            'line_num': linenum,
            'module_name': module_name,
            'script_name': script_name,
            'script_path': script_path,
            'thread_name': thread_name,
            'process_name': process_name,
        }

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
        t = CompressThread(name=f'RotatedLogCompressThread-{self.name}', func=self.__compress_current_old_log)
        t.finished.connect(self.__compress_current_old_log_finished)
        self.__compression_thread_pool.add(t)
        t.start()

    def __compress_current_old_log_finished(self, thread_obj: CompressThread):
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
                message = f"""{'#'*66}
    # <start time> This Program is started at\t {start_time}.
    # <file time> This log file is created at\t {file_time}.
    {'#'*66}\n\n{message}"""
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
            self.signal_all.emit(text)
            self.signal_all_color.emit(text_color)
            self.signal_all_console.emit(text_console)
            self.signal_all_message.emit(msg)
        self.__isWriting = False

    def _trace(self, *args, _sender=None, **kwargs) -> None:
        # This method is mainly used to separate the _sender parameter and prevent external misinformation.
        if self.__log_level > LogLevel.TRACE and _sender != '_LoggingListener':
            return
        text, text_console, text_color, msg = self.__output(LogLevel.TRACE, *args, **kwargs)
        self.signal_trace.emit(text)
        self.signal_trace_color.emit(text_color)
        self.signal_trace_console.emit(text_console)
        self.signal_trace_message.emit(msg)

    def _debug(self, *args, _sender=None, **kwargs) -> None:
        # This method is mainly used to separate the _sender parameter and prevent external misinformation.
        if self.__log_level > LogLevel.DEBUG and _sender != '_LoggingListener':
            return
        text, text_console, text_color, msg = self.__output(LogLevel.DEBUG, *args, **kwargs)
        self.signal_debug.emit(text)
        self.signal_debug_color.emit(text_color)
        self.signal_debug_console.emit(text_console)
        self.signal_debug_message.emit(msg)

    def _info(self, *args, _sender=None, **kwargs) -> None:
        # This method is mainly used to separate the _sender parameter and prevent external misinformation.
        if self.__log_level > LogLevel.INFO and _sender != '_LoggingListener':
            return
        text, text_console, text_color, msg = self.__output(LogLevel.INFO, *args, **kwargs)
        self.signal_info.emit(text)
        self.signal_info_color.emit(text_color)
        self.signal_info_console.emit(text_console)
        self.signal_info_message.emit(msg)

    def _warning(self, *args, _sender=None, **kwargs) -> None:
        # This method is mainly used to separate the _sender parameter and prevent external misinformation.
        if self.__log_level > LogLevel.WARNING and _sender != '_LoggingListener':
            return
        text, text_console, text_color, msg = self.__output(LogLevel.WARNING, *args, **kwargs)
        self.signal_warning.emit(text)
        self.signal_warning_color.emit(text_color)
        self.signal_warning_console.emit(text_console)
        self.signal_warning_message.emit(msg)

    def _error(self, *args, _sender=None, **kwargs) -> None:
        # This method is mainly used to separate the _sender parameter and prevent external misinformation.
        if self.__log_level > LogLevel.ERROR and _sender != '_LoggingListener':
            return
        text, text_console, text_color, msg = self.__output(LogLevel.ERROR, *args, **kwargs)
        self.signal_error.emit(text)
        self.signal_error_color.emit(text_color)
        self.signal_error_console.emit(text_console)
        self.signal_error_message.emit(msg)

    def _critical(self, *args, _sender=None, **kwargs) -> None:
        # This method is mainly used to separate the _sender parameter and prevent external misinformation.
        if self.__log_level > LogLevel.CRITICAL and _sender != '_LoggingListener':
            return
        text, text_console, text_color, msg = self.__output(LogLevel.CRITICAL, *args, **kwargs)
        self.signal_critical.emit(text)
        self.signal_critical_color.emit(text_color)
        self.signal_critical_console.emit(text_console)
        self.signal_critical_message.emit(msg)

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

    def set_listen_logging(self, logger_name: str = '', level: LogLevel = LogLevel.NOTSET) -> SELF_LOGGER:
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

    def remove_listen_logging(self) -> SELF_LOGGER:
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

    def set_exclude_classes(self, classes_list: list) -> SELF_LOGGER:
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

    def set_exclude_modules(self, modules_list: list) -> SELF_LOGGER:
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

    def add_exclude_func(self, func_name: str) -> SELF_LOGGER:
        """ 
        Add the function to be excluded

        - Args:
            - func_name(str): The function name (as strings) to exclude.
        """
        self.__exclude_funcs.add(func_name)
        return self

    def add_exclude_class(self, cls_name: str) -> SELF_LOGGER:
        """ 
        Add the class to be excluded

        - Args:
            - cls_name(str): The class name (as strings) to exclude.
        """
        self.__exclude_classes.add(cls_name)
        return self

    def add_exclude_module(self, module_name: str) -> SELF_LOGGER:
        """ 
        Add the module to be excluded

        - Args:
            - module_name(str): The module name (as strings) to exclude.
        """
        self.__exclude_modules.add(module_name)
        return self

    def remove_exclude_func(self, func_name: str) -> SELF_LOGGER:
        """ 
        Remove the function to be excluded

        - Args:
            - func_name(str): The function name (as strings) to exclude
        """
        self.__exclude_funcs.discard(func_name)
        return self

    def remove_exclude_class(self, cls_name: str) -> SELF_LOGGER:
        """ 
        Remove the class to be excluded

        - Args:
            - cls_name(str): The class name (as strings) to exclude
        """
        self.__exclude_classes.discard(cls_name)
        return self

    def remove_exclude_module(self, module_name: str) -> SELF_LOGGER:
        """ 
        Remove the module to be excluded

        - Args:
            - module_name(str): The module name (as strings) to exclude
        """
        self.__exclude_modules.discard(module_name)
        return self

    def set_root_dir(self, root_dir: str) -> SELF_LOGGER:
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

    def set_root_folder_name(self, root_folder_name: str) -> SELF_LOGGER:
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

    def set_log_folder_name(self, log_folder_name: str) -> SELF_LOGGER:
        """ 
        Set log folder name

        - Args:
            - log_folder_name(str): log folder name
        """
        if log_folder_name in _Log_Default.LIST_RESERVE_NAME:
            warning_text = (
                _ColorMap.asni_ct(f'< WARNING > {log_folder_name} is a reserved name. Log folder name will set to {self.__log_name}', _ColorMap.LIGHTYELLOW.ANSI_TXT))
            if sys.stdout:
                sys.stdout.write(warning_text)
            self.__log_folder_name: str = self.__log_name
        elif not log_folder_name:
            self.__log_folder_name: str = self.__log_name
        else:
            self.__log_folder_name: str = log_folder_name
        self.__log_dir: str = os.path.join(self.__root_path, self.__log_folder_name)
        return self

    def set_level(self, log_level: LogLevel) -> SELF_LOGGER:
        """ 
        Set log level

        - Args:
            - log_level(LogLevel): log level
        """
        self.__log_level = LogLevel._normalize_log_level(log_level)
        return self

    def set_enable_daily_split(self, enable: bool) -> SELF_LOGGER:
        """ 
        Set whether to enable daily split log

        - Args:
            - enable(bool): whether to enable daily split log
        """
        self.__enableDailySplit = enable
        return self

    def set_enable_console_output(self, enable: bool) -> SELF_LOGGER:
        """ 
        Set whether to enable console output

        - Args:
            - enable(bool): Whether to enable console output
        """
        self.__enableConsoleOutput = enable
        return self

    def set_enable_file_output(self, enable: bool) -> SELF_LOGGER:
        """ 
        Set whether to enable file output

        - Args:
            - enable(bool): Whether to enable file output
        """
        self.__enableFileOutput = enable
        return self

    def set_enable_runtime_zip(self, enable: bool) -> SELF_LOGGER:
        """ 
        Set whether to compress log files at runtime

        - Args:
            - enable(bool): Whether to compress log files at runtime
        """
        self.__enableRuntimeZip: bool = enable
        return self

    # def set_enable_startup_zip(self, enable: bool) -> SELF_LOGGER:
    #     """
    #     Set whether to compress log files before running

    #     - Args:
    #       - enable(bool): Whether to compress log files before running
    #     """
    #     self.__enableStartupZip = enable
    #     return self

    def set_file_size_limit_kB(self, size_limit: typing.Union[int, float]) -> SELF_LOGGER:
        """ 
        Set a single log file size limit

        - Args:
            - size_limit(int | float): Single log file size limit, unit is KB
        """
        if not isinstance(size_limit, (int, float)):
            raise TypeError("size_limit must be int")
        self.__limit_single_file_size_Bytes: typing.Union[int, float] = size_limit * 1000
        return self

    def set_file_count_limit(self, count_limit: int, isStict: bool = False) -> SELF_LOGGER:
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

    def set_file_days_limit(self, days_limit: int, isStict: bool = False) -> SELF_LOGGER:
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

    def set_message_format(self, message_format: str) -> SELF_LOGGER:
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

    def set_highlight_type(self, highlight_type: LogHighlightType) -> SELF_LOGGER:
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

    def set_enable_QThread_tracking(self, enable: bool) -> SELF_LOGGER:
        """ 
        Set whether to use QThread.objectName() as the thread name for logging or tracking

        - Args:
            - enable(bool): If True, use QThread.objectName() to represent the thread name.
        """
        self.__enableQThreadtracking = enable
        return self


class JFLoggerGroup(object):
    """
    This class is used to manage a group of loggers. It can collect the log message of all or some loggers and write them to a specific file.
    It is singleton.

    - Args:
        - root_dir(str): The root directory of the log group.
        - root_folder_name(str): The name of the root folder of the log group.
        - limit_single_file_size_kB(int): The maximum size of a single log file, in kilobytes. Default is no limit.
        - limit_files_count(int): The maximum number of log files. Default is no limit.
        - limit_files_days(int): The maximum number of days to keep log files. Default is no limit.
        - enableDailySplit(bool): Whether to split the log files daily. Default is False.
        - enableFileOutput(bool): Whether to output the log files. Default is True.

    - Signals:
        - Explain:
            - xxx: formatted log messages
            - xxx_color: formatted log messages with color
            - xxx_console: formatted log messages for console
            - xxx_message: log messages without color and format
        - Signal for `all` log messages:
            - `signal_all` `signal_all_color` `signal_all_console` `signal_all_message`
        - Signal for `trace` level messages:
            - `signal_trace` `signal_trace_color` `signal_trace_console` `signal_trace_message`
        - Signal for `debug` level messages:
            - `signal_debug` `signal_debug_color` `signal_debug_console` `signal_debug_message`
        - Signal for `info` level messages:
            - `signal_info` `signal_info_color` `signal_info_console` `signal_info_message`
        - Signal for `warning` level messages:
            - `signal_warning` `signal_warning_color` `signal_warning_console` `signal_warning_message`
        - Signal for `error` level messages:
            - `signal_error` `signal_error_color` `signal_error_console` `signal_error_message`
        - Signal for `critical` level messages:
            - `signal_critical` `signal_critical_color` `signal_critical_console` `signal_critical_message`

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
    signal_all = _LogSignal(str)
    signal_all_color = _LogSignal(str)
    signal_all_console = _LogSignal(str)
    signal_all_message = _LogSignal(str)
    signal_trace = _LogSignal(str)
    signal_trace_color = _LogSignal(str)
    signal_trace_console = _LogSignal(str)
    signal_trace_message = _LogSignal(str)
    signal_debug = _LogSignal(str)
    signal_debug_color = _LogSignal(str)
    signal_debug_console = _LogSignal(str)
    signal_debug_message = _LogSignal(str)
    signal_info = _LogSignal(str)
    signal_info_color = _LogSignal(str)
    signal_info_console = _LogSignal(str)
    signal_info_message = _LogSignal(str)
    signal_warning = _LogSignal(str)
    signal_warning_color = _LogSignal(str)
    signal_warning_console = _LogSignal(str)
    signal_warning_message = _LogSignal(str)
    signal_error = _LogSignal(str)
    signal_error_color = _LogSignal(str)
    signal_error_console = _LogSignal(str)
    signal_error_message = _LogSignal(str)
    signal_critical = _LogSignal(str)
    signal_critical_color = _LogSignal(str)
    signal_critical_console = _LogSignal(str)
    signal_critical_message = _LogSignal(str)

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
                _ColorMap.asni_ct('< WARNING > No File Output from', _ColorMap.LIGHTYELLOW.ANSI_TXT) +
                _ColorMap.asni_ct(f'{self.__class__.__name__}\n   ', _ColorMap.LIGHTYELLOW.ANSI_TXT, _ColorMap.GRAY.ANSI_BG) +
                _ColorMap.asni_ct(
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

    def set_root_dir(self, root_dir: str) -> SELF_LOGGERGROUP:
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

    def set_root_folder_name(self, root_folder_name: str) -> SELF_LOGGERGROUP:
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

    def set_enable_daily_split(self, enable: bool) -> SELF_LOGGERGROUP:
        """ 
        Set whether to split the log files daily.

        - Args:
            - enable(bool): whether to split the log files daily        
        """
        self.__enableDailySplit: bool = enable
        return self

    def set_enable_file_output(self, enable: bool) -> SELF_LOGGERGROUP:
        """ 
        Set whether to output log files.

        - Args:
            - enable(bool): whether to output log files
        """
        self.__enableFileOutput: bool = enable
        return self

    def set_enable_runtime_zip(self, enable: bool) -> SELF_LOGGERGROUP:
        """ 
        Set whether to zip the log files at runtime

        - Args:
            - enable(bool): whether to zip the log files at runtime
        """
        self.__enableRuntimeZip: bool = enable
        return self

    # def set_enable_startup_zip(self, enable: bool) -> SELF_LOGGERGROUP:
    #     """
    #     Set whether to zip the log files at startup.

    #     - Args:
    #       - enable(bool): whether to zip the log files at startup
    #     """
    #     self.__enableStartupZip = enable
    #     return self

    def set_file_size_limit_kB(self, size_limit: typing.Union[int, float]) -> SELF_LOGGERGROUP:
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

    def set_file_count_limit(self, count_limit: int, isStict: bool = False) -> SELF_LOGGERGROUP:
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

    def set_file_days_limit(self, days_limit: int, isStict: bool = False) -> SELF_LOGGERGROUP:
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

    def set_log_group(self, log_group: list) -> SELF_LOGGERGROUP:
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

    def append_log(self, log_obj: typing.Union[JFLogger, list]) -> SELF_LOGGERGROUP:
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

    def remove_log(self, log_obj: JFLogger) -> SELF_LOGGERGROUP:
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
        t = CompressThread(name=f'RotatedLogCompressThread<{self.__class__.__name__}>-{len(self.__compression_thread_pool)}', func=self.__compress_current_old_log)
        t.finished.connect(self.__compress_current_old_log_finished)
        self.__compression_thread_pool.add(t)
        t.start()

    def __compress_current_old_log_finished(self, thread_obj: CompressThread):
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
                message = f"""{'#'*66}
    # <start time> This Program is started at\t {start_time}.
    # <file time> This log file is created at\t {file_time}.
    {'#'*66}\n\n{message}"""
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

    def __connect_single(self, log_obj: JFLogger) -> None:
        if log_obj in self.__log_group:
            return
        self.__log_group.append(log_obj)
        log_obj.signal_all.connect(self.__write)
        log_obj.signal_all.connect(self.signal_all)
        log_obj.signal_all_color.connect(self.signal_all_color)
        log_obj.signal_all_console.connect(self.signal_all_console)
        log_obj.signal_all_message.connect(self.signal_all_message)
        log_obj.signal_trace.connect(self.signal_trace)
        log_obj.signal_trace_color.connect(self.signal_trace_color)
        log_obj.signal_trace_console.connect(self.signal_trace_console)
        log_obj.signal_trace_message.connect(self.signal_trace_message)
        log_obj.signal_debug.connect(self.signal_debug)
        log_obj.signal_debug_color.connect(self.signal_debug_color)
        log_obj.signal_debug_console.connect(self.signal_debug_console)
        log_obj.signal_debug_message.connect(self.signal_debug_message)
        log_obj.signal_info.connect(self.signal_info)
        log_obj.signal_info_color.connect(self.signal_info_color)
        log_obj.signal_info_console.connect(self.signal_info_console)
        log_obj.signal_info_message.connect(self.signal_info_message)
        log_obj.signal_warning.connect(self.signal_warning)
        log_obj.signal_warning_color.connect(self.signal_warning_color)
        log_obj.signal_warning_console.connect(self.signal_warning_console)
        log_obj.signal_warning_message.connect(self.signal_warning_message)
        log_obj.signal_error.connect(self.signal_error)
        log_obj.signal_error_color.connect(self.signal_error_color)
        log_obj.signal_error_console.connect(self.signal_error_console)
        log_obj.signal_error_message.connect(self.signal_error_message)
        log_obj.signal_critical.connect(self.signal_critical)
        log_obj.signal_critical_color.connect(self.signal_critical_color)
        log_obj.signal_critical_console.connect(self.signal_critical_console)
        log_obj.signal_critical_message.connect(self.signal_critical_message)

    def __disconnect_single(self, log_obj: JFLogger) -> None:
        if log_obj not in self.__log_group:
            return
        self.__log_group.remove(log_obj)
        log_obj.signal_all.disconnect(self.__write)
        log_obj.signal_all.disconnect(self.signal_all)
        log_obj.signal_all_color.disconnect(self.signal_all_color)
        log_obj.signal_all_console.disconnect(self.signal_all_console)
        log_obj.signal_all_message.disconnect(self.signal_all_message)
        log_obj.signal_trace.disconnect(self.signal_trace)
        log_obj.signal_trace_color.disconnect(self.signal_trace_color)
        log_obj.signal_trace_console.disconnect(self.signal_trace_console)
        log_obj.signal_trace_message.disconnect(self.signal_trace_message)
        log_obj.signal_debug.disconnect(self.signal_debug)
        log_obj.signal_debug_color.disconnect(self.signal_debug_color)
        log_obj.signal_debug_console.disconnect(self.signal_debug_console)
        log_obj.signal_debug_message.disconnect(self.signal_debug_message)
        log_obj.signal_info.disconnect(self.signal_info)
        log_obj.signal_info_color.disconnect(self.signal_info_color)
        log_obj.signal_info_console.disconnect(self.signal_info_console)
        log_obj.signal_info_message.disconnect(self.signal_info_message)
        log_obj.signal_warning.disconnect(self.signal_warning)
        log_obj.signal_warning_color.disconnect(self.signal_warning_color)
        log_obj.signal_warning_console.disconnect(self.signal_warning_console)
        log_obj.signal_warning_message.disconnect(self.signal_warning_message)
        log_obj.signal_error.disconnect(self.signal_error)
        log_obj.signal_error_color.disconnect(self.signal_error_color)
        log_obj.signal_error_console.disconnect(self.signal_error_console)
        log_obj.signal_error_message.disconnect(self.signal_error_message)
        log_obj.signal_critical.disconnect(self.signal_critical)
        log_obj.signal_critical_color.disconnect(self.signal_critical_color)
        log_obj.signal_critical_console.disconnect(self.signal_critical_console)
        log_obj.signal_critical_message.disconnect(self.signal_critical_message)


class Logger(JFLogger):
    """ 
    The new Logger class is renamed to JFLogger.
    The old class name is kept for compatibility, 
    and it will be removed in the future.
    """
    pass


class LoggerGroup(JFLoggerGroup):
    """ 
    The new LoggerGroup class is renamed to JFLoggerGroup.
    The old class name is kept for compatibility, 
    and it will be removed in the future.
    """
    pass


""" 
if __name__ == '__main__':
    Log = JFLogger('Log', os.path.dirname(__file__), log_level='info')
    Log.set_file_size_limit_kB(1024)
    Log.set_enable_daily_split(True)
    Log.set_listen_logging(level=LogLevel.INFO)
    # Log.set_enable_runtime_zip(True)
    Log_1 = JFLogger('Log_1', os.path.dirname(__file__), log_folder_name='test_folder', log_level=LogLevel.TRACE)
    Log_1.set_file_size_limit_kB(1024)
    Log_1.set_enable_daily_split(True)
    Log.signal_debug_message.connect(print)
    JFLogger_group = JFLoggerGroup(os.path.dirname(__file__))
    JFLogger_group.set_file_size_limit_kB(1024)
    # JFLogger_group.set_enable_runtime_zip(True)
    logging.debug('hello world from logging debug')  # logging 跟踪示例
    logging.info('hello world from logging info')
    logging.error("This is a error message from logging.")
    logging.warning("This is a warning message from logging.")
    logging.critical("This is a critical message from logging.")
    Log.trace('This is a trace message.')
    Log.debug('This is a debug message.')
    for i in range(100):
        Log.info(f'This is a info message -- {i}.'*100000)
    import time
    time.sleep(1)

    Log_1.debug('This is a debug message.')
    Log.info('This is a info message.')
    Log_1.warning('This is a warning message.')
    Log.error('This is a error message.')
    Log_1.critical('This is a critical message.')
"""
