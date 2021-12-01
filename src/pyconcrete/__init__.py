# Copyright 2015 Falldog Hsieh <falldog7@gmail.com>
# Modifications copyright 2021 Andrey Martyanov <andrey@martyanov.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from importlib._bootstrap_external import (
    FileFinder,
    PathFinder,
    SourcelessFileLoader,
    _classify_pyc,
    _compile_bytecode,
)

from . import _pyconcrete

EXT_PY  = '.py'
EXT_PYC = '.pyc'
EXT_PYD = '.pyd'
EXT_PYE = '.pye'

__all__ = ["info"]


info = _pyconcrete.info
encrypt_file = _pyconcrete.encrypt_file
decrypt_file = _pyconcrete.decrypt_file
decrypt_buffer = _pyconcrete.decrypt_buffer


class PyeFileLoader(SourcelessFileLoader):

    def get_code(self, fullname):
        path = self.get_filename(fullname)
        data = self.get_data(path)

        # Descrypt the module
        data = decrypt_buffer(data)

        # Call _classify_pyc to do basic validation of the pyc but ignore the
        # result. There's no source to check against.
        exc_details = {
            'name': fullname,
            'path': path,
        }
        _classify_pyc(data, fullname, exc_details)
        return _compile_bytecode(
            memoryview(data)[16:],
            name=fullname,
            bytecode_path=path,
        )


class PyeFileFinder(FileFinder):

    def __init__(self, path, *loader_details):
        loader_details += ([PyeFileLoader, [EXT_PYE]],)
        super().__init__(path, *loader_details)


class PyePathFinder(PathFinder):

    @classmethod
    def find_spec(cls, fullname, path: None, target: None):
        if path is None:
            path = sys.path

        spec = None

        for entry in path:
            spec = PyeFileFinder(entry).find_spec(fullname, target)

            if spec is None:
                continue

            if spec.origin is None:
                spec = None
                break

            if spec is not None:
                break

        return spec


sys.meta_path.insert(0, PyePathFinder())
