Setting up MLIR

```powershell
# Make sure your 'python' is what you expect. Note that on multi-python
# systems, this may have a version suffix, and on many Linuxes and MacOS where
# python2 and python3 co-exist, you may also want to use `python3`.
which python
python -m venv ~/.venv/mlirdev
source ~/.venv/mlirdev/bin/activate

# Note that many LTS distros will bundle a version of pip itself that is too
# old to download all of the latest binaries for certain platforms.
# The pip version can be obtained with `python -m pip --version`, and for
# Linux specifically, this should be cross checked with minimum versions
# here: https://github.com/pypa/manylinux
# It is recommended to upgrade pip:
python -m pip install --upgrade pip


# Now the `python` command will resolve to your virtual environment and
# packages will be installed there.
python -m pip install -r mlir/python/requirements.txt

# Now run your build command with `cmake`, `ninja`, et al.
# MAKE SURE THE CWD IS repo/build!
mkdir build
cd build

# USING BACKSLASHES IN FILE PATHS WILL CAUSE AN ERROR
cmake ..\llvm -G "Visual Studio 17 2022" -DLLVM_ENABLE_PROJECTS="mlir" -DLLVM_TARGETS_TO_BUILD="Native" -DCMAKE_BUILD_TYPE=Release -Thost=x64 -DLLVM_ENABLE_ASSERTIONS=ON -DMLIR_ENABLE_BINDINGS_PYTHON=ON -DPython3_EXECUTABLE="C:/Users/hunta/AppData/Local/Programs/Python/Python312/python.EXE"

# -- Alternative for WSL2
cmake -G Ninja ../llvm -DLLVM_ENABLE_PROJECTS=mlir -DLLVM_BUILD_EXAMPLES=ON -DLLVM_TARGETS_TO_BUILD="Native;NVPTX;AMDGPU" -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_ASSERTIONS=ON -DMLIR_ENABLE_BINDINGS_PYTHON=ON -DPython3_EXECUTABLE="/home/ant13731-wsl/GitHub/llvm-project/.venv/bin/python"

cmake --build . --target check-mlir -j 28
cmake --build . -j 28

# Need to build with release to get binaries (warning: takes a very long time). Then add the Release/bin folder to PATH
cmake --build . -j 28 --config Release

# Run mlir tests. For example, to run python bindings tests only using ninja:
ninja check-mlir-python

# export PYTHONPATH=$(cd build && pwd)/tools/mlir/python_packages/mlir_core
export PYTHONPATH=$(pwd)/tools/mlir/python_packages/mlir_core
export PYTHONPATH=$PYTHONPATH:~/GitHub/llvm-project/build/tools/mlir/python_packages/mlir_core
```
