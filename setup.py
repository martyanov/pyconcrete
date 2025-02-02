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

import os
import sys
import hashlib
import sysconfig
from os.path import join
from distutils.core import setup, Extension, Command
from distutils.dist import Distribution
from distutils.command.build import build
from distutils.command.build_ext import build_ext
from distutils.command.clean import clean
from distutils.command.install import install
from src.config import TEST_DIR, SRC_DIR, EXT_SRC_DIR, EXE_SRC_DIR, SECRET_HEADER_PATH

version = '0.13.0'


# .rst should created by pyconcrete-admin
if os.path.exists('README.rst'):
    readme_path = 'README.rst'
else:
    readme_path = 'README.md'
with open(readme_path, 'r') as f:
    readme = f.read()


def hash_key(key):
    factor = sum([s for s in key])
    factor %= 128
    if factor < 16:
        factor += 16

    m = hashlib.md5()
    m.update(key)
    k = m.digest()

    return k, factor


def create_secret_key_header(key, factor):
    # reference from - http://stackoverflow.com/questions/1356896/how-to-hide-a-string-in-binary-code
    # encrypt the secret key in binary code
    # avoid to easy read from HEX view

    key_val_lst = []
    for i, k in enumerate(key):
        key_val_lst.append("(0x%X ^ (0x%X - %d))" % (k, factor, i))
    key_val_code = ", ".join(key_val_lst)

    code = """
        #define SECRET_NUM 0x%X
        #define SECRET_KEY_LEN %d
        static const unsigned char* GetSecretKey()
        {
            unsigned int i = 0;
            static unsigned char key[] = {%s, 0/* terminal char */};
            static int is_encrypt = 1/*true*/;
            if( is_encrypt )
            {
                for(i = 0 ; i < SECRET_KEY_LEN ; ++i)
                {
                    key[i] = key[i] ^ (SECRET_NUM - i);
                }
                is_encrypt = 0/*false*/;
            }
            return key;
        }
    """ % (factor, len(key), key_val_code)

    with open(SECRET_HEADER_PATH, 'w') as f:
        f.write(code)


def remove_secret_key_header():
    if os.path.exists(SECRET_HEADER_PATH):
        os.remove(SECRET_HEADER_PATH)


class ExeDistribution(Distribution):
    exe_modules = ()

    def has_exe_modules(self):
        return self.exe_modules and len(self.exe_modules) > 0


# ================================================= command ================================================= #


class CmdBase:
    def pre_process(self):
        self.manual_create_secrete_key_file = not os.path.exists(SECRET_HEADER_PATH)
        if self.manual_create_secrete_key_file:
            if not self.passphrase:
                self.passphrase = input("please input the passphrase \nfor encrypt your python script (enter for default) : \n")
                if len(self.passphrase) == 0:
                    self.passphrase = DEFAULT_KEY
                else:
                    passphrase2 = input("please input again to confirm\n")
                    if self.passphrase != passphrase2:
                        raise Exception("Passphrase is different")

            k, f = hash_key(self.passphrase.encode('utf8'))
            create_secret_key_header(k, f)

    def post_process(self):
        if self.manual_create_secrete_key_file:
            remove_secret_key_header()


class BuildEx(CmdBase, build):
    """
    execute extra function before/after build.run()
    """
    user_options = build.user_options + [('passphrase=', None, 'specify passphrase')]

    def initialize_options(self):
        build.initialize_options(self)
        self.passphrase = None

    def run(self):
        self.pre_process()
        ret = build.run(self)
        self.post_process()
        return ret


class BuildExe(CmdBase, build_ext):
    """
    execute extra function before/after build.run()
    """
    user_options = build.user_options + [('passphrase=', None, 'specify passphrase')]

    def initialize_options(self):
        build_ext.initialize_options(self)
        self.passphrase = None
        self.build_scripts = None

    def finalize_options(self):
        build_ext.finalize_options(self)
        self.set_undefined_options('build',
                                   ('build_scripts', 'build_scripts'))
        self.extensions = self.distribution.exe_modules

    def run(self):
        self.pre_process()
        build_ext.run(self)
        self.post_process()

    def build_extensions(self):
        """
        copy from distutils/command/build_ext.py build_ext.build_extensions
        just override build_extensions for covert the compiler setup from build_ext.run()
        """
        ext = self.extensions[0]  # only one exe extension

        macros = ext.define_macros[:]
        for undef in ext.undef_macros:
            macros.append((undef,))

        objects = self.compiler.compile(
            list(ext.sources),
            output_dir=self.build_temp,
            include_dirs=ext.include_dirs,
            macros=macros,
            debug=self.debug,
            depends=ext.depends)

        self._built_objects = objects[:]

        # link for executable file
        self.compiler.link_executable(
            objects,
            ext.name,
            libraries=self.get_libraries(ext),
            library_dirs=ext.library_dirs,
            runtime_library_dirs=ext.runtime_library_dirs,
            extra_postargs=ext.extra_link_args,
            output_dir=self.build_scripts,  # should not use build_lib, it will be copied to python site-packages
            debug=self.debug)


class InstallEx(CmdBase, install):
    """
    execute extra function before/after install.run()
    """
    user_options = install.user_options + [('passphrase=', None, 'specify passphrase')]
    sub_commands = install.sub_commands + [('build_exe', lambda self: True)]

    def initialize_options(self):
        install.initialize_options(self)
        self.passphrase = None
        self.build_scripts = None

    def finalize_options(self):
        install.finalize_options(self)
        self.set_undefined_options('build',
                                   ('build_scripts', 'build_scripts'))

    def _clean_build(self):
        c = clean(self.distribution)
        c.all = True
        c.finalize_options()
        c.run()

    def run(self):
        self._clean_build()

        self.pre_process()
        ret = install.run(self)
        self.install_exe()
        self.post_process()
        self.create_pth()
        return ret

    def create_pth(self):
        """
        create pyconcrete.pth for automatic import pyconcrete after python launched
        """
        # setup(
        #     data_files=(sysconfig.get_python_lib(), 'pyconcrete.pth'),
        #     ...
        # )
        # it will got wrong result in ubuntu, get_python_lib got /usr/lib
        # but pyconcrete installed in /usr/local/lib
        #
        # get install_libbase to avoid this issue
        filename = join(self.install_libbase, 'pyconcrete.pth')
        with open(filename, 'w') as f:
            f.write('import pyconcrete')
        print('creating %s' % filename)

    def install_exe(self):
        # install `pyconcrete` to /usr/local/bin
        exe_name = 'pyconcrete'
        self.copy_file(os.path.join(self.build_scripts, exe_name),
                       os.path.join(self.install_scripts, exe_name))

# ================================================= test command ================================================= #


class TestEx(Command):
    description = "Running all unit test for pyconcrete"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import unittest
        suite = unittest.TestLoader().discover(TEST_DIR)
        unittest.TextTestRunner(verbosity=2).run(suite)


# ================================================= extension ================================================= #

def get_include_dirs():
    openaes_include_dirs = [
        join(EXT_SRC_DIR),
        join(EXT_SRC_DIR, 'openaes', 'inc'),
    ]

    return openaes_include_dirs


def get_libraries(include_python_lib=False):
    libraries = []

    # PEP 3149 -- ABI version tagged .so files
    # link python lib may be: `-l python3.3` or `-l python3.6m`
    # reference link: https://www.python.org/dev/peps/pep-3149/
    link_py_fmt = 'python{version}{abiflags}'
    abiflags = getattr(sys, 'abiflags', '')
    link_py = link_py_fmt.format(
        version=sysconfig.get_python_version(),
        abiflags=abiflags,
    )

    if include_python_lib:
        libraries.append(link_py)

    return libraries


include_dirs = get_include_dirs()
openaes_sources = [
    join(EXT_SRC_DIR, 'openaes', 'src', 'oaes_base64.c'),
    join(EXT_SRC_DIR, 'openaes', 'src', 'oaes_lib.c'),
]

ext_module = Extension(
    'pyconcrete._pyconcrete',
    include_dirs=include_dirs,
    libraries=get_libraries(include_python_lib=False),
    sources=[
        join(EXT_SRC_DIR, 'pyconcrete.c'),
        join(EXT_SRC_DIR, 'pyconcrete_module.c'),
    ] + openaes_sources,
)

exe_module = Extension(
    'pyconcrete',
    include_dirs=include_dirs,
    libraries=get_libraries(include_python_lib=True),
    define_macros=[('PYCONCRETE_VERSION', '"%s"' % version)],
    sources=[
        join(EXE_SRC_DIR, 'pyconcrete_exe.c'),
        join(EXT_SRC_DIR, 'pyconcrete.c'),
    ] + openaes_sources,
)

# ================================================= setup ================================================= #


setup(
    name='pyconcrete',
    version=version,
    description='Protect your python script, encrypt it as .pye and decrypt when import it',
    long_description=readme,
    keywords='python source encryption obfuscation',
    author='Falldog',
    author_email='falldog7@gmail.com',
    url='https://github.com/Falldog/pyconcrete',
    license="Apache License 2.0",
    ext_modules=[ext_module],
    exe_modules=[exe_module],
    cmdclass={
        "build": BuildEx,
        "build_exe": BuildExe,
        "install": InstallEx,
        "test": TestEx,
    },
    scripts=[
        'pyconcrete-admin.py',
    ],
    packages=[
        'pyconcrete',
    ],
    package_dir={
        '': SRC_DIR,
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Security',
        'Topic :: Security :: Cryptography',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: Implementation :: CPython',
        'License :: OSI Approved :: Apache Software License',
    ],
    distclass=ExeDistribution,
)
