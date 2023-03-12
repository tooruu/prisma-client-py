from __future__ import annotations

import sys
from types import ModuleType
from functools import lru_cache
from typing import Type, TypeVar, cast
from typing_extensions import TypedDict

from pydantic import BaseModel, Extra, create_model_from_typeddict
from pydantic.typing import is_typeddict

from ._types import Protocol, runtime_checkable


__all__ = ('validate',)

# NOTE: we should use bound=TypedDict but mypy does not support this
T = TypeVar('T')


class Config:
    extra: Extra = Extra.forbid


@runtime_checkable
class CachedModel(Protocol):
    __pydantic_model__: BaseModel


def _get_module(typ: type[object]) -> ModuleType:
    return sys.modules[typ.__module__]


@lru_cache(maxsize=None)
def patch_pydantic() -> None:
    """Pydantic does not resolve forward references for TypedDict types properly yet

    see https://github.com/samuelcolvin/pydantic/pull/2761
    """
    from pydantic import annotated_types

    create_model = annotated_types.create_model_from_typeddict

    def patched_create_model(
        typeddict_cls: type[TypedDict], **kwargs: object
    ) -> Type[BaseModel]:
        kwargs.setdefault('__module__', typeddict_cls.__module__)
        return create_model(typeddict_cls, **kwargs)

    annotated_types.create_model_from_typeddict = patched_create_model


def validate(type: Type[T], data: object) -> T:
    """Validate untrusted data matches a given TypedDict

    For example:

    from prisma import validate, types
    from prisma.models import User

    def user_create_handler(data: object) -> None:
        validated = validate(types.UserCreateInput, data)
        user = await User.prisma().create(data=validated)
    """
    # avoid patching pydantic until we know we need to in case our
    # monkey patching fails
    patch_pydantic()

    if not is_typeddict(type):
        raise TypeError(
            f'Only TypedDict types are supported, got: {type} instead.'
        )

    # we cannot use pydantic's builtin type -> model resolver
    # as we need to be able to update forward references
    if isinstance(type, CachedModel):
        # cache the model on the type object, mirroring how pydantic works
        # mypy thinks this is unreachable, we know it isn't, just ignore
        model = type.__pydantic_model__  # type: ignore[unreachable]
    else:
        # pyright is more strict than mypy here, we also don't care about the
        # incorrectly inferred type as we have verified that the given type
        # is indeed a TypedDict
        model = create_model_from_typeddict(
            type, __config__=Config  # pyright: ignore[reportGeneralTypeIssues]
        )
        model.update_forward_refs(**vars(_get_module(type)))
        type.__pydantic_model__ = model  # type: ignore

    instance = model.parse_obj(data)
    return cast(T, instance.dict(exclude_unset=True))
