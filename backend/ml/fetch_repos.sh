#!/bin/sh
# Shallow-clone (last 4000 commits) the repositories used to build the training set.
mkdir -p ml/data/repos && cd ml/data/repos || exit 1
while read -r r; do
  [ -z "$r" ] && continue
  d=$(basename "$r")
  [ -d "$d/.git" ] || git clone -q --depth 4000 "https://github.com/$r.git" "$d"
done < ../../repos.txt
