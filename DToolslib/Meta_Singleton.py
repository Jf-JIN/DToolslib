
""" 
单例模式元类
"""


class SingletonMeta(type):
    """ 
    单例模式元类
    """
    __instances = None

    def __call__(cls, *args, **kwargs):
        if not cls.__instances:
            cls.__instances = super().__call__(*args, **kwargs)
        return cls.__instances
