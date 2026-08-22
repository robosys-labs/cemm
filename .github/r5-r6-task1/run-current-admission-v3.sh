#!/usr/bin/env bash
set -euo pipefail

REPO_DIR=${1:?candidate repository path required}
CONTROL_DIR=${2:?control repository path required}
PARENT_SHA=ca4816bc892d14e7eb593f00977309e2031f131b
TRIGGER_SHA=d4be105c99fc7975650a432a1bf8689caa06286f
REPAIR_SHA=8fc96895513dd4305f0737a98319782a1f5aa0f7
REPAIR_TREE=bb073e594f9aa09d50a59882def2fd7bf551297e
SOURCE_SHA=879e421cc731522677fe2db0006d18d6a634e9cb
SOURCE_TREE=65dd0d1b9afb7a0f09599c9e976cbd8f17741da7
CANDIDATE_BRANCH=agent/r5-r6-task1-r4-current-admission-v3-candidate-20260822
OLD_RUNNER=${CONTROL_DIR}/.github/r5-r6-task1/run-current-admission.sh
OLD_PATCH=${CONTROL_DIR}/.github/r5-r6-task1/source-owner-repair.patch.gz.b64
EXTENSION_PATCH=${CONTROL_DIR}/.github/r5-r6-task1/phase-stability.patch.gz.b64
GENERATED_RUNNER=/tmp/r5-r6-task1-current-admission-v3.generated.sh

[[ "$(git -C "${REPO_DIR}" rev-parse HEAD)" == "${TRIGGER_SHA}" ]]
[[ "$(git -C "${REPO_DIR}" rev-parse HEAD^)" == "${PARENT_SHA}" ]]
printf '%s\n' '.github/r5-r6-task1/current-admission-v3-trigger.json' > /tmp/task1-v3-trigger.expected
git -C "${REPO_DIR}" diff --name-only "${PARENT_SHA}" "${TRIGGER_SHA}" | sort > /tmp/task1-v3-trigger.actual
diff -u /tmp/task1-v3-trigger.expected /tmp/task1-v3-trigger.actual
[[ "$(git -C "${REPO_DIR}" hash-object .github/r5-r6-task1/current-admission-v3-trigger.json)" == 'b61537ddc809b1cbc724a45de4fd49d431726d03' ]]

[[ "$(git -C "${CONTROL_DIR}" merge-base "${PARENT_SHA}" HEAD)" == "${PARENT_SHA}" ]]
printf '%s\n' \
  '.github/r5-r6-task1/phase-stability.patch.gz.b64' \
  '.github/r5-r6-task1/run-current-admission-v3.sh' \
  '.github/r5-r6-task1/run-current-admission.sh' \
  '.github/r5-r6-task1/source-owner-repair.patch.gz.b64' \
  '.github/workflows/r5-r6-task1-current-admission-v3.yml' \
  '.github/workflows/r5-r6-task1-current-admission.yml' | sort > /tmp/task1-v3-control.expected
git -C "${CONTROL_DIR}" diff --name-only "${PARENT_SHA}" HEAD | sort > /tmp/task1-v3-control.actual
diff -u /tmp/task1-v3-control.expected /tmp/task1-v3-control.actual
[[ "$(git -C "${CONTROL_DIR}" hash-object .github/r5-r6-task1/run-current-admission.sh)" == '7a468b8e0a5c95008cdaac74966c95e25f530c92' ]]
[[ "$(sha256sum "${OLD_PATCH}" | cut -d' ' -f1)" == 'abc439ec63ed804e31829b0858d2927594c4601672f7bfcbcf935d6510bc4670' ]]
[[ "$(sha256sum "${EXTENSION_PATCH}" | cut -d' ' -f1)" == '67ca65e542816550222a319e70496c737b540683059e2bee3dc76607ffec02dc' ]]

python3 - "${OLD_RUNNER}" "${GENERATED_RUNNER}" <<'PY'
from __future__ import annotations

from pathlib import Path
import sys

template_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
text = template_path.read_text(encoding='utf-8')


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise AssertionError(f'{label}: expected one occurrence, found {count}')
    text = text.replace(old, new, 1)


replace_once(
    'TRIGGER_SHA=5d3523f54223285e26b4d315cd5dbe176aabc1f3',
    'TRIGGER_SHA=d4be105c99fc7975650a432a1bf8689caa06286f',
    'trigger sha',
)
replace_once(
    'SOURCE_SHA=8fc96895513dd4305f0737a98319782a1f5aa0f7\n'
    'SOURCE_TREE=bb073e594f9aa09d50a59882def2fd7bf551297e',
    'REPAIR_SHA=8fc96895513dd4305f0737a98319782a1f5aa0f7\n'
    'REPAIR_TREE=bb073e594f9aa09d50a59882def2fd7bf551297e\n'
    'SOURCE_SHA=879e421cc731522677fe2db0006d18d6a634e9cb\n'
    'SOURCE_TREE=65dd0d1b9afb7a0f09599c9e976cbd8f17741da7',
    'source constants',
)
replace_once(
    'CANDIDATE_BRANCH=agent/r5-r6-task1-r4-current-admission-candidate-20260822',
    'CANDIDATE_BRANCH=agent/r5-r6-task1-r4-current-admission-v3-candidate-20260822',
    'candidate branch',
)
replace_once(
    'PATCH_B64=${CONTROL_DIR}/.github/r5-r6-task1/source-owner-repair.patch.gz.b64\n'
    'EVIDENCE_DIR=',
    'PATCH_B64=${CONTROL_DIR}/.github/r5-r6-task1/source-owner-repair.patch.gz.b64\n'
    'EXTENSION_B64=${CONTROL_DIR}/.github/r5-r6-task1/phase-stability.patch.gz.b64\n'
    'EVIDENCE_DIR=',
    'extension variable',
)
replace_once(
    '.github/r5-r6-task1/current-admission-trigger.json',
    '.github/r5-r6-task1/current-admission-v3-trigger.json',
    'trigger path',
)
replace_once(
    '03b5a3aa800e1dcb1444ae4f876e60220c3ca795',
    'b61537ddc809b1cbc724a45de4fd49d431726d03',
    'trigger blob',
)

control_start = text.index('[[ "$(git -C "${CONTROL_DIR}" merge-base')
control_end = text.index('\n\n# Reconstruct and authenticate', control_start)
text = text[:control_start] + '# Control surface was authenticated by the v3 wrapper.' + text[control_end:]

old_post_commit = '''[[ "$(git -C "${REPO_DIR}" rev-parse HEAD)" == "${SOURCE_SHA}" ]]
[[ "$(git -C "${REPO_DIR}" rev-parse 'HEAD^{tree}')" == "${SOURCE_TREE}" ]]
[[ -z "$(git -C "${REPO_DIR}" status --short --untracked-files=all)" ]]
push_candidate_if_at "${TRIGGER_SHA}" "${SOURCE_SHA}"

cd "${REPO_DIR}/hybrid_mvp"
'''
new_post_commit = '''[[ "$(git -C "${REPO_DIR}" rev-parse HEAD)" == "${REPAIR_SHA}" ]]
[[ "$(git -C "${REPO_DIR}" rev-parse 'HEAD^{tree}')" == "${REPAIR_TREE}" ]]
[[ -z "$(git -C "${REPO_DIR}" status --short --untracked-files=all)" ]]
push_candidate_if_at "${TRIGGER_SHA}" "${REPAIR_SHA}"

base64 --decode "${EXTENSION_B64}" > /tmp/r5-task1-phase-stability.patch.gz
[[ "$(sha256sum /tmp/r5-task1-phase-stability.patch.gz | cut -d' ' -f1)" == 'b53d38d454408ce2a83024e80324f573e4c5ca1cc01e01b85e993fd1d0d81fd1' ]]
gzip -dc /tmp/r5-task1-phase-stability.patch.gz > /tmp/r5-task1-phase-stability.patch
[[ "$(sha256sum /tmp/r5-task1-phase-stability.patch | cut -d' ' -f1)" == 'ad54998477b35790f67b4d34870d053a20a94ee3c971933f229a5a8f0d92c0ea' ]]
git -C "${REPO_DIR}" apply --check /tmp/r5-task1-phase-stability.patch
git -C "${REPO_DIR}" apply /tmp/r5-task1-phase-stability.patch
printf '%s\n' \
  'hybrid_mvp/scripts/publish_r4_feasibility_basis.py' \
  'hybrid_mvp/tests/test_r4_authentic_episodes.py' | sort > /tmp/task1-phase-stability.expected
git -C "${REPO_DIR}" diff --name-only | sort > /tmp/task1-phase-stability.actual
diff -u /tmp/task1-phase-stability.expected /tmp/task1-phase-stability.actual
git -C "${REPO_DIR}" diff --check
git -C "${REPO_DIR}" add -- \
  hybrid_mvp/scripts/publish_r4_feasibility_basis.py \
  hybrid_mvp/tests/test_r4_authentic_episodes.py
GIT_AUTHOR_NAME='CEMM Verification Bot' \
GIT_AUTHOR_EMAIL='41898282+github-actions[bot]@users.noreply.github.com' \
GIT_AUTHOR_DATE='2026-08-22T14:00:00+01:00' \
GIT_COMMITTER_NAME='CEMM Verification Bot' \
GIT_COMMITTER_EMAIL='41898282+github-actions[bot]@users.noreply.github.com' \
GIT_COMMITTER_DATE='2026-08-22T14:00:00+01:00' \
  git -C "${REPO_DIR}" commit --no-gpg-sign -m 'fix(r4): stabilize structured phase execution'
[[ "$(git -C "${REPO_DIR}" rev-parse HEAD)" == "${SOURCE_SHA}" ]]
[[ "$(git -C "${REPO_DIR}" rev-parse 'HEAD^{tree}')" == "${SOURCE_TREE}" ]]
[[ -z "$(git -C "${REPO_DIR}" status --short --untracked-files=all)" ]]
push_candidate_if_at "${REPAIR_SHA}" "${SOURCE_SHA}"

cd "${REPO_DIR}/hybrid_mvp"
'''
replace_once(old_post_commit, new_post_commit, 'source extension insertion')
replace_once(
    'export PYTHONPATH=src/cemm_authoritative_hybrid:src:scripts:.\n',
    'export PYTHONPATH="${REPO_DIR}/hybrid_mvp/src/cemm_authoritative_hybrid:'
    '${REPO_DIR}/hybrid_mvp/src:${REPO_DIR}/hybrid_mvp/scripts:'
    '${REPO_DIR}/hybrid_mvp"\n',
    'absolute Python path',
)
if text.count('2026-08-22T13:30:00+01:00') != 2:
    raise AssertionError('artifact date: expected two occurrences')
text = text.replace('2026-08-22T13:30:00+01:00', '2026-08-22T14:30:00+01:00')
replace_once(
    "'schema':'cemm-r5-r6-task1-r4-current-admission-v2',",
    "'schema':'cemm-r5-r6-task1-r4-current-admission-v3',",
    'publication schema',
)
replace_once(
    "'source_repair_sha':source,",
    "'source_repair_sha':'8fc96895513dd4305f0737a98319782a1f5aa0f7',\n  'source_sha':source,",
    'publication source fields',
)

for forbidden in (
    '5d3523f54223285e26b4d315cd5dbe176aabc1f3',
    'agent/r5-r6-task1-r4-current-admission-candidate-20260822',
    '.github/r5-r6-task1/current-admission-trigger.json',
):
    if forbidden in text:
        raise AssertionError(f'old control identity remains: {forbidden}')
for required in (
    '879e421cc731522677fe2db0006d18d6a634e9cb',
    'phase-stability.patch.gz.b64',
    'fix(r4): stabilize structured phase execution',
    'cemm-r5-r6-task1-r4-current-admission-v3',
):
    if required not in text:
        raise AssertionError(f'missing transformed identity: {required}')

out_path.write_text(text, encoding='utf-8')
PY

chmod +x "${GENERATED_RUNNER}"
bash -n "${GENERATED_RUNNER}"
bash "${GENERATED_RUNNER}" "${REPO_DIR}" "${CONTROL_DIR}"
