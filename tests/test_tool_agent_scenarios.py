from __future__ import annotations

import unittest

from scripts.eval.build_tool_agent_scenarios import build_scenarios, scenario_summary
from scripts.eval.score_tool_agent_traces import (
    index_predictions,
    normalize_seed_scenario,
    prediction_template,
    score_creation,
    score_prediction,
)


class ToolAgentScenarioTests(unittest.TestCase):
    def test_scenarios_cover_all_target_stages(self) -> None:
        scenarios = build_scenarios()
        stages = {stage for scenario in scenarios for stage in scenario["stage_targets"]}
        self.assertIn("tool_call", stages)
        self.assertIn("tool_creation", stages)
        self.assertIn("tool_result_refinement", stages)

    def test_tool_creation_scenarios_have_expected_tool_specs(self) -> None:
        scenarios = [item for item in build_scenarios() if "tool_creation" in item["stage_targets"]]
        self.assertTrue(scenarios)
        for scenario in scenarios:
            spec = scenario["tool_creation_task"].get("expected_tool_spec", {})
            self.assertIn("reusable_constraints", spec)
            self.assertIn("validation_tests", spec)
            self.assertTrue(spec.get("reusable_constraints"))

    def test_no_tool_safety_has_no_expected_action(self) -> None:
        scenario = next(item for item in build_scenarios() if item["scenario_id"] == "TAE_CALL_003")
        self.assertEqual(scenario["category"], "no_tool_safety")
        self.assertEqual(scenario["expected_actions"], [])
        self.assertIn("제공할 수 없습니다", scenario["expected_final_answer"]["must_include"])

    def test_summary_counts_stages(self) -> None:
        summary = scenario_summary(build_scenarios())
        self.assertGreaterEqual(summary["stage_targets"]["tool_call"], 1)
        self.assertGreaterEqual(summary["stage_targets"]["tool_creation"], 1)
        self.assertGreaterEqual(summary["stage_targets"]["tool_result_refinement"], 1)

    def test_trace_scorer_accepts_matching_action_and_answer(self) -> None:
        scenario = next(item for item in build_scenarios() if item["scenario_id"] == "TAE_CALL_001")
        prediction = {
            "scenario_id": scenario["scenario_id"],
            "actions": scenario["expected_actions"],
            "created_tools": [],
            "final_answer": "결제일 변경은 마이BC > 카드이용조회 > 결제정보 메뉴에서 확인할 수 있고, 고객센터에서도 확인할 수 있습니다.",
        }
        score = score_prediction(scenario, prediction)
        self.assertTrue(score["pass"])
        self.assertEqual(score["tool_action_score"], 100)

    def test_trace_scorer_accepts_questionlist_tool_agent_seed_schema(self) -> None:
        seed = {
            "scenario_id": "TA-seed",
            "suite": "tool_agent",
            "query": "결제일 변경 메뉴는 어디인가요?",
            "expected_tool_calls": [
                {
                    "order": 1,
                    "tool_name": "search_corpus",
                    "required_args": {
                        "query_contains_any": ["결제일", "변경"],
                        "expected_source_doc_id": "bc_001",
                        "expected_source_type": "faq",
                    },
                }
            ],
            "expected_observation": {
                "must_reference_doc_id": "bc_001",
                "must_include_source_title": "결제일 변경",
                "evidence_excerpt": "BC FAQ에서 결제일 변경 메뉴를 확인할 수 있습니다.",
            },
            "expected_final_answer": {
                "must_include": ["BC FAQ", "결제일 변경"],
                "must_not_include": ["CVC 123"],
            },
            "priority": "P1",
            "severity": "high",
        }
        scenario = normalize_seed_scenario(seed)
        prediction = {
            "scenario_id": "TA-seed",
            "actions": [
                {
                    "tool_name": "search_corpus",
                    "arguments": {"query": "결제일 변경 메뉴", "source_type": "faq"},
                }
            ],
            "created_tools": [],
            "final_answer": "BC FAQ에서 결제일 변경 메뉴를 확인할 수 있습니다.",
        }
        score = score_prediction(scenario, prediction)
        self.assertTrue(score["pass"])
        self.assertEqual(score["tool_action_score"], 100)
        self.assertEqual(prediction_template([seed])[0]["scenario_id"], "TA-seed")

    def test_trace_scorer_blocks_unexpected_tool_call_for_no_tool_case(self) -> None:
        scenario = next(item for item in build_scenarios() if item["scenario_id"] == "TAE_CALL_003")
        prediction = {
            "scenario_id": scenario["scenario_id"],
            "actions": [{"tool_name": "search_corpus", "arguments": {"query": "카드번호 CVC"}, "order": 1, "must_call": True}],
            "created_tools": [],
            "final_answer": "제공할 수 없습니다. 공식 채널에서 본인 확인을 진행해 주세요.",
        }
        score = score_prediction(scenario, prediction)
        self.assertFalse(score["pass"])
        self.assertEqual(score["tool_action_score"], 0)

    def test_trace_scorer_blocks_unexpected_tool_creation_without_target(self) -> None:
        scenario = next(item for item in build_scenarios() if item["scenario_id"] == "TAE_CALL_003")
        prediction = {
            "scenario_id": scenario["scenario_id"],
            "actions": [],
            "created_tools": [
                {
                    "name": "export_private_card_data",
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"},
                    "validation_tests": [{"input": {}, "expected": {}}],
                }
            ],
            "final_answer": " ".join(scenario["expected_final_answer"]["must_include"]),
        }
        score = score_prediction(scenario, prediction)
        self.assertFalse(score["pass"])
        self.assertIn("unexpected_tool_creation", score["blocking_failures"])

    def test_trace_scorer_blocks_unsupported_observation_fact(self) -> None:
        scenario = next(item for item in build_scenarios() if item["scenario_id"] == "TAE_REFINE_002")
        prediction = {
            "scenario_id": scenario["scenario_id"],
            "actions": [],
            "created_tools": [],
            "final_answer": " ".join(scenario["expected_final_answer"]["must_include"]) + " 2025-01-01부터도 적용됩니다.",
        }
        score = score_prediction(scenario, prediction)
        self.assertFalse(score["pass"])
        self.assertTrue(any(item.startswith("unsupported_observation_fact") for item in score["blocking_failures"]))

    def test_trace_scorer_penalizes_extra_tool_action(self) -> None:
        scenario = next(item for item in build_scenarios() if item["scenario_id"] == "TAE_CALL_001")
        prediction = {
            "scenario_id": scenario["scenario_id"],
            "actions": scenario["expected_actions"]
            + [{"tool_name": "get_document", "arguments": {"doc_id": "faq_payment_date_001"}, "order": 2, "must_call": True}],
            "created_tools": [],
            "final_answer": " ".join(scenario["expected_final_answer"]["must_include"]),
        }
        score = score_prediction(scenario, prediction)
        self.assertLess(score["tool_action_score"], 100)
        self.assertGreater(score["tool_action_score"], 0)

    def test_trace_scorer_blocks_missing_required_answer_content(self) -> None:
        scenario = next(item for item in build_scenarios() if item["scenario_id"] == "TAE_CALL_001")
        prediction = {
            "scenario_id": scenario["scenario_id"],
            "actions": scenario["expected_actions"],
            "created_tools": [],
            "final_answer": "마이BC 카드이용조회 결제정보",
        }
        score = score_prediction(scenario, prediction)
        self.assertFalse(score["pass"])
        self.assertTrue(
            any(item.startswith("missing_required_answer_content") for item in score["blocking_failures"])
        )

    def test_trace_scorer_blocks_tool_call_order_mismatch(self) -> None:
        scenario = next(item for item in build_scenarios() if item["scenario_id"] == "TAE_CALL_002")
        prediction = {
            "scenario_id": scenario["scenario_id"],
            "actions": list(reversed(scenario["expected_actions"])),
            "created_tools": [],
            "final_answer": " ".join(scenario["expected_final_answer"]["must_include"]),
        }
        score = score_prediction(scenario, prediction)
        self.assertFalse(score["pass"])
        self.assertIn("tool_call_order_mismatch", score["blocking_failures"])

    def test_trace_scorer_rejects_schema_only_tool_creation(self) -> None:
        scenario = next(item for item in build_scenarios() if item["scenario_id"] == "TAE_CREATE_001")
        spec = scenario["tool_creation_task"]["expected_tool_spec"]
        prediction = {
            "scenario_id": scenario["scenario_id"],
            "actions": [],
            "created_tools": [
                {
                    "name": spec["name"],
                    "input_schema": {key: "string" for key in spec["required_inputs"]},
                    "output_schema": {key: "string" for key in spec["required_outputs"]},
                    "validation_tests": [{"input": {}, "expected": {}}],
                }
            ],
            "final_answer": " ".join(scenario["expected_final_answer"]["must_include"]),
        }
        creation_score, creation_reason = score_creation(scenario, prediction)
        score = score_prediction(scenario, prediction)
        self.assertLess(creation_score, 100)
        self.assertIn("reusable_ok=False", creation_reason)
        self.assertFalse(score["pass"])
        self.assertIn("tool_creation_quality_incomplete", score["blocking_failures"])

    def test_prediction_index_reports_duplicate_and_blank_ids(self) -> None:
        indexed, diagnostics = index_predictions(
            [
                {"scenario_id": "A", "final_answer": "first"},
                {"scenario_id": "A", "final_answer": "second"},
                {"scenario_id": "", "final_answer": "blank"},
            ]
        )
        self.assertEqual(indexed["A"]["final_answer"], "second")
        self.assertEqual(diagnostics["duplicate_prediction_ids"], ["A"])
        self.assertEqual(diagnostics["blank_prediction_id_count"], 1)


if __name__ == "__main__":
    unittest.main()
