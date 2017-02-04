#!/bin/bash
# not the best way to go, but it will do for now

# cleans previous build
rm -rf build

# for each project in src/
for project in $(ls src); do
  if [ -d src/$project ]; then

    # creates a corresponding directory in build
    mkdir -p build/$project

    # and for each profile in the project directory
    for profile in $(ls src/$project); do
      # concat the base file with the specific one to form an standalone script
      cp src/bashible.sh build/$project/$profile
      cat src/$project/$profile >> build/$project/$profile
    done
  fi
done
