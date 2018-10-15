#!/bin/sh -ex

# cleans a potentially failed previous test run
[ -f tmp/pid ] && kill $(cat tmp/pid)
[ -d tmp/ ] && sudo rm -rf tmp/

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
sudo ../src/zebr0-script -c tmp -d tmp/history run test --dry > tmp/dry_before
diff tmp/dry_before results/dry_before

# test first run
sudo ../src/zebr0-script -c tmp -d tmp/history run test > tmp/first_run
diff tmp/first_run results/first_run
diff tmp/history/f4fc192a9bb717d392c21bda92b930ba results/history/f4fc192a9bb717d392c21bda92b930ba
diff tmp/history/2e319d8e37e1a0293ab8680413aba8b1 results/history/2e319d8e37e1a0293ab8680413aba8b1
diff tmp/history/33d97341f7e26ce567dce8c078d26f74 results/history/33d97341f7e26ce567dce8c078d26f74
diff tmp/history/55802db65c9fe6f2e052fb91b56f3249 results/history/55802db65c9fe6f2e052fb91b56f3249

# test dry output after run
sudo ../src/zebr0-script -c tmp -d tmp/history run test --dry > tmp/dry_after
diff tmp/dry_after results/dry_after

# test second run
sudo ../src/zebr0-script -c tmp -d tmp/history run test > tmp/second_run
diff tmp/second_run results/second_run

# stops the mock server
kill $(cat tmp/pid) && rm tmp/pid

# cleans tmp directory
sudo rm -rf tmp
