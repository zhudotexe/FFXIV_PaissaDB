import asyncio
import functools
from typing import Callable, TypeVar

_ArgsT = TypeVar("_ArgsT")  # todo(3.10): ParamSpec https://docs.python.org/3/library/typing.html#typing.ParamSpec
_ReturnT = TypeVar("_ReturnT")


async def executor(func: Callable[[_ArgsT], _ReturnT], *args: _ArgsT, **kwargs: _ArgsT) -> _ReturnT:
    return await asyncio.get_running_loop().run_in_executor(None, functools.partial(func, *args, **kwargs))
