import gc, weakref
from DToolslib.Signal_Event import EventSignal


def test_memory_leak_0():
    """测试EventSignal内存泄漏"""

    class TestClass:
        signal = EventSignal(str)

    def create_test_instance():
        obj = TestClass()
        obj.signal.connect(lambda x: print(x))
        return weakref.ref(obj)

    for i in range(100):
        weak_ref = create_test_instance()
        gc.collect()

        if weak_ref() is not None:
            print(f"第{i + 1}次测试：内存泄漏！实例未被释放")

        bound_signals = [obj for obj in gc.get_objects()
                         if hasattr(obj, '__class__') and 'BoundSignal' in obj.__class__.__name__]
        print(f"第{i + 1}次测试：存活BoundSignal数量: {len(bound_signals)}")


test_memory_leak_0()


def test_memory_leak_1():
    class TestClass:
        signal = EventSignal(str)

    def create_instance():
        obj = TestClass()
        obj.signal.connect(lambda x: x)
        return weakref.ref(obj)

    refs = [create_instance() for _ in range(100)]
    gc.collect()

    for i, r in enumerate(refs):
        if r() is not None:
            print(f"第{i + 1}次测试：内存泄漏！实例未被释放")

        alive_bound = [o for o in gc.get_objects() if hasattr(o, '__class__') and 'BoundSignal' in o.__class__.__name__]
        print(f"第{i + 1}次测试: 存活BoundSignal数量: {len(alive_bound)}")


test_memory_leak_1()
