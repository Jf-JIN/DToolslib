import typing


def ansi_color_text(
    text: str | typing.Any,
    txt_color: int | None = None,
    bg_color: int | None = None,
    bold: bool = False,
    dim: bool = False,
    italic: bool = False,
    underline: bool = False,
    blink: bool = False,
) -> str:
    """
    Generates ANSI escape sequences for terminal control.

    - Args:
        - text (str): The text to be escaped.
        - txt_color (str, optional): The text color. Defaults to None.
        - bg_color (str, optional): The background color. Defaults to None.
        - bold (bool, optional): Whether it is a bold color. Defaults to False.
        - dim (bool, optional): Whether it is a dim color. Defaults to False.
        - italic (bool, optional): Whether it is an italic color. Defaults to False.
        - underline (bool, optional): Whether it is an underline color. Defaults to False.
        - blink (bool, optional): Whether it is a blink color. Defaults to False.

    - Returns:
        - str: The escaped text.

    - Recommands:
        - `BLACK` - `30` - `40`
        - `RED` - `31` - `41`
        - `GREEN` - `32` - `42`
        - `YELLOW` - `33` - `43`
        - `BLUE` - `34` - `44`
        - `PINK` - `35` - `45`
        - `CYAN` - `36` - `46`
        - `WHITE` - `37` - `47`
        - `GRAY` - `90` - `100`
        - `LIGHTRED` - `91` - `101`
        - `LIGHTGREEN` - `92` - `102`
        - `LIGHTYELLOW` - `93` - `103`
        - `LIGHTBLUE` - `94` - `104`
        - `LIGHTPINK` - `95` - `105`
        - `LIGHTCYAN` - `96` - `106`
        - `LIGHTWHITE` - `97` - `107`

    """
    style_list: list = []
    style_list.append('1') if bold else ''  # 粗体
    style_list.append('2') if dim else ''  # 暗色
    style_list.append('3') if italic else ''  # 斜体
    style_list.append('4') if underline else ''  # 下划线
    style_list.append('5') if blink else ''  # 闪烁
    style_list.append(str(txt_color)) if isinstance(txt_color, int) else ''  # 字体颜色
    style_list.append(str(bg_color)) if isinstance(bg_color, int) else ''  # 背景颜色
    style_str: str = ';'.join(item for item in style_list if item)
    ct: str = f'\x1B[{style_str}m{text}\x1B[0m' if style_str else text
    return ct


def html_color_text(
    text: str,
    txt_color: str | None = None,
    bg_color: str | None = None,
    bold: bool = False,
    dim: bool = False,
    italic: bool = False,
    underline: bool = False,
    blink: bool = False,
) -> str:
    """
    Generates an HTML color tag for the given text and style options.

    - Args:
        - text: The text to be styled.
        - txt_color: The text color.
        - bg_color: The background color.
        - bold: Whether the text should be bold.
        - dim: Whether the text should be dimmed.
        - italic: Whether the text should be italic.
        - underline: Whether the text should be underlined.
        - blink: Whether the text should be blinking.

    - Returns:
        - str: The HTML color tag for the given text and style options.


    - Recommands:
        - `BLACK` - `#010101`
        - `RED` - `#DE382B`
        - `GREEN` - `#39B54A`
        - `YELLOW` - `#FFC706`
        - `BLUE` - `#006FB8`
        - `PINK` - `#762671`
        - `CYAN` - `#2CB5E9`
        - `WHITE` - `#CCCCCC`
        - `GRAY` - `#808080`
        - `LIGHTRED` - `#FF0000`
        - `LIGHTGREEN` - `#00FF00`
        - `LIGHTYELLOW` - `#FFFF00`
        - `LIGHTBLUE` - `#0000FF`
        - `LIGHTPINK` - `#FF00FF`
        - `LIGHTCYAN` - `#00FFFF`
        - `LIGHTWHITE` - `#FFFFFF`
    """
    style_list: list = []
    style_list.append('color: ' + txt_color) if txt_color else ''
    style_list.append('background-color: ' + bg_color) if bg_color else ''
    style_list.append('font-weight: bold') if bold else ''
    style_list.append('font-style: italic') if italic else ''
    style_list.append('text-decoration: underline') if underline else ''
    style_list.append('opacity: 0.7;animation: blink 1s step-end infinite') if blink else ''
    style_str: str = ';'.join(item for item in style_list if item) + ';'
    output_text: str = (f'<span style="{style_str}">{text}</span>').replace('\n', '<br>')
    pre_blick_text = '<style > @keyframes blink{50% {opacity: 50;}}</style>'
    output_text = pre_blick_text + output_text if blink else output_text
    return output_text
