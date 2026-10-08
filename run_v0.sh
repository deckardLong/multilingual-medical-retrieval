#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"                    
mkdir -p workspace/runs

START="${START:-s1}"                     
steps=(s1_chunk s2_embed s3_retrieve s4_rerank s5_select s6_build_submit s7_validate)
go=0
for s in "${steps[@]}"; do
  [[ "$s" == "$START"* ]] && go=1
  if [[ $go -eq 1 ]]; then
    echo "=== $s  $(date +%H:%M:%S) ==="
    python "src/$s.py"
  fi
done
echo "Xong. File nộp: workspace/runs/submission.zip"