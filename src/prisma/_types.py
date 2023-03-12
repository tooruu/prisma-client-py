from __future__ import annotations

from typing import Callable, Coroutine, TypeVar, Type, Tuple, Any, Mapping
from pydantic import BaseModel
from typing_extensions import (
    TypeGuard as TypeGuard,
    TypedDict as TypedDict,
    Protocol as Protocol,
    Literal as Literal,
    get_args as get_args,
    runtime_checkable as runtime_checkable,
)

Method = Literal['GET', 'POST']

CallableT = TypeVar('CallableT', bound='FuncType')
BaseModelT = TypeVar('BaseModelT', bound=BaseModel)

# TODO: use a TypeVar everywhere
FuncType = Callable[..., object]
CoroType = Callable[..., Coroutine[Any, Any, object]]


@runtime_checkable
class InheritsGeneric(Protocol):
    __orig_bases__: Tuple['_GenericAlias']


class _GenericAlias(Protocol):
    __origin__: Type[object]


# Note: not exhaustively defined, there may be other fields
class ErrorResponse(TypedDict, total=False):
    user_facing_error: UserFacingError


class UserFacingError(TypedDict, total=False):
    error_code: str
    message: str
    meta: Mapping[str, object]
