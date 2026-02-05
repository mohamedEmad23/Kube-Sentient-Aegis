#!/usr/bin/env bash
set -euo pipefail

context="${KUBE_CONTEXT:-minikube}"
output="${KUBE_DOCKER_CONFIG:-deploy/docker/kubeconfig-docker.yaml}"

tmp="$(mktemp)"

kubectl config view --raw --minify --context "${context}" -o yaml > "${tmp}"

python - "${tmp}" "${output}" <<'PY'
import os
import pathlib
import re
import sys

src = pathlib.Path(sys.argv[1])
dst = pathlib.Path(sys.argv[2])

text = src.read_text()
home = os.path.expanduser("~")
text = text.replace(f"{home}/.minikube", "/home/aegis/.minikube")
text = re.sub(r"https://(127\\.0\\.0\\.1|localhost):(\\d+)", r"https://host.docker.internal:\\2", text)

dst.parent.mkdir(parents=True, exist_ok=True)
dst.write_text(text)
PY

rm -f "${tmp}"

echo "Wrote ${output}"
