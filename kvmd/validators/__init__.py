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


import re

from typing import List
from typing import Mapping
from typing import Sequence
from typing import Callable
from typing import NoReturn
from typing import Union
from typing import Any


# =====
class ValidatorError(ValueError):
    pass


# =====
def raise_error(arg: Any, name: str, hide: bool=False) -> NoReturn:
    arg_str = " "
    if not hide:
        arg_str = (" %r " if isinstance(arg, (str, bytes)) else " '%s' ") % (arg)
    raise ValidatorError("The argument" + arg_str + "is not a valid " + name)


def check_not_none(arg: Any, name: str) -> Any:
    if arg is None:
        raise ValidatorError("Empty argument is not a valid %s" % (name))
    return arg


def check_not_none_string(arg: Any, name: str, strip: bool=True) -> str:
    arg = str(check_not_none(arg, name))
    if strip:
        arg = arg.strip()
    return arg


def check_in_list(arg: Any, name: str, variants: Union[Sequence, Mapping]) -> Any:
    if arg not in variants:
        raise_error(arg, name)
    return arg


def check_string_in_list(arg: Any, name: str, variants: Union[Sequence[str], Mapping[str, Any]], lower: bool=True) -> Any:
    arg = check_not_none_string(arg, name)
    if lower:
        arg = arg.lower()
    return check_in_list(arg, name, variants)


def check_re_match(arg: Any, name: str, pattern: str, strip: bool=True, hide: bool=False) -> str:
    arg = check_not_none_string(arg, name, strip=strip)
    if re.match(pattern, arg, flags=re.MULTILINE) is None:
        raise_error(arg, name, hide=hide)
    return arg


def check_any(arg: Any, name: str, validators: List[Callable[[Any], Any]]) -> Any:
    for validator in validators:
        try:
            return validator(arg)
        except Exception:
            pass
    raise_error(arg, name)