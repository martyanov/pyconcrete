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

from os.path import join, abspath, dirname, pardir

DEFAULT_KEY = 'secret-key'

ROOT_DIR = abspath(join(dirname(__file__), pardir))
TEST_DIR = 'test'
SRC_DIR = join('src')
PY_SRC_DIR = join(SRC_DIR, 'pyconcrete')
EXT_SRC_DIR = join(SRC_DIR, 'pyconcrete_ext')
EXE_SRC_DIR = join(SRC_DIR, 'pyconcrete_exe')
SECRET_HEADER_PATH = join(EXT_SRC_DIR, 'secret_key.h')
