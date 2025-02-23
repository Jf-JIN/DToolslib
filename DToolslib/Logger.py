import pprint
import sys
import os
import inspect
import re
import traceback
import logging
from datetime import datetime

_LOG_FOLDER_NAME = 'Logs'
_LOG_GROUP_FOLDER_NAME = '#Global_Log'


class _EnumBaseMeta(type):
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
    @classmethod
    def values(cls):
        return cls._members_.values()


class _ColorMapItem(object):
    def __init__(self, name, ansi_txt, ansi_bg, hex):
        self.name = name
        self.ANSI_TXT = ansi_txt
        self.ANSI_BG = ansi_bg
        self.HEX = hex

    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise AttributeError(f'Disable external modification of enumeration items\t< {name} > = {self.__dict__[name]}')
        super().__setattr__(name, value)


class _ColorMap(_EnumBase):
    """ 颜色枚举类 """
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


class LogLevel(_EnumBase):
    """ 日志级别枚举类 """
    NOTSET = 0
    TRACE = 10
    DEBUG = 20
    INFO = 30
    WARNING = 40
    ERROR = 50
    CRITICAL = 60
    NOOUT = 70


class LogHighlightType(_EnumBase):
    """ 高亮类型枚举类 """
    ASNI = 'ASNI'
    HTML = 'HTML'
    NONE = None


def _normalize_log_level(log_level: str | int | LogLevel) -> LogLevel:
    normalized_log_level = 0
    if isinstance(log_level, str):
        if log_level.upper() in LogLevel:
            normalized_log_level = getattr(LogLevel, log_level.upper())
        else:
            raise ValueError(f'<ERROR> Log level "{log_level}" is not a valid log level.')
    elif isinstance(log_level, int | float):
        normalized_log_level = abs(log_level // 10 * 10)
    else:
        raise ValueError(f'<ERROR> Log level "{log_level}" is not a valid log level. It should be a string or a number.')
    return normalized_log_level


def asni_ct(
    text: str,
    txt_color: str | None = None,
    bg_color: str | None = None,
    dim: bool = False,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    blink: bool = False,
    *args, **kwargs
) -> str:
    """
    ANSI转义序列生成器

    参数:
    - text: 需要转义的文本
    - txt_color: 文本颜色
    - bg_color: 背景颜色
    - dim: 是否为暗色
    - bold: 是否为粗体
    - italic: 是否为斜体
    - underline: 是否为下划线
    - blink: 是否为闪烁

    返回:
    - 转义后的文本
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


def html_ct(
    text: str,
    txt_color: str | None = None,
    bg_color: str | None = None,
    dim: bool = False,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    blink: bool = False,
    *args, **kwargs
) -> str:
    """
    HTML转义序列生成器

    参数:
    - text: 需要转义的文本
    - txt_color: 文本颜色
    - bg_color: 背景颜色
    - dim: 是否为暗色
    - bold: 是否为粗体
    - italic: 是否为斜体
    - underline: 是否为下划线
    - blink: 是否为闪烁

    返回:
    - 转义后的文本
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


class _BoundSignal:
    __name__: str = 'LogSignal'
    __qualname__: str = 'LogSignal'

    def __init__(self, types, owner, name, isClassSignal=False):
        if all([isinstance(typ, (type, tuple)) for typ in types]):
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

    def __del__(self):
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
    signal_trace = _LogSignal(str)
    signal_debug = _LogSignal(str)
    signal_info = _LogSignal(str)
    signal_warning = _LogSignal(str)
    signal_error = _LogSignal(str)
    signal_critical = _LogSignal(str)
    __instance = None

    def __new__(cls, *args, **kwargs):
        if not cls.__instance:
            cls.__instance = super().__new__(cls)
            cls.__instance.__isInitialized = False
        return cls.__instance

    def __init__(self, level) -> None:
        if self.__isInitialized:
            return
        self.__isInitialized = True
        super().__init__(level=level)

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
        self.__text_console = asni_ct(text, self.__color_font, self.__color_background, self.__dim, self.__bold, self.__italic, self.__underline, self.__blink)

    def __colorize_text(self, text: str, *args, highlight_type=None, **kwargs) -> str:
        if highlight_type is None:
            highlight_type = self.__highlight_type
            if highlight_type is None:
                return text
        if highlight_type == LogHighlightType.ASNI:
            return asni_ct(text, *args, **kwargs)
        elif highlight_type == LogHighlightType.HTML:
            return html_ct(text, *args, **kwargs)
        return text


class Logger(object):
    """
    日志类

    参数:
    - log_name(str): 日志名称
    - log_path(str): 日志路径, 默认为无路径
    - log_sub_folder_name(str): 日志子文件夹名称, 默认'', 此时将以日志名称作为子文件夹名称
    - log_level(str): 日志级别, 默认为 `INFO`
        - `TRACE` | `DEBUG` | `INFO` | `WARNING` | `ERROR` | `CRITICAL`
    - default_level(str): 默认日志级别, 是直接调用类时执行的日志级别, 默认为`INFO`
    - console_output(bool): 是否输出到控制台, 默认输出
    - file_output(bool): 是否输出到文件, 默认输出
    - size_limit(int): 文件大小限制, 单位为 kB, 默认不限制. 此项无法限制单消息长度, 若单个消息长度超过设定值, 为了消息完整性, 即使大小超过限制值, 也会完整写入日志文件, 则当前文件大小将超过限制值
    - files_limit(int): 文件数量限制, 默认不限制
    - days_limit(int): 天数限制, 默认不限制
    - split_by_day(bool): 是否按天分割日志, 默认不分割
    - message_format(str): 消息格式, 可自定义, 详细方法见示例. 默认格式为: `%(consoleLine)s\\n[%(asctime)s] [log: %(logName)s] [module: %(moduleName)s] [class: %(className)s] [function: %(functionName)s] [line: %(lineNum)s]- %(levelName)s\\n%(message)s\\n`
    - exclude_funcs(list[str]): 排除的函数列表, 用于追溯调用位置时, 排除父级调用函数, 排除的函数链应是完整的, 只写顶层的函数名将可能不会产生效果, 默认为空列表, 当前可以和当前级类并写来更加精确地定位排除项, 如: ['ClassA.funcA']
    - exclude_classes(list[str]): 排除的类列表, 用于追溯调用位置时, 排除父级调用类, 默认为空列表, 当前可以和当前级模块并写来更加精确地定位排除项, 如: ['ModuleA.ClassA']
    - exclude_modules(list[str]): 排除的模块列表, 用于追溯调用位置时, 排除父级调用模块, 默认为空列表
    - highlight_type(str|None): 高亮模式. 默认为 `ASNI`, 取消高亮则使用 None. 当前支持 `ASNI`, `HTML`
    - **kwargs, 消息格式中的自定义参数, 使用方法见示例


    信号:
    - signal_all: 所有日志消息信号对象, 用于在类外部接收所有日志类的日志消息
    - signal_all_color: 所有日志消息信号对象, 用于在类外部接收所有日志类的日志消息, 并带有颜色高亮
    - signal_all_console: 所有日志消息信号对象, 用于在类外部接收所有日志类的日志消息, 并带有控制台高亮
    - signal_all_message: 所有日志消息信号对象, 用于在类外部接收所有日志类的日志消息, 仅为消息内容
    - signal_trace: trace 级别日志消息信号对象, 用于在类外部接收 trace 级别的日志消息
    - signal_trace_color: trace 级别日志消息信号对象, 用于在类外部接收 trace 级别的日志消息, 并带有颜色高亮
    - signal_trace_console: trace 级别日志消息信号对象, 用于在类外部接收 trace 级别的日志消息, 并带有控制台高亮
    - signal_trace_message: trace 级别日志消息信号对象, 用于在类外部接收 trace 级别的日志消息, 仅为消息内容
    - signal_debug: debug 级别日志消息信号对象, 用于在类外部接收 debug 级别的日志消息
    - signal_debug_color: debug 级别日志消息信号对象, 用于在类外部接收 debug 级别的日志消息, 并带有颜色高亮
    - signal_debug_console: debug 级别日志消息信号对象, 用于在类外部接收 debug 级别的日志消息, 并带有控制台高亮
    - signal_debug_message: debug 级别日志消息信号对象, 用于在类外部接收 debug 级别的日志消息, 仅为消息内容
    - signal_info: info 级别日志消息信号对象, 用于在类外部接收 info 级别的日志消息
    - signal_info_color: info 级别日志消息信号对象, 用于在类外部接收 info 级别的日志消息, 并带有颜色高亮
    - signal_info_console: info 级别日志消息信号对象, 用于在类外部接收 info 级别的日志消息, 并带有控制台高亮
    - signal_info_message: info 级别日志消息信号对象, 用于在类外部接收 info 级别的日志消息, 仅为消息内容
    - signal_warning: warning 级别日志消息信号对象, 用于在类外部接收 warning 级别的日志消息
    - signal_warning_color: warning 级别日志消息信号对象, 用于在类外部接收 warning 级别的日志消息, 并带有颜色高亮
    - signal_warning_console: warning 级别日志消息信号对象, 用于在类外部接收 warning 级别的日志消息, 并带有控制台高亮
    - signal_warning_message: warning 级别日志消息信号对象, 用于在类外部接收 warning 级别的日志消息, 仅为消息内容
    - signal_error: error 级别日志消息信号对象, 用于在类外部接收 error 级别的日志消息
    - signal_error_color: error 级别日志消息信号对象, 用于在类外部接收 error 级别的日志消息, 并带有颜色高亮
    - signal_error_console: error 级别日志消息信号对象, 用于在类外部接收 error 级别的日志消息, 并带有控制台高亮
    - signal_error_message: error 级别日志消息信号对象, 用于在类外部接收 error 级别的日志消息, 仅为消息内容
    - signal_critical: critical 级别日志消息信号对象, 用于在类外部接收 critical 级别的日志消息
    - signal_critical_color: critical 级别日志消息信号对象, 用于在类外部接收 critical 级别的日志消息, 并带有颜色高亮
    - signal_critical_console: critical 级别日志消息信号对象, 用于在类外部接收 critical 级别的日志消息, 并带有控制台高亮
    - signal_critical_message: critical 级别日志消息信号对象, 用于在类外部接收 critical 级别的日志消息, 仅为消息内容

    方法:
    - trace(*message) # 输出追踪信息, 支持多参数
    - debug(*message) # 输出调试信息, 支持多参数
    - info(*message)  # 输出普通信息, 支持多参数
    - warning(*message)  # 输出警告信息, 支持多参数
    - error(*message)  # 输出错误信息, 支持多参数
    - critical(*message)  # 输出严重错误信息, 支持多参数
    - exception(*message)  # 输出异常信息, 支持多参数

    示例:
    1. 通常调用:

        logger = Logger(log_name='test', log_path='D:/test')

        logger.debug('debug message')

    2. (不推荐): 可以直接调用类, 默认是执行info方法, 可以通过修改初始化参数表中的default_level来修改默认类执行的日志级别

        logger('info message')

    3. 关于格式的设置:

    - 提供的默认格式参数有:
        - `asctime` 当前时间
        - `moduleName` 模块名称
        - `functionName` 函数/方法名称
        - `className` 类名称
        - `levelName` 当前日志级别
        - `lineNum` 代码行号
        - `message` 消息内容
        - `scriptName` 脚本名称
        - `scriptPath` 脚本路径
        - `consoleLine` 控制台链接行

    - 如需添加自定义的参数, 可以在初始化中添加, 并可以在后续对相应的属性进行赋值

    logger = Logger(log_name='test', log_path='D:/test', message_format='%(asctime)s-%(levelName)s -%(message)s -%(happyNewYear)s', happyNewYear=False)

    logger.happyNewYear = True

    logger.debug('debug message')

    得到输出: `2025-01-01 06:30:00-INFO -debug message -True`
    """
    __logging_listening_level_int__ = 100
    __logging_listener_handler = _LoggingListener(0)
    __logging_listener = logging.getLogger()
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
    __logger_folder_name_list__ = []

    def __new__(cls, log_name, *args, **kwargs):
        instance = super().__new__(cls)
        if log_name in cls.__logger_name_list__:
            raise ValueError(f'Logger "{log_name}" already exists.')
        cls.__logger_name_list__.append(log_name)
        cls.__instance_list__.append(instance)
        return instance

    def __init__(
        self,
        log_name: str,
        log_folder_path: str = '',
        log_sub_folder_name: str = '',
        log_level: str | int = LogLevel.INFO,
        default_level: str | int = LogLevel.INFO,
        console_output: bool = True,
        file_output: bool = True,
        size_limit: int = -1,  # KB
        files_limit: int = -1,
        days_limit: int = -1,
        split_by_day: bool = False,
        message_format: str = '%(consoleLine)s\n[%(asctime)s] [log: %(logName)s] [module: %(moduleName)s] [class: %(className)s] [function: %(functionName)s] [line: %(lineNum)s]- %(levelName)s\n%(message)s\n',
        exclude_funcs: list = [],
        exclude_classes: list = [],
        exclude_modules: list = [],
        highlight_type: str | None = None,
        ** kwargs,
    ) -> None:
        self.__doConsoleOutput = console_output if isinstance(console_output, bool) else True
        self.__doFileOutput = file_output if isinstance(file_output, bool) else True
        self.__log_name = log_name
        if not isinstance(log_folder_path, str):
            raise ValueError(f'<WARNING> Log folder path "{log_folder_path}" is not a string.')
        self.__log_path = os.path.join(log_folder_path, _LOG_FOLDER_NAME) if log_folder_path else ''
        self.__isExistsPath = False
        if log_folder_path and os.path.exists(log_folder_path):
            self.__isExistsPath = True
        elif log_folder_path:
            raise FileNotFoundError(f'Log folder path "{log_folder_path}" does not exist, create it.')
        else:
            self.__printf(
                f'\x1B[93m < WARNING > No File Output from \x1B[93;100m<{self.__log_name}>\x1B[0m\n   \x1B[33m- No log file will be recorded because the log folder path is not specified. The current file path input is "{self.__log_path}". Type: {type(self.__log_path)}\x1B[0m\n')
        self.__log_sub_folder_name = log_sub_folder_name if isinstance(log_sub_folder_name, str) and log_sub_folder_name else self.__log_name
        if self.__log_sub_folder_name in self.__class__.__logger_folder_name_list__:
            raise ValueError(f'<WARNING> Log sub-folder name "{self.__log_sub_folder_name}" is already in use.')
        self.__class__.__logger_folder_name_list__.append(self.__log_sub_folder_name)
        self.__log_level = _normalize_log_level(log_level)
        self.__default_level = _normalize_log_level(default_level)
        self.__size_limit = size_limit * 1000 if isinstance(size_limit, int) else -1
        self.__count_limit = files_limit if isinstance(files_limit, int) else -1
        self.__days_limit = days_limit if isinstance(days_limit, int) else -1
        self.__doSplitByDay = split_by_day if isinstance(split_by_day, bool) else False
        self.__message_format = message_format if isinstance(
            message_format, str) else '%(consoleLine)s\n[%(asctime)s] [log: %(logName)s] [module: %(moduleName)s] [class: %(className)s] [function: %(functionName)s] [line: %(lineNum)s]- %(levelName)s\n%(message)s\n'
        self.__exclude_funcs_list = exclude_funcs if isinstance(exclude_funcs, list) else []
        self.__exclude_classes_list = exclude_classes if isinstance(exclude_classes, list) else []
        self.__exclude_modules_list = exclude_modules if isinstance(exclude_modules, list) else []
        self.__highlight_type = highlight_type if isinstance(highlight_type, (str, type(None))) and highlight_type in LogHighlightType.values() else LogHighlightType.NONE
        self.__kwargs = kwargs
        self.__dict__.update(kwargs)
        self.__init_params()
        self.__clear_files()

    def __init_params(self) -> None:
        self.__var_dict = {  # 日志变量字典
            'logName': _LogMessageItem('logName', font_color=_ColorMap.CYAN.name, highlight_type=self.__highlight_type),
            'asctime': _LogMessageItem('asctime', font_color=_ColorMap.GREEN.name, highlight_type=self.__highlight_type, bold=True),
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
        self.__self_class_name: str = self.__class__.__name__
        self.__self_module_name: str = os.path.splitext(os.path.basename(__file__))[0]
        self.__start_time = datetime.now()
        for key, value in self.__kwargs.items():
            if key not in self.__var_dict:
                self.__var_dict[key] = _LogMessageItem(key, font_color=_ColorMap.CYAN.name)
            self.__var_dict[key].set_text(value)
        self.__exclude_funcs = set()  # 存储 __find_caller 中忽略的函数
        self.__exclude_funcs.update(self.__class__.__dict__.keys())
        self.__exclude_funcs.difference_update(dir(object))
        self.__exclude_classes: set = {
            self.__self_class_name,
            '_LoggingListener',
            '_LogSignal',
            '_BoundSignal',
            'RootLogger',
        }
        self.__exclude_modules = set()
        # self.__exclude_modules.add(self.__self_module_name)
        for item in self.__exclude_funcs_list:
            self.__exclude_funcs.add(item)
        for item in self.__exclude_classes_list:
            self.__exclude_classes.add(item)
        for item in self.__exclude_modules_list:
            self.__exclude_modules.add(item)
        self.__current_size = 0
        self.__current_day = datetime.today().date()
        self.__isNewFile = True
        self.__level_color_dict = {
            LogLevel.NOTSET: _LogMessageItem('levelName', text='NOTSET', font_color=_ColorMap.LIGHTBLUE.name, highlight_type=self.__highlight_type),
            LogLevel.TRACE: _LogMessageItem('levelName', text='TRACE', font_color=_ColorMap.LIGHTGREEN.name, highlight_type=self.__highlight_type),
            LogLevel.DEBUG: _LogMessageItem('levelName', text='DEBUG', font_color=_ColorMap.BLACK.name, background_color=_ColorMap.LIGHTGREEN.name, highlight_type=self.__highlight_type),
            LogLevel.INFO: _LogMessageItem('levelName', text='INFO', font_color=_ColorMap.BLUE.name, highlight_type=self.__highlight_type),
            LogLevel.WARNING: _LogMessageItem('levelName', text='WARNING', font_color=_ColorMap.LIGHTYELLOW.name, highlight_type=self.__highlight_type, bold=True),
            LogLevel.ERROR: _LogMessageItem('levelName', text='ERROR', font_color=_ColorMap.WHITE.name, background_color=_ColorMap.LIGHTRED.name, highlight_type=self.__highlight_type, bold=True),
            LogLevel.CRITICAL: _LogMessageItem('levelName', text='CRITICAL', font_color=_ColorMap.LIGHTYELLOW.name, background_color=_ColorMap.RED.name, highlight_type=self.__highlight_type, bold=True, blink=True),
        }
        listen_level_dict = {
            LogLevel.NOTSET: LogLevel.NOTSET,
            LogLevel.TRACE: LogLevel.NOTSET,
            LogLevel.DEBUG: LogLevel.TRACE,
            LogLevel.INFO: LogLevel.DEBUG,
            LogLevel.WARNING: LogLevel.INFO,
            LogLevel.ERROR: LogLevel.WARNING,
            LogLevel.CRITICAL: LogLevel.ERROR,
            LogLevel.NOOUT: LogLevel.ERROR
        }
        if self.__class__.__logging_listening_level_int__ >= 100:
            self.__logging_listener_handler.signal_trace.connect(self._trace)
            self.__logging_listener_handler.signal_debug.connect(self._debug)
            self.__logging_listener_handler.signal_info.connect(self._info)
            self.__logging_listener_handler.signal_warning.connect(self._warning)
            self.__logging_listener_handler.signal_error.connect(self._error)
            self.__logging_listener_handler.signal_critical.connect(self._critical)
            self.__logging_listener.addHandler(self.__logging_listener_handler)
        if self.__log_level <= self.__class__.__logging_listening_level_int__:
            self.__logging_listener.setLevel(listen_level_dict[self.__log_level])
            self.__class__.__logging_listening_level_int__ = self.__log_level

    def __set_log_file_path(self) -> None:
        """ 设置日志文件路径 """
        # 支持的字符 {}[];'',.!~@#$%^&()_+-=
        if self.__isExistsPath is False:
            return
        if not hasattr(self, '_Logger__log_file_path'):  # 初始化, 创建属性
            self.__start_time_format = self.__start_time.strftime("%Y%m%d_%H'%M'%S")
            self.__current_log_folder_path = os.path.join(self.__log_path, self.__log_sub_folder_name)
            if not os.path.exists(self.__current_log_folder_path):
                os.makedirs(self.__current_log_folder_path)
            self.__log_file_path = os.path.join(self.__log_path, self.__log_sub_folder_name, f'{self.__log_name}-[{self.__start_time_format}]--0.log')
        else:
            file_name = os.path.splitext(os.path.basename(self.__log_file_path))[0]
            str_list = file_name.split('--')
            self.__log_file_path = os.path.join(self.__log_path, self.__log_sub_folder_name, f'{str_list[0]}--{int(str_list[-1]) + 1}.log')

    def __call__(self, *args, **kwargs) -> None:
        call_dict = {
            LogLevel.DEBUG: self.debug,
            LogLevel.INFO: self.info,
            LogLevel.WARNING: self.warning,
            LogLevel.ERROR: self.error,
            LogLevel.CRITICAL: self.critical,
        }
        if self.__default_level in call_dict:
            call_dict[self.__default_level](*args, **kwargs)
        else:
            raise TypeError("'module' object is not callable. Please use Logger.trace/debug/info/warning/error/critical to log.")

    def __setattr__(self, name: str, value) -> None:
        if hasattr(self, '_Logger__kwargs') and name != '_Logger__kwargs' and name in self.__kwargs:
            self.__kwargs[name] = value
            if name not in self.__var_dict:
                self.__var_dict[name] = _LogMessageItem(name, _ColorMap.CYAN.name)
            self.__var_dict[name].set_text(value)
        if hasattr(self, '_Logger__kwargs') and (not name.startswith('_Logger__') and name not in ['__signals__', '__class_signals__'] and name not in self.__dict__):
            raise AttributeError(f"'Logger' object has no attribute '{name}'")
        super().__setattr__(name, value)

    def __clear_files(self) -> None:
        """
        清理日志文件.
        """
        if self.__isExistsPath is False:
            return
        if (not isinstance(self.__count_limit, int) and self.__count_limit < 0) or (not isinstance(self.__days_limit, int) and self.__days_limit <= 0):
            return
        self.__current_log_folder_path = os.path.join(self.__log_path, self.__log_sub_folder_name)
        if not os.path.exists(self.__current_log_folder_path):
            return
        current_file_list = []
        for file in os.listdir(self.__current_log_folder_path):
            fp = os.path.join(self.__current_log_folder_path, file)
            if file.endswith('.log') and os.path.isfile(fp):
                current_file_list.append(fp)
        length_file_list = len(current_file_list)
        # 清理超过文件数量限制的文件
        if (isinstance(self.__count_limit, int) and self.__count_limit >= 0) and length_file_list > self.__count_limit:
            sorted_files = sorted(current_file_list, key=os.path.getctime)
            for file_path in sorted_files[:length_file_list - self.__count_limit]:
                os.remove(file_path)
        # 清理超过天数限制的文件
        elif isinstance(self.__days_limit, int) and self.__days_limit > 0:
            for file_path in current_file_list:
                if (datetime.today() - datetime.fromtimestamp(os.path.getctime(file_path))).days > self.__days_limit:
                    os.remove(file_path)

    def __find_caller(self) -> dict:
        """ 定位调用者 """
        stack = inspect.stack()
        caller_name = ''
        class_name = ''
        linenum = -1
        module_name = ''
        script_name = ''
        script_path = ''
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
                and f'_Logger__{unprefix_variable}' not in self.__exclude_funcs
                and temp_class_name not in self.__exclude_classes
                and module_class_name not in self.__exclude_classes
                and temp_module_name not in self.__exclude_modules
            ):  # 不在排除列表中, 同时也排除当前类中的私有方法
                caller_name = fn.function
                class_name = temp_class_name
                linenum = fn.lineno
                module_name = temp_module_name
                script_name = os.path.basename(fn.filename)
                script_path = fn.filename
                func = fn
                break
        return {
            'caller': func,
            'caller_name': caller_name,
            'class_name': class_name,
            'line_num': linenum,
            'module_name': module_name,
            'script_name': script_name,
            'script_path': script_path,
        }

    def __format(self, log_level: int, *args) -> tuple:
        """ 格式化日志信息 """
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
        """ 打印日志信息 """
        if not self.__doConsoleOutput:
            return
        sys.stdout.write(message)

    def __write(self, message: str) -> None:
        """ 写入日志信息 """
        if not self.__doFileOutput or self.__isExistsPath is False:
            return
        if self.__size_limit and self.__size_limit > 0:
            # 大小限制
            writting_size = len(message.encode('utf-8'))
            self.__current_size += writting_size
            if self.__current_size >= self.__size_limit:
                self.__isNewFile = True
        if self.__doSplitByDay:
            # 按天分割
            if datetime.today().date() != self.__current_day:
                self.__isNewFile = True
        if self.__isNewFile:
            # 创建新文件
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
        if not os.path.exists(self.__current_log_folder_path):
            os.makedirs(self.__current_log_folder_path)
        with open(self.__log_file_path, 'a', encoding='utf-8') as f:
            f.write(message)

    def __output(self, level, *args, **kwargs) -> tuple:
        text, text_console, text_color, msg = self.__format(level, *args)
        self.__write(text)
        self.__printf(text_console)
        self.signal_all.emit(text)
        self.signal_all_color.emit(text_color)
        self.signal_all_console.emit(text_console)
        self.signal_all_message.emit(msg)
        return text, text_console, text_color, msg

    def _trace(self, *args, _sender=None, **kwargs) -> None:
        """ 打印追踪信息 """
        if self.__log_level > LogLevel.TRACE and _sender != '_LoggingListener':
            return
        text, text_console, text_color, msg = self.__output(LogLevel.TRACE, *args, **kwargs)
        self.signal_trace.emit(text)
        self.signal_trace_color.emit(text_color)
        self.signal_trace_console.emit(text_console)
        self.signal_trace_message.emit(msg)

    def _debug(self, *args, _sender=None, **kwargs) -> None:
        """ 打印调试信息 """
        if self.__log_level > LogLevel.DEBUG and _sender != '_LoggingListener':
            return
        text, text_console, text_color, msg = self.__output(LogLevel.DEBUG, *args, **kwargs)
        self.signal_debug.emit(text)
        self.signal_debug_color.emit(text_color)
        self.signal_debug_console.emit(text_console)
        self.signal_debug_message.emit(msg)

    def _info(self, *args, _sender=None, **kwargs) -> None:
        """ 打印信息 """
        if self.__log_level > LogLevel.INFO and _sender != '_LoggingListener':
            return
        text, text_console, text_color, msg = self.__output(LogLevel.INFO, *args, **kwargs)
        self.signal_info.emit(text)
        self.signal_info_color.emit(text_color)
        self.signal_info_console.emit(text_console)
        self.signal_info_message.emit(msg)

    def _warning(self, *args, _sender=None, **kwargs) -> None:
        """ 打印警告信息 """
        if self.__log_level > LogLevel.WARNING and _sender != '_LoggingListener':
            return
        text, text_console, text_color, msg = self.__output(LogLevel.WARNING, *args, **kwargs)
        self.signal_warning.emit(text)
        self.signal_warning_color.emit(text_color)
        self.signal_warning_console.emit(text_console)
        self.signal_warning_message.emit(msg)

    def _error(self, *args, _sender=None, **kwargs) -> None:
        """ 打印错误信息 """
        if self.__log_level > LogLevel.ERROR and _sender != '_LoggingListener':
            return
        text, text_console, text_color, msg = self.__output(LogLevel.ERROR, *args, **kwargs)
        self.signal_error.emit(text)
        self.signal_error_color.emit(text_color)
        self.signal_error_console.emit(text_console)
        self.signal_error_message.emit(msg)

    def _critical(self, *args, _sender=None, **kwargs) -> None:
        """ 打印严重错误信息 """
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

    def exception(self, *args, **kwargs) -> None:
        """ 打印异常信息 """
        exception_str = traceback.format_exc()
        if exception_str == f'{type(None).__name__}: {None}\n':
            return
        exception_str += '\n'
        self.error(exception_str, *args, **kwargs)


class LoggerGroup(object):
    """
    日志组类

    参数:
    - log_folder_path(str): 日志组文件夹路径
    - size_limit(int): 文件大小限制, 单位为 kB, 默认不限制. 此项无法限制单消息长度, 若单个消息长度超过设定值, 为了消息完整性, 即使大小超过限制值, 也会完整写入日志文件, 则当前文件大小将超过限制值
    - files_limit(int): 文件数量限制, 默认不限制
    - days_limit(int): 天数限制, 默认不限制
    - split_by_day(bool): 是否按天分割日志, 默认不分割

    信号:
    - signal_all: 公共日志消息信号对象, 用于在类外部接收所有日志类的日志消息
    - signal_all_color: 公共日志消息信号对象, 用于在类外部接收所有日志类的日志消息, 并带有颜色高亮
    - signal_all_console: 公共日志消息信号对象, 用于在类外部接收所有日志类的日志消息, 并带有控制台高亮
    - signal_all_message: 公共日志消息信号对象, 用于在类外部接收所有日志类的日志消息, 仅为消息内容
    - signal_trace: trace 级别公共日志消息信号对象, 用于在类外部接收 trace 级别的日志消息
    - signal_trace_color: trace 级别公共日志消息信号对象, 用于在类外部接收 trace 级别的日志消息, 并带有颜色高亮
    - signal_trace_console: trace 级别公共日志消息信号对象, 用于在类外部接收 trace 级别的日志消息, 并带有控制台高亮
    - signal_trace_message: trace 级别公共日志消息信号对象, 用于在类外部接收 trace 级别的日志消息, 仅为消息内容
    - signal_debug: debug 级别公共日志消息信号对象, 用于在类外部接收 debug 级别的日志消息
    - signal_debug_color: debug 级别公共日志消息信号对象, 用于在类外部接收 debug 级别的日志消息, 并带有颜色高亮
    - signal_debug_console: debug 级别公共日志消息信号对象, 用于在类外部接收 debug 级别的日志消息, 并带有控制台高亮
    - signal_debug_message: debug 级别公共日志消息信号对象, 用于在类外部接收 debug 级别的日志消息, 仅为消息内容
    - signal_info: info 级别公共日志消息信号对象, 用于在类外部接收 info 级别的日志消息
    - signal_info_color: info 级别公共日志消息信号对象, 用于在类外部接收 info 级别的日志消息, 并带有颜色高亮
    - signal_info_console: info 级别公共日志消息信号对象, 用于在类外部接收 info 级别的日志消息, 并带有控制台高亮
    - signal_info_message: info 级别公共日志消息信号对象, 用于在类外部接收 info 级别的日志消息, 仅为消息内容
    - signal_warning: warning 级别公共日志消息信号对象, 用于在类外部接收 warning 级别的日志消息
    - signal_warning_color: warning 级别公共日志消息信号对象, 用于在类外部接收 warning 级别的日志消息, 并带有颜色高亮
    - signal_warning_console: warning 级别公共日志消息信号对象, 用于在类外部接收 warning 级别的日志消息, 并带有控制台高亮
    - signal_warning_message: warning 级别公共日志消息信号对象, 用于在类外部接收 warning 级别的日志消息, 仅为消息内容
    - signal_error: error 级别公共日志消息信号对象, 用于在类外部接收 error 级别的日志消息
    - signal_error_color: error 级别公共日志消息信号对象, 用于在类外部接收 error 级别的日志消息, 并带有颜色高亮
    - signal_error_console: error 级别公共日志消息信号对象, 用于在类外部接收 error 级别的日志消息, 并带有控制台高亮
    - signal_error_message: error 级别公共日志消息信号对象, 用于在类外部接收 error 级别的日志消息, 仅为消息内容
    - signal_critical: critical 级别公共日志消息信号对象, 用于在类外部接收 critical 级别的日志消息
    - signal_critical_color: critical 级别公共日志消息信号对象, 用于在类外部接收 critical 级别的日志消息, 并带有颜色高亮
    - signal_critical_console: critical 级别公共日志消息信号对象, 用于在类外部接收 critical 级别的日志消息, 并带有控制台高亮
    - signal_critical_message: critical 级别公共日志消息信号对象, 用于在类外部接收 critical 级别的日志消息, 仅为消息内容

    方法:
    - set_log_group
    - append_log
    - remove_log
    - clear

    示例:

    Log = Logger('test')

    Log_2 = Logger('test_2')

    Log_gp = LoggerGroup()

    此时 Log_gp 即可获取到 Log 和 Log_2 的日志信息
    """
    __instance = None
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
            cls.__instance = super().__new__(cls)
            cls.__instance.__isInitialized = False
        return cls.__instance

    def __init__(
        self,
        log_folder_path: str = '',
        log_group: list = [],
        exclude_logs: list = [],
        size_limit: int = -1,  # KB
        files_limit: int = -1,
        days_limit: int = -1,
        split_by_day: bool = False,
        file_output: bool = True,
    ) -> None:
        if self.__isInitialized:
            # sys.stdout.write(f'\x1B[93m <Warning> LoggerGroup initialization is already complete. Reinitialization is invalid.\x1B[0m\n')
            return
        self.__isInitialized = True
        self.__doFileOutput = file_output if isinstance(file_output, bool) else True
        self.__start_time = datetime.now()
        self.__log_path = os.path.join(log_folder_path, _LOG_FOLDER_NAME) if log_folder_path else ''
        self.__isExistsPath = False
        if log_folder_path and os.path.exists(log_folder_path):
            self.__isExistsPath = True
        elif log_folder_path:
            raise FileNotFoundError(f'Log folder path "{log_folder_path}" does not exist, create it.')
        else:
            sys.stdout.write(
                f'\x1B[93m < WARNING > No File Output from \x1B[93;100m<LoggerGroup>\x1B[0m\n   \x1B[33m- No log file will be recorded because the log folder path is not specified. The current file path input is "{self.__log_path}". Type: {type(self.__log_path)}\x1B[0m\n')
        self.__isNewFile = True
        self.__size_limit = size_limit * 1000 if isinstance(size_limit, int) else -1
        self.__count_limit = files_limit if isinstance(files_limit, int) else -1
        self.__days_limit = days_limit if isinstance(days_limit, int) else -1
        self.__doSplitByDay = split_by_day if isinstance(split_by_day, bool) else False
        self.__log_folder_path = os.path.join(log_folder_path, _LOG_FOLDER_NAME)
        self.__current_size = 0
        self.__current_day = datetime.today().date()
        self.__log_group = []
        self.__exclude_logs = exclude_logs if isinstance(exclude_logs, list) else []
        self.__initialized = False
        self.__set_log_file_path()
        self.set_log_group(log_group)
        self.__clear_files()
        self.__initialized = True

    def set_log_group(self, log_group: list) -> None:
        if not isinstance(log_group, list):
            raise TypeError('log_group must be list')
        if self.__log_group == log_group and self.__initialized:
            return
        self.__log_group = log_group
        self.__disconnect(log_group)
        if log_group:
            self.__disconnect_all()
            self.__connection()
        else:
            self.__connect_all()

    def append_log(self, log_obj: Logger | list) -> None:
        if isinstance(log_obj, list | tuple):
            self.__log_group += list(log_obj)
            for log in list(log_obj):
                self.__connect_single(log)
        elif isinstance(log_obj, Logger):
            self.__log_group.append(log_obj)
            self.__connect_single(log_obj)
        else:
            raise TypeError(f'log_obj must be list or Logger, but got {type(log_obj)}')

    def remove_log(self, log_obj: Logger) -> None:
        if isinstance(log_obj, Logger):
            self.__log_group.remove(log_obj)
            self.__disconnect_single(log_obj)
        else:
            raise TypeError(f'log_obj must be Logger, but got {type(log_obj)}')
        if len(self.__log_group) == 0:
            self.__connect_all()

    def clear(self) -> None:
        self.__disconnect_all()
        self.__log_group: list = []
        self.__connect_all()

    def __connect_all(self) -> None:
        for log_obj in Logger.__instance_list__:
            log_obj: Logger
            if log_obj in self.__exclude_logs:
                continue
            self.__connect_single(log_obj)

    def __disconnect_all(self) -> None:
        for log_obj in Logger.__instance_list__:
            log_obj: Logger
            self.__disconnect_single(log_obj)

    def __connection(self) -> None:
        if not self.__log_group:
            return
        for log_obj in self.__log_group:
            log_obj: Logger
            if log_obj in self.__exclude_logs:
                continue
            self.__connect_single(log_obj)

    def __disconnect(self, log_group) -> None:
        for log_obj in self.__log_group:
            log_obj: Logger
            if log_obj in log_group:
                self.__disconnect_single(log_obj)

    def __set_log_file_path(self) -> None:
        """ 设置日志文件路径 """
        # 支持的字符 {}[];'',.!~@#$%^&()_+-=

        if self.__isExistsPath is False:
            return
        if not hasattr(self, f'_{self.__class__.__name__}__log_sub_folder_path'):  # 初始化, 创建属性
            self.__start_time_format = self.__start_time.strftime("%Y%m%d_%H'%M'%S")
            self.__log_sub_folder_path = os.path.join(self.__log_folder_path, _LOG_GROUP_FOLDER_NAME)
            if not os.path.exists(self.__log_sub_folder_path):
                os.makedirs(self.__log_sub_folder_path)
            self.__log_file_path = os.path.join(self.__log_sub_folder_path, f'Global_Log-[{self.__start_time_format}]--0.log')
        else:
            file_name = os.path.splitext(os.path.basename(self.__log_file_path))[0]
            str_list = file_name.split('--')
            self.__log_file_path = os.path.join(self.__log_sub_folder_path, f'{str_list[0]}--{int(str_list[-1]) + 1}.log')

    def __clear_files(self) -> None:
        """
        清理日志文件.
        """
        if self.__isExistsPath is False:
            return
        if (not isinstance(self.__count_limit, int) and self.__count_limit < 0) or (not isinstance(self.__days_limit, int) and self.__days_limit <= 0):
            return
        current_folder_path = os.path.join(self.__log_folder_path, _LOG_GROUP_FOLDER_NAME)
        if not os.path.exists(current_folder_path):
            return
        current_file_list = []
        for file in os.listdir(current_folder_path):
            fp = os.path.join(current_folder_path, file)
            if file.endswith('.log') and os.path.isfile(fp):
                current_file_list.append(fp)
        length_file_list = len(current_file_list)
        # 清理超过文件数量限制的文件
        if (isinstance(self.__count_limit, int) and self.__count_limit >= 0) and length_file_list > self.__count_limit:
            sorted_files = sorted(current_file_list, key=os.path.getctime)
            for file_path in sorted_files[:length_file_list - self.__count_limit]:
                os.remove(file_path)
        # 清理超过天数限制的文件
        elif isinstance(self.__days_limit, int) and self.__days_limit > 0:
            for file_path in current_file_list:
                if (datetime.today() - datetime.fromtimestamp(os.path.getctime(file_path))).days > self.__days_limit:
                    os.remove(file_path)

    def __write(self, message: str) -> None:
        """ 写入日志信息 """
        if not self.__doFileOutput or self.__isExistsPath is False:
            return
        if self.__size_limit and self.__size_limit > 0:
            # 大小限制
            writting_size = len(message.encode('utf-8'))
            self.__current_size += writting_size
            if self.__current_size >= self.__size_limit:
                self.__isNewFile = True
        if self.__doSplitByDay:
            # 按天分割
            if datetime.today().date() != self.__current_day:
                self.__isNewFile = True
        if self.__isNewFile:
            # 创建新文件
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
        if not os.path.exists(self.__log_folder_path):
            os.makedirs(self.__log_folder_path)
        if not os.path.exists(self.__log_sub_folder_path):
            os.makedirs(self.__log_sub_folder_path)
        with open(self.__log_file_path, 'a', encoding='utf-8') as f:
            f.write(message)

    def __connect_single(self, log_obj: Logger) -> None:
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

    def __disconnect_single(self, log_obj: Logger) -> None:
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


""" 
if __name__ == '__main__':
    Log = Logger('test', os.path.dirname(__file__), log_level='info', size_limit=1024, doSplitByDay=True)
    Log_1 = Logger('tests', os.path.dirname(__file__), log_sub_folder_name='test_folder', log_level='trace', size_limit=1024, doSplitByDay=True)
    Log.signal_debug_message.connect(print)
    Logger_group = LoggerGroup(os.path.dirname(__file__))
    logging.debug('hello world from logging debug')  # logging 跟踪示例
    logging.info('hello world from logging info')
    logging.error("This is a error message from logging.")
    logging.warning("This is a warning message from logging.")
    logging.critical("This is a critical message from logging.")
    Log.trace('This is a trace message.')
    Log.debug('This is a debug message.')
    Log_1.debug('This is a debug message.')
    Log.info('This is a info message.')
    Log_1.warning('This is a warning message.')
    Log.error('This is a error message.')
    Log_1.critical('This is a critical message.')
"""
