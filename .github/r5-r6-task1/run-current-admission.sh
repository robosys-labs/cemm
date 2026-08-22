#!/usr/bin/env bash
set -euo pipefail

REPO_DIR=${1:?candidate repository path required}
CONTROL_DIR=${2:?control repository path required}
PARENT_SHA=ca4816bc892d14e7eb593f00977309e2031f131b
TRIGGER_SHA=5d3523f54223285e26b4d315cd5dbe176aabc1f3
SOURCE_SHA=8fc96895513dd4305f0737a98319782a1f5aa0f7
SOURCE_TREE=bb073e594f9aa09d50a59882def2fd7bf551297e
CANDIDATE_BRANCH=agent/r5-r6-task1-r4-current-admission-candidate-20260822
TARGET_BRANCH=agent/r4-task4-batch-publisher-20260816
CANDIDATE_REF=refs/heads/${CANDIDATE_BRANCH}
TARGET_REF=refs/heads/${TARGET_BRANCH}
PATCH_B64=${CONTROL_DIR}/.github/r5-r6-task1/source-owner-repair.patch.gz.b64
EVIDENCE_DIR=/tmp/r5-r6-task1-evidence
BUILD_A=/tmp/r5-r6-task1-build-a
BUILD_B=/tmp/r5-r6-task1-build-b
mkdir -p "${EVIDENCE_DIR}"

export PYTHONDONTWRITEBYTECODE=1
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export PYTHONHASHSEED=0
export PYTHONPATH=src/cemm_authoritative_hybrid:src:scripts:.

remote_sha() {
  git -C "${REPO_DIR}" ls-remote origin "$1" | cut -f1
}

push_candidate_if_at() {
  local expected=$1
  local desired=$2
  local actual
  actual=$(remote_sha "${CANDIDATE_REF}")
  if [[ "${actual}" == "${desired}" ]]; then
    return 0
  fi
  [[ "${actual}" == "${expected}" ]] || {
    echo "candidate branch moved: expected ${expected} or ${desired}, got ${actual}" >&2
    exit 1
  }
  git -C "${REPO_DIR}" push \
    --force-with-lease="${CANDIDATE_REF}:${expected}" \
    origin "${desired}:${CANDIDATE_REF}"
  [[ "$(remote_sha "${CANDIDATE_REF}")" == "${desired}" ]]
}

assert_outcome() {
  local path=$1 phase=$2 tier=$3 owner=${4:-}
  python - "$path" "$phase" "$tier" "$owner" <<'PY'
import json
from pathlib import Path
import sys
path, phase, tier, owner = sys.argv[1:]
value = json.loads(Path(path).read_text(encoding="utf-8"))
assert value["phase"] == phase, value
assert value["tier"] == tier, value
assert value["disposition"] == "passed", value
assert value["fresh"] is True, value
if owner:
    assert value["owner"] == owner, value
PY
}

# Exact trigger and control surfaces.
[[ "$(git -C "${REPO_DIR}" rev-parse HEAD)" == "${TRIGGER_SHA}" ]]
[[ "$(git -C "${REPO_DIR}" rev-parse HEAD^)" == "${PARENT_SHA}" ]]
printf '%s\n' '.github/r5-r6-task1/current-admission-trigger.json' > /tmp/task1-trigger-path
git -C "${REPO_DIR}" diff --name-only "${PARENT_SHA}" "${TRIGGER_SHA}" | sort > /tmp/task1-trigger-actual
diff -u /tmp/task1-trigger-path /tmp/task1-trigger-actual
[[ "$(git -C "${REPO_DIR}" hash-object .github/r5-r6-task1/current-admission-trigger.json)" == "950d485c5859182c54192fb1d6950e45e9659412" ]]
[[ "$(git -C "${CONTROL_DIR}" merge-base "${PARENT_SHA}" HEAD)" == "${PARENT_SHA}" ]]
printf '%s\n' \
  '.github/r5-r6-task1/run-current-admission.sh' \
  '.github/r5-r6-task1/source-owner-repair.patch.gz.b64' \
  '.github/workflows/r5-r6-task1-current-admission.yml' | sort > /tmp/task1-control-expected
git -C "${CONTROL_DIR}" diff --name-only "${PARENT_SHA}" HEAD | sort > /tmp/task1-control-actual
diff -u /tmp/task1-control-expected /tmp/task1-control-actual
[[ "$(sha256sum "${PATCH_B64}" | cut -d' ' -f1)" == "97322ae51aa45628b2db1411a7a485f89d3c87cd12766df8fa1fa17fa18c327f" ]]

# Reconstruct the exact four-file source-owner repair.
git -C "${REPO_DIR}" checkout --detach "${PARENT_SHA}"
base64 --decode "${PATCH_B64}" > /tmp/r5-task1-source-repair.patch.gz
[[ "$(sha256sum /tmp/r5-task1-source-repair.patch.gz | cut -d' ' -f1)" == "3da80dd034149133e35c1b65c235f5c9902052ccfe76d09bc6f0065285b08492" ]]
gzip -dc /tmp/r5-task1-source-repair.patch.gz > /tmp/r5-task1-source-repair.patch
[[ "$(sha256sum /tmp/r5-task1-source-repair.patch | cut -d' ' -f1)" == "ca83b4e32acdd6a7525c12eb3a84db03cf583fa5f2519afec0a894ad0356a6c0" ]]
git -C "${REPO_DIR}" apply --check /tmp/r5-task1-source-repair.patch
git -C "${REPO_DIR}" apply /tmp/r5-task1-source-repair.patch
printf '%s\n' \
  'hybrid_mvp/artifacts/validation/R5_TEST_DISPOSITIONS.json' \
  'hybrid_mvp/artifacts/validation/TEST_INVENTORY_RECEIPT.json' \
  'hybrid_mvp/tests/test_r4_admission.py' \
  'hybrid_mvp/tests/test_r4_validation_gate.py' | sort > /tmp/task1-source-paths
git -C "${REPO_DIR}" diff --name-only | sort > /tmp/task1-source-actual
diff -u /tmp/task1-source-paths /tmp/task1-source-actual
git -C "${REPO_DIR}" diff --check

git -C "${REPO_DIR}" config user.name 'CEMM Verification Bot'
git -C "${REPO_DIR}" config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git -C "${REPO_DIR}" add -- $(cat /tmp/task1-source-paths)
GIT_AUTHOR_NAME='CEMM Verification Bot' \
GIT_AUTHOR_EMAIL='41898282+github-actions[bot]@users.noreply.github.com' \
GIT_AUTHOR_DATE='2026-08-22T13:00:00+01:00' \
GIT_COMMITTER_NAME='CEMM Verification Bot' \
GIT_COMMITTER_EMAIL='41898282+github-actions[bot]@users.noreply.github.com' \
GIT_COMMITTER_DATE='2026-08-22T13:00:00+01:00' \
  git -C "${REPO_DIR}" commit --no-gpg-sign -m 'test(r4): migrate admission owners to ABI-4'
[[ "$(git -C "${REPO_DIR}" rev-parse HEAD)" == "${SOURCE_SHA}" ]]
[[ "$(git -C "${REPO_DIR}" rev-parse 'HEAD^{tree}')" == "${SOURCE_TREE}" ]]
[[ -z "$(git -C "${REPO_DIR}" status --short --untracked-files=all)" ]]
push_candidate_if_at "${TRIGGER_SHA}" "${SOURCE_SHA}"

cd "${REPO_DIR}/hybrid_mvp"
python scripts/verify_r3_r4_test_metadata.py | tee "${EVIDENCE_DIR}/metadata.txt"
python scripts/generate_r5_test_dispositions.py --check artifacts/validation/R5_TEST_DISPOSITIONS.json
for phase in G0 R1 R2 R3 R4 R5; do
  python scripts/check_test_inventory.py --phase "${phase}" --source-only \
    > "${EVIDENCE_DIR}/inventory-${phase}.json"
done
python scripts/check_r3_r4_structure.py | tee "${EVIDENCE_DIR}/structure.txt"
python scripts/audit_legacy_test_hard_cut.py | tee "${EVIDENCE_DIR}/legacy-audit.json"
python scripts/update_replay_status.py --verify-chain | tee "${EVIDENCE_DIR}/pre-status.txt"
python -m pytest \
  tests/test_r4_validation_gate.py::test_r4_admission_evidence_policy_is_sorted_and_unique \
  -q -p no:cacheprovider

# Two independent authentic builds from the exact repaired source.
rm -rf "${BUILD_A}" "${BUILD_B}"
(
  python scripts/build_r4_artifacts.py \
    --environment src/cemm_authoritative_hybrid/r4_environment.py \
    --source-revision "${SOURCE_SHA}" \
    --output "${BUILD_A}" \
    > "${EVIDENCE_DIR}/build-a.json"
) & pid_a=$!
(
  python scripts/build_r4_artifacts.py \
    --environment src/cemm_authoritative_hybrid/r4_environment.py \
    --source-revision "${SOURCE_SHA}" \
    --output "${BUILD_B}" \
    > "${EVIDENCE_DIR}/build-b.json"
) & pid_b=$!
wait "${pid_a}"
wait "${pid_b}"

python - "${BUILD_A}" "${BUILD_B}" "${SOURCE_SHA}" "${EVIDENCE_DIR}" <<'PY'
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
from cemm_authoritative_hybrid.r4_admission import verify_r4_admission
from cemm_authoritative_hybrid.r4_pipeline import R4BuildReceipt
from cemm_authoritative_hybrid.r4_partition_contracts import SPLITS

a = Path(sys.argv[1])
b = Path(sys.argv[2])
source = sys.argv[3]
evidence = Path(sys.argv[4])
expected_paths = {
    'BUILD_RECEIPT.json', 'authorizations/train.json', 'capabilities/train.json',
    'episodes.jsonl', 'expanded_cases.jsonl', 'expected_contracts.jsonl',
    'expected_derivations.jsonl', 'mutation_observations.jsonl', 'mutations.jsonl',
    'partition_evidence.json', 'partition_sufficiency.json', 'split_manifest.json',
    'splits/calibration.jsonl', 'splits/frozen_test.jsonl',
    'splits/selection.jsonl', 'splits/train.jsonl', 'structural_sufficiency.json',
}

def inspect(root: Path) -> dict[str, object]:
    receipt = R4BuildReceipt.from_dict(json.loads((root / 'BUILD_RECEIPT.json').read_text()))
    assert receipt.abi_version == 4
    assert receipt.source_revision == source
    report = verify_r4_admission(
        Path('.').resolve(),
        expected_source_revision=source,
        expected_authority_generation=receipt.authority_generation,
        candidate_root=root,
    )
    assert report['build_receipt_abi_version'] == 4
    assert report['artifact_count'] > len(expected_paths)
    paths = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    assert paths == expected_paths
    seen: set[str] = set()
    counts: dict[str, int] = {}
    for split in SPLITS:
        rows = [json.loads(line) for line in (root/'splits'/f'{split}.jsonl').read_text().splitlines() if line]
        refs = [row['episode_ref'] for row in rows]
        assert refs == sorted(refs)
        assert not seen.intersection(refs)
        seen.update(refs)
        counts[split] = len(rows)
    assert sum(counts.values()) == 400
    files = []
    for path in sorted(p for p in root.rglob('*') if p.is_file()):
        raw = path.read_bytes()
        files.append({'path': path.relative_to(root).as_posix(), 'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(raw)})
    return {'counts': counts, 'files': files, 'receipt_ref': receipt.receipt_ref, 'report': report, 'source': source}

manifest_a = inspect(a)
manifest_b = inspect(b)
assert manifest_a == manifest_b
(evidence/'candidate-manifest.json').write_text(json.dumps(manifest_a, sort_keys=True, separators=(',', ':'))+'\n')
PY

for slot in a b; do
  dir_var=BUILD_${slot^^}
  dir=${!dir_var}
  tar --sort=name --mtime='@0' --owner=0 --group=0 --numeric-owner --format=gnu \
    -cf "${EVIDENCE_DIR}/candidate-${slot}.tar" -C "${dir}" .
done
sha_a=$(sha256sum "${EVIDENCE_DIR}/candidate-a.tar" | cut -d' ' -f1)
sha_b=$(sha256sum "${EVIDENCE_DIR}/candidate-b.tar" | cut -d' ' -f1)
[[ "${sha_a}" == "${sha_b}" ]]
printf '%s\n' "${sha_a}" > "${EVIDENCE_DIR}/candidate-tar.sha256"

# Artifact-only commit.
cd "${REPO_DIR}"
[[ "$(git rev-parse HEAD)" == "${SOURCE_SHA}" ]]
rm -rf hybrid_mvp/artifacts/r4
mkdir -p hybrid_mvp/artifacts/r4
cp -a "${BUILD_A}/." hybrid_mvp/artifacts/r4/
git add -A -- hybrid_mvp/artifacts/r4
git diff --cached --check
changed=$(git diff --cached --name-only)
[[ -n "${changed}" ]]
[[ -z "$(printf '%s\n' "${changed}" | grep -v '^hybrid_mvp/artifacts/r4/' || true)" ]]
[[ ! -e hybrid_mvp/artifacts/r4/training_allowlist.json ]]
[[ ! -d hybrid_mvp/artifacts/r4/partitions ]]
GIT_AUTHOR_NAME='CEMM Verification Bot' \
GIT_AUTHOR_EMAIL='41898282+github-actions[bot]@users.noreply.github.com' \
GIT_AUTHOR_DATE='2026-08-22T13:30:00+01:00' \
GIT_COMMITTER_NAME='CEMM Verification Bot' \
GIT_COMMITTER_EMAIL='41898282+github-actions[bot]@users.noreply.github.com' \
GIT_COMMITTER_DATE='2026-08-22T13:30:00+01:00' \
  git commit --no-gpg-sign -m 'build(r4): publish current ABI-4 artifact graph'
ARTIFACT_SHA=$(git rev-parse HEAD)
ARTIFACT_TREE=$(git rev-parse 'HEAD^{tree}')
[[ "$(git rev-parse HEAD^)" == "${SOURCE_SHA}" ]]
[[ -z "$(git status --short --untracked-files=all)" ]]
push_candidate_if_at "${SOURCE_SHA}" "${ARTIFACT_SHA}"
printf '%s\n' "${ARTIFACT_SHA}" > "${EVIDENCE_DIR}/artifact-sha.txt"
printf '%s\n' "${ARTIFACT_TREE}" > "${EVIDENCE_DIR}/artifact-tree.txt"

# Every R4 owner, one phase tier, and static governance.
cd "${REPO_DIR}/hybrid_mvp"
for owner in artifact-integrity expected-contract governance mutation-partition structural-sufficiency surface-expansion; do
  python scripts/validate_mvp.py --phase R4 --tier owner --owner "${owner}" \
    > "${EVIDENCE_DIR}/owner-${owner}.json"
  assert_outcome "${EVIDENCE_DIR}/owner-${owner}.json" R4 owner "${owner}"
done
python scripts/validate_mvp.py --phase R4 --tier phase > "${EVIDENCE_DIR}/phase.json"
assert_outcome "${EVIDENCE_DIR}/phase.json" R4 phase
python scripts/verify_r3_r4_test_metadata.py > "${EVIDENCE_DIR}/metadata-post-artifact.txt"
for phase in G0 R1 R2 R3 R4 R5; do
  python scripts/check_test_inventory.py --phase "${phase}" --source-only \
    > "${EVIDENCE_DIR}/inventory-post-${phase}.json"
done
python scripts/check_r3_r4_structure.py > "${EVIDENCE_DIR}/structure-post-artifact.txt"
python scripts/audit_legacy_test_hard_cut.py > "${EVIDENCE_DIR}/legacy-post-artifact.json"
pre_status=$(python scripts/update_replay_status.py --verify-chain)
printf '%s\n' "${pre_status}" > "${EVIDENCE_DIR}/pre-admission-status.txt"
[[ "${pre_status}" == *'G0=green R1=green R2=green R3=green R4=red R5=red R6=red R7=red R8=red'* ]]
find . -type d -name __pycache__ -prune -exec rm -rf {} +
[[ -z "$(git -C "${REPO_DIR}" status --short --untracked-files=all)" ]]

# One fresh admission and one green transition.
python scripts/validate_mvp.py --phase R4 --tier admission > "${EVIDENCE_DIR}/admission.json"
assert_outcome "${EVIDENCE_DIR}/admission.json" R4 admission
readarray -t admission_fields < <(python - "${EVIDENCE_DIR}/admission.json" <<'PY'
import json
from pathlib import Path
import sys
v=json.loads(Path(sys.argv[1]).read_text())
assert v['run_ref'].startswith('run:')
assert v['gate_result_ref'].startswith('gate_result:')
assert v['receipt_path'].startswith('artifacts/validation/runs/')
print(v['run_ref']); print(v['gate_result_ref']); print(v['receipt_path'])
PY
)
RUN_REF=${admission_fields[0]}
GATE_REF=${admission_fields[1]}
RECEIPT_PATH=${admission_fields[2]}
python scripts/update_replay_status.py --phase R4 --status green --run-ref "${RUN_REF}" --dry-run \
  > "${EVIDENCE_DIR}/status-candidate.json"
RECORD_REF=$(python - "${EVIDENCE_DIR}/status-candidate.json" <<'PY'
import json
from pathlib import Path
import sys
v=json.loads(Path(sys.argv[1]).read_text())
assert v['phase']=='R4' and v['status']=='green'
print(v['record_ref'])
PY
)
python scripts/update_replay_status.py --phase R4 --status green --run-ref "${RUN_REF}" \
  --expect-record-ref "${RECORD_REF}" --append > "${EVIDENCE_DIR}/status-appended.json"
diff -u "${EVIDENCE_DIR}/status-candidate.json" "${EVIDENCE_DIR}/status-appended.json"
final_status=$(python scripts/update_replay_status.py --verify-chain)
printf '%s\n' "${final_status}" > "${EVIDENCE_DIR}/effective-status.txt"
[[ "${final_status}" == *'G0=green R1=green R2=green R3=green R4=green R5=red R6=red R7=red R8=red'* ]]

cd "${REPO_DIR}"
RECEIPT_RELATIVE="hybrid_mvp/${RECEIPT_PATH}"
[[ -f "${RECEIPT_RELATIVE}" ]]
printf '%s\n' "${RECEIPT_RELATIVE}" 'hybrid_mvp/governance/replay_status.jsonl' | sort > /tmp/task1-evidence-paths
git add -- "${RECEIPT_RELATIVE}" hybrid_mvp/governance/replay_status.jsonl
git diff --cached --name-only | sort > /tmp/task1-evidence-actual
diff -u /tmp/task1-evidence-paths /tmp/task1-evidence-actual
git diff --cached --check
[[ -z "$(git status --short --untracked-files=all | grep -vE '^(A |M ) (hybrid_mvp/artifacts/validation/runs/[0-9a-f]{24}\.json|hybrid_mvp/governance/replay_status\.jsonl)$' || true)" ]]
git commit --no-gpg-sign -m 'gov(r4): admit current ABI-4 artifact graph'
FINAL_SHA=$(git rev-parse HEAD)
[[ "$(git rev-parse HEAD^)" == "${ARTIFACT_SHA}" ]]
[[ -z "$(git status --short --untracked-files=all)" ]]
push_candidate_if_at "${ARTIFACT_SHA}" "${FINAL_SHA}"

remote_target=$(remote_sha "${TARGET_REF}")
if [[ "${remote_target}" == "${PARENT_SHA}" ]]; then
  git push origin "${FINAL_SHA}:${TARGET_REF}"
else
  [[ "${remote_target}" == "${FINAL_SHA}" ]]
fi
[[ "$(remote_sha "${TARGET_REF}")" == "${FINAL_SHA}" ]]

python - "${SOURCE_SHA}" "${ARTIFACT_SHA}" "${ARTIFACT_TREE}" "${FINAL_SHA}" "${sha_a}" "${RUN_REF}" "${GATE_REF}" "${RECEIPT_PATH}" "${final_status}" <<'PY'
import json
from pathlib import Path
import sys
(source, artifact, tree, final, tar_sha, run_ref, gate_ref, receipt_path, status) = sys.argv[1:]
Path('/tmp/r5-r6-task1-evidence/publication.json').write_text(json.dumps({
  'schema':'cemm-r5-r6-task1-r4-current-admission-v2',
  'parent_sha':'ca4816bc892d14e7eb593f00977309e2031f131b',
  'source_repair_sha':source,
  'artifact_sha':artifact,
  'artifact_tree':tree,
  'final_sha':final,
  'candidate_tar_sha256':tar_sha,
  'run_ref':run_ref,
  'gate_result_ref':gate_ref,
  'receipt_path':receipt_path,
  'effective_status':status,
  'artifact_file_count':17,
  'episode_count':400,
  'build_receipt_abi_version':4,
  'r5_source_implementation_unblocked':True,
}, sort_keys=True, indent=2)+'\n')
PY

echo "Task 1 complete: ${FINAL_SHA}"
