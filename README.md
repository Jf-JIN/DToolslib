# DToolslib

A simple and complex tool library containing multiple tool scripts
一个简单且杂的工具库, 包含多个工具脚本

### StaticEnum

An enumeration library, supported
一个枚举类库, 支持:

- Unique variables (not repetitively named)
  唯一变量(不可重复命名)
- Value cannot be modified
  值不可修改
- Custom properties
  自定义属性
- Keep the original type (except None, Boolean), you can use `isinstance` to judge
  保留原类型(None, Boolean 除外), 可以使用 `isinstance` 判断
- It can be read directly, and there is no need to use its `value` property. Of course, it can also use `value`
  可以直接读取, 不需要使用其 `value` 属性, 当然也可以使用 `value`

###### How to use | 使用方法

```python
class TestEnum(StaticEnum):
    # __allow_new_attr__ = True  # Allow new attributes to be added outside the class | 允许类外部添加新属性
    A = '#ff0000'
    A.color_name = 'Red'
    A.ansi_font = 31
    A.ansi_background = 41

print(TestEnum.A)  # output: #ff0000
print(TestEnum.A.name)  # output: A
print(TestEnum.A.color_name)  # output: Red
print(TestEnum.A.ansi_font)  # output: 31
print(type(TestEnum.A))  # output: <class '__main__.SEString'>
print('#ff0000' in TestEnum)  # output: True
print(isinstance(TestEnum.A, str))  # output: True
```

### EventSignal

Imitating the mechanism of Qt's signal and slot, custom signals, this signal can be used out of the Qt framework. There is currently no thread locking and asynchronous mechanism, which supports:
模仿于 Qt 的信号和槽的机制, 自定义的信号, 该信号可以脱离 Qt 框架使用, 目前没有线程锁和异步的机制, 支持:

- Instance signal (default) 
  实例信号(默认)
- Class signals
  类信号
- Attribute protection, the signal cannot be assigned
  属性保护, 信号不可被赋值

###### How to use | 使用方法

```python
class Test:
    signal_instance_a = EventSignal(str)  # Instance Signal
    signal_instance_b = EventSignal(str, int)  # Instance Signal
    signal_class = EventSignal(str, int, signal_scope='class')  # Class Signal
a = Test()
b = Test()
b.signal_instance_a.connect(print)
a.signal_instance_b.connect(b.signal_instance_a)
b.signal_instance_a.emit('This is a test message')
a.signal_instance_a.disconnect(b.signal_instance_a)
# output: This is a test message
print(a.signal_class is b.signal_class)  # output: True
print(a.signal_instance_a is b.signal_instance_a)  # output: False
print(type(a.signal_class))  # output: <class '__main__.EventSignal'>
print(a.__signals__)  # output: {...} a dict with 2 keys, the values are signal instances. You can also see the slots of the signal.
print(a.__class_signals__)  # output: {...} a dict with 1 keys, the values are signal instances. You can also see the slots of the signal.
```

### Logger

Logger, see docstring for details, support:
日志器, 详见 docstring, 支持:

- Clean old logs before startup to define the total number of retained
  启动前清理旧日志, 可定义保留总数
  
- Size splitting
  大小分割
  
- Days segmentation
  天数分割
  
- Function traceability exclusion, class traceability exclusion, module traceability exclusion, for example: Exclude func1 function under ClassA class (assuming the relationship chain is: ClassA->func3->func2->func1), then log positioning will be located to func2
  
  
  
  函数追溯排除, 类追溯排除, 模块追溯排除, 例如: 排除 `ClassA` 类下的 `func1` 函数(假设关系链为:  `ClassA->func3->func2->func1` ), 则日志定位将定位到`func2`
  
- Output highlight styles and terminal color styles. After setting, you can obtain HTML style information through the signal.
  输出高亮样式, 终端彩色样式. 设置后, 可以通过信号获取 HTML 样式的信息
  
- Can track logging output
  可跟踪 logging 输出
  
- Can be output with a signal
  可通过信号针对性输出

###### How to use | 使用方法

```python
Log = Logger('test', os.path.dirname(__file__), log_level='info', size_limit=1024, doSplitByDay=True)
Log.signal_debug_message.connect(print)
logging.debug('hello world from logging debug') # logging tracking example
Log.trace('This is a trace message.')
Log.debug('This is a debug message.')
Log.info('This is a info message.')
Log.warning('This is a warning message.')
Log.error('This is a error message.')
Log.critical('This is a critical message.')
```

### LoggerGroup

Logger group, see docstring for details, support
日志器组, 详见 docstring, 支持

- Size splitting
  大小分割
- Days segmentation
  天数分割
- All Logger information is automatically collected by default, and it can also be manually changed to specify a few Loggers.
  默认自动收集所有 Logger 信息, 也可以手动更改为指定某几个 Logger
- Output highlight style, same Logger
  输出高亮样式, 同 Logger
- Can be output with a signal
  可通过信号针对性输出
- Singleton mode
  单例模式

###### How to use | 使用方法

```python
Log = Logger('test', os.path.dirname(__file__), log_level='info', size_limit=1024, doSplitByDay=True)
Log_1 = Logger('tests', os.path.dirname(__file__), log_sub_folder_name='test_folder', log_level='trace', size_limit=1024, doSplitByDay=True)
Logger_group = LoggerGroup(os.path.dirname(__file__))
Log.info('This is a info message.')
Log_1.warning('This is a warning message.')
Log.error('This is a error message.')
Log_1.critical('This is a critical message.')
```

### SingletonMeta

Singleton pattern metaclass
单例模式元类

###### How to use | 使用方法

```python
class Test(metaclass=SingletonMeta):
	...
a = Test()
b = Test()
print(a is b) # output: True
```

### Inner_Decorators

Interior Decorators
内部装饰器

- `try_except_log`: Capture errors and output them to logs. The function needs to be improved and is not recommended
                    捕捉报错并输出给日志, 功能有待完善, 不推荐使用
- `boundary_check`: Function/method boundary check, not tested
                    函数/方法边界检查, 未测试
- `time_counter`: Calculate the function/method run time and print it
                    计算函数/方法运行时间, 并打印
- `who_called_me`: Get the call tree
                    获取调用树

# 版本信息 Version Info

#### v0.0.1.4

* The new logger supports the exclusion of combined function names (such as `ClassA.func1`). Currently, only first-level combinations are supported, that is, the most recent class to which the method belongs must be consistent with the current class at the time of call.
        新增日志器支持对组合函数名(如 `ClassA.func1`)的排除. 目前仅支持一级组合, 即方法所属的最近一级类必须与调用时的当前类一致. 
* Fixed the issue that StaticEnum could add new properties outside, as well as the bug in data type errors in multi-layer nested classes inside.
        修复 StaticEnum 可在外部新增属性的问题, 以及内部多层嵌套类的数据类型错误的 bug. 
* Changed the way data types are converted in the StaticEnum metaclass, changed from the previous eval to created with the class.
        更改了 StaticEnum 元类中转换数据类型的方式, 从之前的eval更改为用类创建. 

