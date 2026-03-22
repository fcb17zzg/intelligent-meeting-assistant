---
name: long-audio-test-generation
description: "Use this skill when you need a long-duration meeting test audio plan, validation checklist, and generation workflow without immediately producing audio files. Trigger phrases: long test audio, stress test audio, synthetic meeting audio, benchmark audio, ASR duration test, diarization test input."
---

# Long Audio Test Generation Skill

## Purpose

Use this skill to design and review a reliable long-duration test audio strategy for a meeting assistant system before creating actual audio files.

This skill is for planning and specification only by default. Do not generate audio unless the user explicitly asks to run the generation step.

## Use When

- You need test audio longer than typical sample clips (for example 30 to 180 minutes).
- You need controlled scenarios for ASR, summarization, topic extraction, and action-item extraction.
- You want repeatable and versioned test inputs for regression testing.
- You need to evaluate edge cases: overlap speech, silence, noise, accents, and speaker turns.

## Inputs To Collect

Ask for or infer these parameters before proposing a final plan:

1. Target duration in minutes.
2. Number of speakers and speaking style.
3. Language and domain vocabulary (general meeting, product review, research seminar).
4. Audio profile (sample rate, channels, bitrate, output format).
5. Noise conditions (clean, office ambience, keyboard, crosstalk).
6. Annotation requirements (timestamps, speaker labels, action-item ground truth).
7. Acceptance criteria (WER target, extraction accuracy, summary quality rubric).

## Output Contract

Return a structured specification with these sections:

1. Scenario Matrix
2. Audio Composition Plan
3. Ground Truth Schema
4. Validation Metrics
5. Execution Steps
6. Risk and Mitigation

## Recommended Scenario Matrix

Design at least one baseline and three stress scenarios:

1. Baseline clean meeting
2. High speaker-overlap meeting
3. Noisy remote meeting
4. Long silence plus rapid topic switch meeting

For each scenario, define:

- Duration
- Speaker count
- Turn density
- Overlap ratio
- Noise level
- Expected challenge

## Audio Composition Guidance

- Keep segment lengths varied (short turns and long turns) to avoid unrealistic rhythm.
- Introduce periodic silence windows to test segmentation robustness.
- Include explicit decision points and action items in transcript content.
- Use consistent loudness targets across scenarios for fair comparison.
- Keep deterministic seeds for synthetic generation to ensure reproducibility.

## Ground Truth Schema

Provide machine-readable annotations (for example JSON) with:

- meeting_id
- scenario_id
- segments[]
- segments.start_ms
- segments.end_ms
- segments.speaker
- segments.text
- segments.topic
- action_items[]
- action_items.owner
- action_items.task
- action_items.deadline
- decisions[]
- unresolved_questions[]

## Validation Metrics

Define pass/fail thresholds before generation:

- ASR quality: WER and CER thresholds.
- Diarization quality: speaker-attributed segment accuracy.
- NLP quality: summary coverage, topic precision, action-item precision and recall.
- System quality: end-to-end processing time and stability over long inputs.

## Workflow

1. Confirm requirements and constraints.
2. Draft scenario matrix and annotation schema.
3. Produce generation blueprint (without generating audio).
4. If repository context is unclear, call an Explore subagent to locate reusable scripts under `scripts/`, tests under `tests/audio_processing/`, and output directories under `test_audio/generated/`.
5. Ask user for approval.
6. Only after approval, generate audio and annotations.
7. Run pipeline tests and collect metrics.
8. Produce a comparison report across scenarios.

## Script Invocation (Repository-Aware)

Use script-first execution to keep the workflow reproducible.

### Default Mode

- Default to `plan-only` mode: output a JSON plan and command templates.
- Do not generate audio files unless the user explicitly requests generation.

### Existing Repository Entry Points

- End-to-end sample check: `python scripts/run_real_audio_e2e_check.py`
- Long-audio processing tests: `pytest tests/audio_processing/test_long_audio.py -s`

### Plan Script (Recommended)

Use the planning script to create deterministic scenario specs and command templates:

- `python scripts/generate_long_audio_test_plan.py --duration-min 120 --speakers 4 --scenario-set stress --plan-only --output test_audio/generated/plans`

Expected outputs:

- Plan JSON file in `test_audio/generated/plans/`
- Scenario matrix and acceptance thresholds
- Suggested generation commands (not executed)

### Optional Generation Step (Only With User Approval)

After approval, run one of the generated commands to produce audio files and annotations, then execute pipeline tests.

### Naming and Path Convention

- Plan file: `long_audio_plan_<timestamp>.json`
- Suggested audio file naming: `<duration_sec>s_<speaker_count>spk_<scenario>.wav`
- Generated assets root: `test_audio/generated/`

## Safety and Practical Constraints

- Never claim real-world recording authenticity for synthetic content.
- Do not use copyrighted voice assets without permission.
- Keep personally identifiable information out of synthetic transcripts.
- Store generated files in a dedicated test directory with version tags.

## Response Template

Use this response format:

1. Goal and constraints
2. Proposed scenario matrix
3. Audio and annotation spec
4. Validation criteria
5. Step-by-step execution plan
6. Approval request before generation

## Non-Goals

- This skill does not run model training.
- This skill does not modify production business logic.
- This skill does not generate audio automatically unless explicitly requested.
- This skill does not auto-run generated shell commands without user confirmation.
