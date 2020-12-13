#!/bin/sh -ex

# cleans a potentially failed previous test run
[ -f tmp/pid ] && [ -d /proc/$(cat tmp/pid) ] && kill $(cat tmp/pid)
[ -d tmp/ ] && rm -rf tmp/

# creates tmp directory
mkdir tmp

# starts the mock server
cd mock-json
python3 -m http.server &
echo $! > ../tmp/pid
sleep 1
cd ..

# initializes zebr0 configuration
../zebr0-setup -f tmp/zebr0.conf -u http://localhost:8000 -l dummy_project dummy_stage

# test dry output before run
../zebr0-script -f tmp/zebr0.conf -d tmp/history run test-ok --dry > tmp/dry_before
diff tmp/dry_before results/dry_before

# test first run
../zebr0-script -f tmp/zebr0.conf -d tmp/history run test-ok > tmp/first_run
diff tmp/first_run results/first_run
diff tmp/history/2e319d8e37e1a0293ab8680413aba8b1 results/history/2e319d8e37e1a0293ab8680413aba8b1
diff tmp/history/33d97341f7e26ce567dce8c078d26f74 results/history/33d97341f7e26ce567dce8c078d26f74
diff tmp/history/55802db65c9fe6f2e052fb91b56f3249 results/history/55802db65c9fe6f2e052fb91b56f3249
diff tmp/history/7e9bf2c7ba05d0323c2cd592d06094c8 results/history/7e9bf2c7ba05d0323c2cd592d06094c8
diff tmp/history/e2e406ee41e39a849d0f307143ff2e67 results/history/e2e406ee41e39a849d0f307143ff2e67
diff tmp/history/f4fc192a9bb717d392c21bda92b930ba results/history/f4fc192a9bb717d392c21bda92b930ba
diff tmp/dir/lookup mock-json/lookup

# test dry output after run
../zebr0-script -f tmp/zebr0.conf -d tmp/history run test-ok --dry > tmp/dry_after
diff tmp/dry_after results/dry_after

# test second run
../zebr0-script -f tmp/zebr0.conf -d tmp/history run test-ok > tmp/second_run
diff tmp/second_run results/second_run

# test script ko
../zebr0-script -f tmp/zebr0.conf -d tmp/history run test-ko-script > tmp/ko-script || true
diff tmp/ko-script results/ko-script

# test lookup ko
../zebr0-script -f tmp/zebr0.conf -d tmp/history run test-ko-lookup > tmp/ko-lookup || true
#diff tmp/ko-lookup results/ko-lookup

# stops the mock server in a few seconds, to make the following test fail
echo "sleep 2 && kill $(cat tmp/pid) && rm tmp/pid" | at now

# test connection ko
../zebr0-script -f tmp/zebr0.conf -d tmp/history run test-ko-connection > tmp/ko-connection-dirty || true
sed "s/0x.*>/0xFFFF>/g" tmp/ko-connection-dirty > tmp/ko-connection-clean
#diff tmp/ko-connection-clean results/ko-connection-clean
diff tmp/history/33ea634aeb8bb8ba6c648f7d1cb42538 results/history/33ea634aeb8bb8ba6c648f7d1cb42538

# cleans tmp directory
rm -rf tmp
