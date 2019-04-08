# ========================================================================== #
#                                                                            #
#    KVMD - The main Pi-KVM daemon.                                          #
#                                                                            #
#    Copyright (C) 2018  Maxim Devaev <mdevaev@gmail.com>                    #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU General Public License as published by    #
#    the Free Software Foundation, either version 3 of the License, or       #
#    (at your option) any later version.                                     #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU General Public License for more details.                            #
#                                                                            #
#    You should have received a copy of the GNU General Public License       #
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.  #
#                                                                            #
# ========================================================================== #


import json

from typing import Tuple
from typing import List
from typing import Dict
from typing import Callable
from typing import Optional
from typing import Any


# =====
class ConfigError(ValueError):
    pass


# =====
def build_raw_from_options(options: List[str]) -> Dict[str, Any]:
    raw: Dict[str, Any] = {}
    for option in options:
        (key, value) = (option.split("=", 1) + [None])[:2]  # type: ignore
        if len(key.strip()) == 0:
            raise ConfigError("Empty option key (required 'key=value' instead of %r)" % (option))
        if value is None:
            raise ConfigError("No value for key %r" % (key))

        section = raw
        subs = list(map(str.strip, key.split("/")))
        for sub in subs[:-1]:
            section.setdefault(sub, {})
            section = section[sub]
        section[subs[-1]] = _parse_value(value)
    return raw


def _parse_value(value: str) -> Any:
    value = value.strip()
    if (
        not value.isdigit()
        and value not in ["true", "false", "null"]
        and not value.startswith(("{", "[", "\""))
    ):
        value = "\"%s\"" % (value)
    return json.loads(value)


# =====
class Section(dict):
    def __init__(self) -> None:
        dict.__init__(self)
        self.__meta: Dict[str, Dict[str, Any]] = {}

    def _unpack(self, _section: Optional["Section"]=None) -> Dict[str, Any]:
        if _section is None:
            _section = self
        unpacked: Dict[str, Any] = {}
        for (key, value) in _section.items():
            if isinstance(value, Section):
                unpacked[key] = value._unpack()  # pylint: disable=protected-access
            else:  # Option
                unpacked[_section._get_unpack_as(key)] = value  # pylint: disable=protected-access
        return unpacked

    def _set_meta(self, key: str, default: Any, unpack_as: str, help: str) -> None:  # pylint: disable=redefined-builtin
        self.__meta[key] = {
            "default": default,
            "unpack_as": unpack_as,
            "help": help,
        }

    def _get_default(self, key: str) -> Any:
        return self.__meta[key]["default"]

    def _get_unpack_as(self, key: str) -> str:
        return (self.__meta[key]["unpack_as"] or key)

    def _get_help(self, key: str) -> str:
        return self.__meta[key]["help"]

    def __getattribute__(self, key: str) -> Any:
        if key in self:
            return self[key]
        else:  # For pickling
            return dict.__getattribute__(self, key)


class Option:
    __type = type

    def __init__(
        self,
        default: Any,
        type: Optional[Callable[[Any], Any]]=None,  # pylint: disable=redefined-builtin
        only_if: str="",
        unpack_as: str="",
        help: str="",  # pylint: disable=redefined-builtin
    ) -> None:

        self.default = default
        self.type: Callable[[Any], Any] = (type or (self.__type(default) if default is not None else str))  # type: ignore
        self.only_if = only_if
        self.unpack_as = unpack_as
        self.help = help

    def __repr__(self) -> str:
        return "<Option(default={0.default}, type={0.type}, only_if={0.only_if}, unpack_as={0.unpack_as})>".format(self)


# =====
def make_config(raw: Dict[str, Any], scheme: Dict[str, Any], _keys: Tuple[str, ...]=()) -> Section:
    if not isinstance(raw, dict):
        raise ConfigError("The node %r must be a dictionary" % ("/".join(_keys) or "/"))

    config = Section()

    def make_full_key(key: str) -> Tuple[str, ...]:
        return _keys + (key,)

    def make_full_name(key: str) -> str:
        return "/".join(make_full_key(key))

    def process_option(key: str, no_only_if: bool=False) -> Any:
        if key not in config:
            option: Option = scheme[key]
            only_if = option.only_if
            only_if_negative = option.only_if.startswith("!")
            if only_if_negative:
                only_if = only_if[1:]

            if only_if and no_only_if:  # pylint: disable=no-else-raise
                # Перекрестный only_if запрещен
                raise RuntimeError("Found only_if recursuon on key %r" % (make_full_name(key)))
            elif only_if and (
                (not only_if_negative and not process_option(only_if, no_only_if=True))
                or (only_if_negative and process_option(only_if, no_only_if=True))
            ):
                # Если есть условие и оно ложно - ставим дефолт и не валидируем
                value = option.default
            else:
                value = raw.get(key, option.default)
                try:
                    value = option.type(value)
                except ValueError as err:
                    raise ConfigError("Invalid value %r for key %r: %s" % (value, make_full_name(key), str(err)))

            config[key] = value
            config._set_meta(  # pylint: disable=protected-access
                key=key,
                default=option.default,
                unpack_as=option.unpack_as,
                help=option.help,
            )
        return config[key]

    for key in scheme:
        if isinstance(scheme[key], Option):
            process_option(key)
        elif isinstance(scheme[key], dict):
            config[key] = make_config(raw.get(key, {}), scheme[key], make_full_key(key))
        else:
            raise RuntimeError("Incorrect scheme definition for key %r:"
                               " the value is %r, not dict() or Option()" % (make_full_name(key), type(scheme[key])))
    return config