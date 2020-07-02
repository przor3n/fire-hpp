
"""
    Copyright Kristjan Kongas 2020

    Boost Software License - Version 1.0 - August 17th, 2003

    Permission is hereby granted, free of charge, to any person or organization
    obtaining a copy of the software and accompanying documentation covered by
    this license (the "Software") to use, reproduce, display, distribute,
    execute, and transmit the Software, and to prepare derivative works of the
    Software, and to permit third-parties to whom the Software is furnished to
    do so, all subject to the following:

    The copyright notices in the Software and this entire statement, including
    the above license grant, this restriction and the following disclaimer,
    must be included in all copies of the Software, in whole or in part, and
    all derivative works of the Software, unless such copies or derivative
    works are solely in the form of machine-executable object code generated by
    a source language processor.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE, TITLE AND NON-INFRINGEMENT. IN NO EVENT
    SHALL THE COPYRIGHT HOLDERS OR ANYONE DISTRIBUTING THE SOFTWARE BE LIABLE
    FOR ANY DAMAGES OR OTHER LIABILITY, WHETHER IN CONTRACT, TORT OR OTHERWISE,
    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.
"""

import json
import argparse
from pathlib import Path
import os, shutil, subprocess, sys

description = """Batch-test combinations of compilers and cmake settings. CMake root directory needs to contain a file called `.release_tests.json`. Example contents:
{
  "compiler_prefix": "/usr/bin/",
  "compilers": [
    {"cc": "gcc", "cxx": "g++", "standards": [11, 14, 17, 20]},
    {"cc": "clang", "cxx": "clang++", "standards": [11, 14, 17, 20]},
    {"generator": "Unix Makefiles", "standards": [11, 14, 17, 20]}
  ],
  "cmake_build_types": ["Debug", "", "Release"]
}

"""

def main():
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("cmake_root")

    args = parser.parse_args()
    json_path = Path(args.cmake_root) / ".release_tests.json"
    with open(json_path, "r") as json_file:
        setup = json.load(json_file)
        try:
            batch_test(args.cmake_root, setup.get("compiler_prefix"), setup["compilers"], setup["cmake_build_types"])
        except KeyboardInterrupt:
            print("Tests interrupted")

    clear_cmake_cache()


def batch_test(cmake_root, prefix, compilers, cmake_build_types):
    for comp in compilers:
        assert ("cc" in comp and "cxx" in comp) or "generator" in comp

        print()
        print()
        if "cc" in comp and "cxx" in comp:
            print("Testing {} and {}".format(comp["cc"], comp["cxx"]))
        if "generator" in comp:
            print("Testing {}".format(comp["generator"]))
        print()
        for standard in comp["standards"]:
            for build_type in cmake_build_types:
                print_build = "Default" if build_type == "" else build_type
                print("Testing " + print_build + " mode, C++" + str(standard))

                clear_cmake_cache()

                # Build and test
                cmd = [
                    "cmake", cmake_root,
                    "-D", "CMAKE_CXX_STANDARD=" + str(standard),
                    "-D", "CMAKE_BUILD_TYPE=" + build_type
                ]

                env = dict(os.environ)
                if "cc" in comp and "cxx" in comp:
                    env.update({"CC": str(Path(prefix) / comp["cc"]), "CXX": str(Path(prefix) / comp["cxx"])})
                if "generator" in comp:
                    env.update({"CMAKE_GENERATOR": comp["generator"]})

                run(cmd, env=env)
                run(["cmake", "--build", "."])
                run(["python3", "tests/run_standard_tests.py"])

    print()
    print("++++++++++        SUCCESS        ++++++++++")
    print()


def run(cmd, env=None):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if result.returncode != 0:
        print("STDOUT:")
        print(str(result.stdout, "utf-8"))
        print()
        print("STDERR:")
        print(str(result.stderr, "utf-8"))
        print()
        print()
        print("----------        FAILURE        ----------")
        print()
        sys.exit(1)


def clear_cmake_cache():
    for dir_path, _, files in os.walk("."):
        if dir_path[-len("CMakeLists"):] == "CMakeLists":
            shutil.rmtree(dir_path)
        for file in files:
            if file == "CMakeCache.txt":
                os.remove(Path(dir_path) / file)


if __name__ == "__main__":
    main()
