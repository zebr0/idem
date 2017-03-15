#!/bin/sh
set -ex

# cleans previous build
rm -rf build/

# for each project in src/
for project in $(ls src); do
  if [ -d src/$project ]; then

    # creates a corresponding directory in build/
    mkdir -p build/$project

    # and for each profile in the project directory
    for profile in $(ls src/$project); do
      # concat the base file with the specific one to form a standalone script
      cp src/idem.sh build/$project/$profile
      cat src/$project/$profile >> build/$project/$profile
    done
  fi
done

# tests
# cleans previous failed test run if exists
rm -rf test/
mkdir test

# first run
cat build/common/test.sh | IDEM_DIR=./test sh > test/result_1
cmp test/result_1 resources/common/test_stdout_1
cmp test/fe55a42ae7273e7639b20454362c85ab resources/common/test_md5

# second run
cat build/common/test.sh | IDEM_DIR=./test sh > test/result_2
cmp test/result_2 resources/common/test_stdout_2

# cleans successful test run
rm -rf test/
