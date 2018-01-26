#!/bin/sh -ex

# starts the mock server
cd mock
python3 -m http.server &
pid=$!
sleep 1
cd ..

# creates tmp directory
mkdir tmp

# test dry output before run
sudo ../src/idem run test --dry > tmp/dry_before
diff tmp/dry_before results/dry_before

# test first run
sudo ../src/idem run test --retry > tmp/first_run
diff tmp/first_run results/first_run
diff tmp/idem/f4fc192a9bb717d392c21bda92b930ba results/idem/f4fc192a9bb717d392c21bda92b930ba
diff tmp/idem/55802db65c9fe6f2e052fb91b56f3249 results/idem/55802db65c9fe6f2e052fb91b56f3249
diff tmp/idem/de6b9dad18c35dbf9108396facfcf879 results/idem/de6b9dad18c35dbf9108396facfcf879
diff tmp/idem/2e319d8e37e1a0293ab8680413aba8b1 results/idem/2e319d8e37e1a0293ab8680413aba8b1
diff tmp/idem/33d97341f7e26ce567dce8c078d26f74 results/idem/33d97341f7e26ce567dce8c078d26f74
diff tmp/resource mock/resources/include/resource

# test dry output after run
sudo ../src/idem run test --dry > tmp/dry_after
diff tmp/dry_after results/dry_after

# test second run
sudo ../src/idem run test > tmp/second_run
diff tmp/second_run results/second_run

# stops the mock server
kill ${pid}

# cleans tmp directory
sudo rm -rf tmp
