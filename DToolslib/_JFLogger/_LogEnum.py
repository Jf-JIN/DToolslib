from DToolslib import StaticEnum
from DToolslib.Color_Text import *
import typing


class LogLevel(StaticEnum):
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
                print(log_level.upper(), log_level.upper() in LogLevel)
                raise ValueError(f'<ERROR> Log level "{log_level}" is not a valid log level.')
        elif isinstance(log_level, (int, float)):
            normalized_log_level = abs(log_level // 10 * 10)
        else:
            raise ValueError(f'<ERROR> Log level "{log_level}" is not a valid log level. It should be a string or a number.')
        return normalized_log_level


class LogHighlightType(StaticEnum):
    """ Highlight type enumeration class """
    ANSI = 'ANSI'
    HTML = 'HTML'
    NONE = None


class _Log_Default(StaticEnum):
    """ This class represents the default log level enumeration. """
    GROUP_FOLDER_NAME = '#Global_Log'
    HISTORY_FOLDER_NAME = '#History_Log'
    LIST_RESERVE_NAME = [GROUP_FOLDER_NAME, HISTORY_FOLDER_NAME]
    ROOT_FOLDER_NAME = 'Logs'

    # MESSAGE_FORMAT =  '%(consoleLine)s\n[%(asctime)s] [log: %(logName)s] [module: %(moduleName)s] [class: %(className)s] [function: %(functionName)s] [line: %(lineNum)s]- %(levelName)s\n%(message)s\n'

    # MESSAGE_FORMAT = '%(consoleLine)s\n[%(asctime)s] [log: %(logName)s] [thread: %(threadName)s] [%(moduleName)s::%(className)s.%(functionName)s] [line: %(lineNum)s] - %(levelName)s\n%(message)s\n'

    MESSAGE_FORMAT = '%(consoleLine)s\n[%(asctime)s] [%(logName)s] [%(processName)s | %(threadName)s | %(moduleName)s::%(className)s.%(functionName)s] - %(levelName)s\n%(message)s\n'


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


class _ColorMap(StaticEnum):
    """ This class represents the color map enumeration. """
    BLACK = _ColorMapItem('BLACK', 30, 40, '#010101')
    RED = _ColorMapItem('RED', 31, 41, '#DE382B')
    GREEN = _ColorMapItem('GREEN', 32, 42, '#39B54A')
    YELLOW = _ColorMapItem('YELLOW', 33, 43, '#FFC706')
    BLUE = _ColorMapItem('BLUE', 34, 44, '#006FB8')
    PINK = _ColorMapItem('PINK', 35, 45, '#762671')
    CYAN = _ColorMapItem('CYAN', 36, 46, '#2CB5E9')
    WHITE = _ColorMapItem('WHITE', 37, 47, '#CCCCCC')
    GRAY = _ColorMapItem('GRAY', 90, 100, '#808080')
    LIGHTRED = _ColorMapItem('LIGHTRED', 91, 101, '#FF0000')
    LIGHTGREEN = _ColorMapItem('LIGHTGREEN', 92, 102, '#00FF00')
    LIGHTYELLOW = _ColorMapItem('LIGHTYELLOW', 93, 103, '#FFFF00')
    LIGHTBLUE = _ColorMapItem('LIGHTBLUE', 94, 104, '#0000FF')
    LIGHTPINK = _ColorMapItem('LIGHTPINK', 95, 105, '#FF00FF')
    LIGHTCYAN = _ColorMapItem('LIGHTCYAN', 96, 106, '#00FFFF')
    LIGHTWHITE = _ColorMapItem('LIGHTWHITE', 97, 107, '#FFFFFF')


class _LogMessageItem(object):
    """ This class is used to store the log message item. """

    def __init__(self, title, text='', font_color=None, background_color=None, dim=False, bold=False, italic=False, underline=False, blink=False, highlight_type=None) -> None:
        self.__title = title
        self.__color_font: _ColorMapItem = font_color
        self.__color_background: _ColorMapItem = background_color
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
        text_color: _ColorMapItem = self.__color_font
        background_color: _ColorMapItem = self.__color_background
        ansi_text_color = text_color.ANSI_TXT if text_color else ''
        ansi_background_color = background_color.ANSI_BG if background_color else ''
        self.__text_color = self.__colorize_text(self.__text, text_color, background_color, self.__bold, self.__dim, self.__italic, self.__underline, self.__blink)
        self.__text_console = ansi_color_text(text, ansi_text_color, ansi_background_color, self.__bold, self.__dim, self.__italic, self.__underline, self.__blink)

    def __colorize_text(self, text: str, text_color: _ColorMapItem, background_color: _ColorMapItem, *args, highlight_type=None, **kwargs) -> str:
        if highlight_type is None:
            highlight_type = self.__highlight_type
            if highlight_type is None:
                return text
        if highlight_type == LogHighlightType.ANSI:
            text_color = text_color.ANSI_TXT if isinstance(text_color, _ColorMapItem) else text_color
            background_color = background_color.ANSI_BG if isinstance(background_color, _ColorMapItem) else background_color
            return ansi_color_text(text, text_color, background_color, *args, **kwargs)
        elif highlight_type == LogHighlightType.HTML:
            text_color = text_color.HEX if isinstance(text_color, _ColorMapItem) else text_color
            background_color = background_color.HEX if isinstance(background_color, _ColorMapItem) else background_color
            return html_color_text(text, text_color, background_color, *args, **kwargs)
        return text

    def set_highlight_type(self, highlight_type: LogHighlightType) -> None:
        self.__highlight_type: LogHighlightType = highlight_type
