# -e stands for "error" stop the script if there are errors
# -x print contents of the script as it runs it
set -ex
curl -sfS http://127.0.0.1:8080/ > /dev/null
curl -sfS http://127.0.0.1:8080/login > /dev/null
curl -sfS http://127.0.0.1:8080/logout > /dev/null