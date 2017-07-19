#!/bin/sh -ex

# cleans previous build
rm -rf build/

# for each project in src/
for project in $(ls src); do
  if [ -d src/$project ]; then

    # creates a corresponding directory in build/
    mkdir -p build/$project

    # and for each profile in the project directory
    for profile in $(ls src/$project); do
      # concat the base files with the specific one to form a standalone script
      dest=build/$project/$profile
      cp src/header.sh $dest
      cat src/idem.sh >> $dest
      cat src/footer.sh >> $dest
      cat src/$project/$profile >> $dest
    done
  fi
done

# tests
# cleans previous failed test run if exists
rm -rf test/
mkdir test

# first run
cat build/test/test.sh | sh > test/result_1
cmp test/result_1 resources/test/stdout_1
cmp test/fe55a42ae7273e7639b20454362c85ab resources/test/md5

# second run
cat build/test/test.sh | sh > test/result_2
cmp test/result_2 resources/test/stdout_2

# cleans successful test run
rm -rf test/
