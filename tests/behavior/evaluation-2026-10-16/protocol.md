# Four-case planning comparison

Date: 2026-10-16 (UTC).

## What was tested

Two separate response sessions answered the same four fictional task requests. One could read this skill and its relevant references; the other used its ordinary instructions without reading this project. Both produced plans only. Neither was allowed to contact services, start jobs, upload, purchase, or delete anything.

The input was reduced to the request and observations from the existing behavior fixtures. The evaluators' `must`, `must_not`, and `evidence` criteria were withheld from both response sessions. The skill and rubric were not changed after seeing their responses.

The same parent model was inherited without a model override, with `xhigh` reasoning requested in both sessions. The exact model build, temperature, seed, and serving details were unavailable. Each session handled all four cases together; these are not four independent repetitions per condition. Existing platform instructions remained in force for both conditions, so this compares adding the skill to an already-instructed assistant, not to an instruction-free model.

An independent assessment session received responses labeled A and B, the requests, and the existing rubric. The condition mapping was withheld until scoring. This is label blinding, not proof that writing differences could not reveal the condition. A is the with-skill response; B is the without-skill response. Scores retain these labels for traceability.

## Scoring

For each criterion, assess only explicit response content. A planned action is not evidence that it happened. Separate behavioral `must` / `must_not` judgments from execution-evidence criteria. Do not reward length or assume the skill must win. Preserve partial or not-demonstrated results rather than filling gaps from expected behavior.

The assessment contains short quotations so readers can check judgments against the complete responses. No scalar improvement score, statistical significance, compute saving, or production reliability claim is justified by these four examples.

## Reproduce the comparison

1. Freeze the skill and rubric revisions before generating responses.
2. Give two fresh sessions `requests.json` and the same plan-only task instruction in `prompts.md`.
3. Provide the skill files only to the with-skill session; do not reveal the scoring rubric to either.
4. Save their full final responses. Record actual model/settings when available; mark unavailable values as unknown.
5. Give an independent assessor anonymously labeled responses and the frozen rubric. Keep the condition mapping separate until scoring is saved.
6. Report disagreements and omissions, including cases where the ordinary assistant performs equally well or better. Use repeated, broader tests before drawing general conclusions.

## Scope limits

This checks written decisions under supplied observations. It does not test browser recovery, real quotas, account eligibility, job dispatch, remote storage, or deletion controls. The repository's CPU demo independently exercises local checkpoint and file recovery; the manifest unit tests independently exercise implemented JSON rules. Neither establishes live cloud integration reliability.
