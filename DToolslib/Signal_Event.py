from typing import Callable


class _RealSignal:
    __name__: str = 'EventSignal'
    __qualname__: str = 'EventSignal'

    def __init__(self, types, owner, name, isClassSignal=False) -> None:
        if all([isinstance(typ, (type, tuple)) for typ in types]):
            self.__types = types
        else:
            raise TypeError('types must be a tuple of types')
        self.__owner = owner
        self.__name = name
        self.__isClassSignal: bool = isClassSignal
        self.__slots = []

    def connect(self, slot: 'EventSignal' | Callable) -> None:
        if callable(slot):
            if slot not in self.__slots:
                self.__slots.append(slot)
        elif isinstance(slot, _RealSignal):
            self.__slots.append(slot.emit)
        else:
            raise ValueError('Slot must be callable')

    def disconnect(self, slot: 'EventSignal' | Callable) -> None:
        if slot in self.__slots:
            self.__slots.remove(slot)

    def emit(self, *args, **kwargs) -> None:
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
        return f'<Signal EventSignal {self.__name} of {owner_repr} at 0x{id(self.__owner):016X}>'

    def __repr__(self) -> str:
        return f"\n{self.__str__()}\n    - slots:{self.__slots}\n"

    def __del__(self) -> None:
        self.__slots.clear()


class EventSignal:
    def __init__(self, *types, signal_scope='instance') -> None:
        self.types = types
        self.__scope = signal_scope

    def __get__(self, instance, instance_type) -> _RealSignal:
        if instance is None:
            return self
        else:
            if self.__scope == 'class':
                return self.__handle_class_signal(instance_type)
            else:
                return self.__handle_instance_signal(instance)

    def __set__(self, instance, value) -> None:
        raise AttributeError('LogSignal is read-only, cannot be set')

    def __set_name__(self, instance, name) -> None:
        self.__name = name

    def __handle_class_signal(self, instance_type) -> _RealSignal:
        if not hasattr(instance_type, '__class_signals__'):
            instance_type.__class_signals__ = {}
        if self not in instance_type.__class_signals__:
            instance_type.__class_signals__[self] = _RealSignal(
                self.types,
                instance_type,
                self.__name,
                isClassSignal=True
            )
        return instance_type.__class_signals__[self]

    def __handle_instance_signal(self, instance) -> _RealSignal:
        if not hasattr(instance, '__signals__'):
            instance.__signals__ = {}
        if self not in instance.__signals__:
            instance.__signals__[self] = _RealSignal(
                self.types,
                instance,
                self.__name
            )
        return instance.__signals__[self]


if __name__ == '__main__':
    class Test:
        signal_instance_a = EventSignal(int)
        signal_instance_b = EventSignal(str, int)
        signal_class = EventSignal(str, int, signal_scope='class')
    a = Test()
    b = Test()
    print(f'[a.signal_instance_a] id: {id(a.signal_instance_a)}')
    print(f'[b.signal_instance_a] id: {id(b.signal_instance_a)}')
    print(f'Are they identical? {a.signal_instance_a is b.signal_instance_a}\n')
    print(f'[a.signal_class] id: {id(a.signal_class)}')
    print(f'[b.signal_class] id: {id(b.signal_class)}')
    print(f'Are they identical? {a.signal_class is b.signal_class}')
    print(type(a.signal_class))
