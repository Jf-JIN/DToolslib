from DToolslib import StaticEnum


class TestEnum(StaticEnum, enable_member_attribute=True):
    A = '#ff0000'
    A.color_name = 'Red'
    A.ansi_font = 31
    A.ansi_background = 41
    B: int
    C: int
    D = None

    class TestEnum2(StaticEnum):
        a = 1
        b = 3
        AA = '#ff00ff'
        BB: int
        CC: int

    class TestEnum3:
        AAA = '#00ff00'
        BBB: int
