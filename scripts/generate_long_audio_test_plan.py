import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Scenario:
    scenario_id: str
    duration_min: int
    speakers: int
    overlap_ratio: float
    noise_level: str
    turn_density: str
    expected_challenge: str


def build_scenarios(duration_min: int, speakers: int, scenario_set: str) -> list[Scenario]:
    if scenario_set == "baseline":
        return [
            Scenario(
                scenario_id="baseline_clean",
                duration_min=duration_min,
                speakers=speakers,
                overlap_ratio=0.05,
                noise_level="clean",
                turn_density="medium",
                expected_challenge="Long context retention with clean audio",
            )
        ]

    # Default stress set contains one baseline + three stress cases.
    return [
        Scenario(
            scenario_id="baseline_clean",
            duration_min=duration_min,
            speakers=speakers,
            overlap_ratio=0.05,
            noise_level="clean",
            turn_density="medium",
            expected_challenge="Reference quality and stable segmentation",
        ),
        Scenario(
            scenario_id="overlap_heavy",
            duration_min=duration_min,
            speakers=max(3, speakers),
            overlap_ratio=0.35,
            noise_level="low",
            turn_density="high",
            expected_challenge="Speaker overlap and diarization confusion",
        ),
        Scenario(
            scenario_id="noisy_remote",
            duration_min=duration_min,
            speakers=speakers,
            overlap_ratio=0.15,
            noise_level="office",
            turn_density="medium",
            expected_challenge="Noise robustness and ASR stability",
        ),
        Scenario(
            scenario_id="silence_topic_switch",
            duration_min=duration_min,
            speakers=speakers,
            overlap_ratio=0.1,
            noise_level="clean",
            turn_density="bursty",
            expected_challenge="Long silence handling and rapid topic transitions",
        ),
    ]


def build_acceptance_thresholds() -> dict:
    return {
        "asr": {
            "wer_max": 0.22,
            "cer_max": 0.15,
        },
        "diarization": {
            "speaker_segment_accuracy_min": 0.82,
        },
        "nlp": {
            "summary_coverage_min": 0.8,
            "topic_precision_min": 0.75,
            "action_item_precision_min": 0.75,
            "action_item_recall_min": 0.7,
        },
        "system": {
            "e2e_timeout_sec": 3600,
            "pipeline_crash_count_max": 0,
        },
    }


def build_command_templates(duration_min: int, speakers: int) -> list[str]:
    duration_sec = duration_min * 60
    return [
        (
            "python scripts/audio_gen.py "
            f"--duration-sec {duration_sec} --speakers {speakers} "
            "--scenario baseline_clean --output test_audio/generated --seed 42"
        ),
        (
            "python scripts/audio_gen.py "
            f"--duration-sec {duration_sec} --speakers {max(3, speakers)} "
            "--scenario overlap_heavy --noise office --overlap-ratio 0.35 "
            "--output test_audio/generated --seed 42"
        ),
        "python scripts/run_real_audio_e2e_check.py",
        "pytest tests/audio_processing/test_long_audio.py -s",
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a long-audio test plan and command templates (plan-only by default)."
    )
    parser.add_argument("--duration-min", type=int, default=120, help="Target duration in minutes")
    parser.add_argument("--speakers", type=int, default=4, help="Target speaker count")
    parser.add_argument(
        "--scenario-set",
        choices=["baseline", "stress"],
        default="stress",
        help="Scenario set to include in the plan",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        default=True,
        help="Keep plan-only mode. Script will not generate audio.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="test_audio/generated/plans",
        help="Output directory for generated plan JSON",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    scenarios = build_scenarios(args.duration_min, args.speakers, args.scenario_set)
    acceptance = build_acceptance_thresholds()
    commands = build_command_templates(args.duration_min, args.speakers)

    payload = {
        "generated_at": datetime.now().isoformat(),
        "plan_only": bool(args.plan_only),
        "parameters": {
            "duration_min": args.duration_min,
            "speakers": args.speakers,
            "scenario_set": args.scenario_set,
        },
        "scenario_matrix": [asdict(s) for s in scenarios],
        "acceptance_thresholds": acceptance,
        "command_templates": commands,
        "notes": [
            "Commands are templates and are not executed by this script.",
            "Request explicit user approval before running generation commands.",
        ],
    }

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"long_audio_plan_{timestamp}.json"
    output_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"plan_path": str(output_file), "scenario_count": len(scenarios)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
