#!/bin/sh -ex

# cleans a potentially failed previous test run
[ -f tmp/pid ] && [ -d /proc/$(cat tmp/pid) ] && kill $(cat tmp/pid)
[ -d tmp/ ] && rm -rf tmp/

# creates tmp directory
mkdir tmp

# starts the mock server
cd mock
python3 -m http.server &
echo $! > ../tmp/pid
sleep 1
cd ..

# initializes zebr0 configuration
zebr0-init -c tmp -u http://localhost:8000 -p dummy_project -s dummy_stage

# test dry output before run
../src/zebr0-script -c tmp -d tmp/history run test-ok --dry > tmp/dry_before
diff tmp/dry_before results/dry_before

# test first run
../src/zebr0-script -c tmp -d tmp/history run test-ok > tmp/first_run
diff tmp/first_run results/first_run
diff tmp/history/f4fc192a9bb717d392c21bda92b930ba results/history/f4fc192a9bb717d392c21bda92b930ba
diff tmp/history/2e319d8e37e1a0293ab8680413aba8b1 results/history/2e319d8e37e1a0293ab8680413aba8b1
diff tmp/history/33d97341f7e26ce567dce8c078d26f74 results/history/33d97341f7e26ce567dce8c078d26f74
diff tmp/history/55802db65c9fe6f2e052fb91b56f3249 results/history/55802db65c9fe6f2e052fb91b56f3249
diff tmp/history/c11bd38dad44c0074dbb5b7ea6a9e8ae results/history/c11bd38dad44c0074dbb5b7ea6a9e8ae
diff tmp/lookup mock/lookup

# test dry output after run
../src/zebr0-script -c tmp -d tmp/history run test-ok --dry > tmp/dry_after
diff tmp/dry_after results/dry_after

# test second run
../src/zebr0-script -c tmp -d tmp/history run test-ok > tmp/second_run
diff tmp/second_run results/second_run

# test script ko
../src/zebr0-script -c tmp -d tmp/history run test-ko-script > tmp/ko-script || true
diff tmp/ko-script results/ko-script

# test lookup ko
../src/zebr0-script -c tmp -d tmp/history run test-ko-lookup > tmp/ko-lookup || true
diff tmp/ko-lookup results/ko-lookup

# stops the mock server in a few seconds, to make the following test fail
echo "sleep 2 && kill $(cat tmp/pid) && rm tmp/pid" | at now

# test connection ko
../src/zebr0-script -c tmp -d tmp/history run test-ko-connection > tmp/ko-connection-dirty || true
sed "s/0x.*>/0xFFFF>/g" tmp/ko-connection-dirty > tmp/ko-connection-clean
diff tmp/ko-connection-clean results/ko-connection-clean

# cleans tmp directory
rm -rf tmp
