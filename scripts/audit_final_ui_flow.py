from __future__ import annotations

import argparse
import base64
import json
import re
from urllib.parse import urlparse
from pathlib import Path
from typing import Any

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


def load_basic_auth() -> dict[str, str] | None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not re.match(r"^\s*FINAL_UI_AUTH_USERS\s*=", line):
            continue
        raw = re.sub(r"^\s*FINAL_UI_AUTH_USERS\s*=\s*", "", line).strip().strip("\"'")
        first = raw.split(",", 1)[0].strip()
        parts = [part.strip() for part in first.split(":")]
        if len(parts) >= 2 and parts[0] and parts[1]:
            return {"username": parts[0], "password": parts[1]}
    return None


def assert_true(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def safe_text(page, selector: str) -> str:
    try:
        return page.locator(selector).inner_text(timeout=3000).strip()
    except PlaywrightTimeoutError:
        return ""


def visible_panel_id(page) -> str:
    return page.evaluate(
        "() => [...document.querySelectorAll('.panel.active')].map((el) => el.id).join(',')"
    )


def click_tab(page, tab_id: str, failures: list[str]) -> None:
    page.locator(f'#tab-{tab_id}').click()
    page.wait_for_timeout(250)
    assert_true(visible_panel_id(page) == tab_id, f"{tab_id} tab did not become active", failures)


def collect_state(page) -> dict[str, Any]:
    return page.evaluate(
        """() => ({
            runCount: runs.length,
            caseCount: cases.length,
            gateCount: runReleaseGates.length,
            modelCount: [...new Set(cases.map((row) => row.version))].length,
            caseModels: [...new Set(cases.map((row) => row.version))].sort(),
            selectedRunId,
            latestRunId: latestRun && latestRun.run_id,
            activeTab: document.body.dataset.activeTab,
        })"""
    )


def search_model_counts(page) -> list[dict[str, Any]]:
    return page.evaluate(
        """() => {
          const counts = new Map();
          for (const row of cases) counts.set(row.version, (counts.get(row.version) || 0) + 1);
          return [...document.querySelectorAll('#globalSearchModel option')]
            .filter((option) => option.value)
            .map((option) => ({
              value: option.value,
              label: option.textContent.trim(),
              expectedRows: counts.get(option.value) || 0,
            }));
        }"""
    )


def audit(url: str, *, headless: bool, screenshot_dir: Path | None) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    console_errors: list[str] = []
    blocked_requests: list[str] = []
    screenshots: list[str] = []

    chrome_path = DEFAULT_CHROME if DEFAULT_CHROME.exists() else None
    auth = load_basic_auth()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            executable_path=str(chrome_path) if chrome_path else None,
        )
        context_kwargs: dict[str, Any] = {
            "viewport": {"width": 1440, "height": 1100},
            "ignore_https_errors": True,
        }
        if auth:
            context_kwargs["http_credentials"] = auth
        context = browser.new_context(**context_kwargs)
        page = context.new_page()

        page.on(
            "console",
            lambda msg: console_errors.append(msg.text)
            if msg.type in {"error", "warning"} and "favicon" not in msg.text.lower()
            else None,
        )
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))

        def guard(route, request):
            path = urlparse(request.url).path.lower()
            risky = (
                request.method in {"POST", "PUT", "PATCH", "DELETE"}
                or path.startswith("/api/models/")
                or path == "/api/eval/run"
                or path == "/api/eval/reblend"
            )
            if risky:
                blocked_requests.append(f"{request.method} {request.url}")
                route.abort()
                return
            route.continue_()

        page.route("**/*", guard)
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_function("() => typeof appReady !== 'undefined' && appReady === true", timeout=120000)

        state = collect_state(page)
        assert_true(state["runCount"] >= 10, f"expected many run rows, got {state['runCount']}", failures)
        assert_true(state["caseCount"] >= 1000, f"expected case rows loaded, got {state['caseCount']}", failures)
        assert_true(state["modelCount"] >= 10, f"expected all model result rows, got {state['modelCount']}", failures)

        expected_labels = ["통과/실패 문항 개요", "문항별 모델 상세 응답"]
        body_text = page.locator("body").inner_text(timeout=10000)
        for label in expected_labels:
            assert_true(label in body_text, f"missing UI label: {label}", failures)

        for tab_id in ["settings", "caseSets", "runEval", "overview", "compare", "failures", "explorer", "search"]:
            click_tab(page, tab_id, failures)
            if screenshot_dir:
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                path = screenshot_dir / f"{tab_id}.png"
                page.screenshot(path=str(path), full_page=True)
                screenshots.append(str(path))

        click_tab(page, "overview", failures)
        assert_true(page.locator("#resultRunSelect option").count() >= 2, "run selector has fewer than two runs", failures)
        assert_true(page.locator("#resultMatrix .matrix-result-cell").count() > 0, "result matrix has no cells", failures)
        page.locator("#resultMatrix .matrix-result-cell:not(.empty)").first.click()
        page.wait_for_timeout(200)
        detail_text = safe_text(page, "#resultDetail")
        assert_true("모델 답변" in detail_text and "채점" in detail_text, "result detail does not show answer/scoring sections", failures)

        result_model_options = page.locator("#resultModelFilter option").count()
        assert_true(result_model_options >= state["modelCount"], "result model filter lost models", failures)
        page.locator("#resultViewMode").select_option("failures")
        page.wait_for_timeout(250)
        assert_true("실패 문항" in safe_text(page, "#resultMatrix"), "failure view label missing in matrix", failures)
        page.locator("#clearResultFilters").click()
        page.wait_for_timeout(250)

        click_tab(page, "search", failures)
        search_models = search_model_counts(page)
        assert_true(len(search_models) == state["modelCount"], f"global search model count mismatch: {len(search_models)} vs {state['modelCount']}", failures)
        empty_prompt = safe_text(page, "#globalSearchResults")
        assert_true("검색어를 입력하거나 모델을 선택하세요" in empty_prompt, "global search empty prompt missing", failures)
        missing_models: list[str] = []
        for item in search_models:
            page.locator("#globalSearchModel").select_option(item["value"])
            page.wait_for_timeout(120)
            result_text = safe_text(page, "#globalSearchResults")
            if "검색 결과가 없습니다" in result_text or not result_text:
                missing_models.append(item["label"])
        assert_true(not missing_models, f"global search returned no rows for models: {missing_models}", failures)
        page.locator("#clearGlobalSearch").click()
        page.wait_for_timeout(150)
        first_question = page.evaluate("() => (cases[0] && cases[0].question || '').slice(0, 8)")
        if first_question:
            page.locator("#globalSearchInput").fill(first_question)
            page.wait_for_timeout(250)
            assert_true("총 " in safe_text(page, "#globalSearchResults"), "global text search did not return result count", failures)

        click_tab(page, "explorer", failures)
        assert_true(page.locator("#questionSelect option").count() > 0, "question selector is empty", failures)
        explorer_text = safe_text(page, "#questionDetail")
        assert_true("모델" in explorer_text and "채점" in explorer_text, "question detail table missing model/scoring columns", failures)
        first_question_id = page.locator("#questionSelect option").first.get_attribute("value")
        if first_question_id:
            page.locator("#questionSearch").fill(first_question_id[:8])
            page.wait_for_timeout(250)
            assert_true(page.locator("#questionSelect option").count() > 0, "question search emptied all options unexpectedly", failures)

        click_tab(page, "failures", failures)
        for subtab in ["failure-overview", "failure-benchmark", "failure-regression", "failure-exploratory", "failure-review"]:
            page.locator(f'[data-subtab-target="{subtab}"]').click()
            page.wait_for_timeout(200)
            active = page.locator(f'[data-subtab-panel="{subtab}"]').evaluate("el => el.classList.contains('active')")
            assert_true(active, f"{subtab} subtab did not activate", failures)

        click_tab(page, "compare", failures)
        assert_true(page.locator("#compareChart .compare-row").count() > 0, "compare chart has no rows", failures)
        page.locator('[data-compare-action="top2"]').click()
        page.wait_for_timeout(250)
        assert_true("1대1 비교 모드" in safe_text(page, "#compareControls"), "top2 compare action did not switch to head-to-head mode", failures)
        page.locator('[data-compare-action="all"]').click()
        page.wait_for_timeout(250)

        click_tab(page, "caseSets", failures)
        for subtab in ["case-preview", "case-distribution", "case-samples"]:
            page.locator(f'[data-subtab-target="{subtab}"]').click()
            page.wait_for_timeout(300)
            active = page.locator(f'[data-subtab-panel="{subtab}"]').evaluate("el => el.classList.contains('active')")
            assert_true(active, f"{subtab} subtab did not activate", failures)
        assert_true(page.locator("#datasetSelect option").count() > 0, "dataset selector is empty", failures)
        page.locator('[data-subtab-target="case-preview"]').click()
        page.wait_for_timeout(200)
        page.locator("#runWithSelectedDataset").click()
        page.wait_for_timeout(200)
        assert_true(visible_panel_id(page) == "runEval", "runWithSelectedDataset did not navigate to run tab", failures)

        click_tab(page, "settings", failures)
        assert_true(page.locator("#modelRegistryForm").count() == 1, "model registry form missing", failures)
        assert_true(page.locator("#judgeRegistryForm").count() == 1, "judge registry form missing", failures)
        registry_controls = page.evaluate(
            """() => ({
                targets: document.querySelectorAll('#targetRegistryList .target-registry-item').length,
                deleteButtons: document.querySelectorAll('#targetRegistryList [data-delete-model]').length,
                defaultBadges: [...document.querySelectorAll('#targetRegistryList .registry-badge')]
                    .filter((el) => el.textContent.trim() === '기본').length,
            })"""
        )
        assert_true(registry_controls["targets"] > 0, "target registry list is empty", failures)
        assert_true(
            registry_controls["deleteButtons"] == registry_controls["targets"],
            f"target registry delete buttons mismatch: {registry_controls}",
            failures,
        )
        assert_true(registry_controls["defaultBadges"] == 0, "target registry still shows default badges", failures)

        if console_errors:
            warnings.append(f"console messages: {console_errors[:8]}")
        if blocked_requests:
            warnings.append(f"blocked risky requests during audit: {blocked_requests[:8]}")

        browser.close()

    return {
        "url": url,
        "state": state,
        "failures": failures,
        "warnings": warnings,
        "screenshots": screenshots,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Final UI user flows without calling costly APIs.")
    parser.add_argument("--url", default="http://127.0.0.1:8512/")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--screenshots", default="")
    args = parser.parse_args()

    screenshot_dir = Path(args.screenshots) if args.screenshots else None
    report = audit(args.url, headless=not args.headed, screenshot_dir=screenshot_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
