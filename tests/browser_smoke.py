"""Optional browser check: pip install playwright, then run this file."""
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
EDGE = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")


def main():
    ARTIFACTS.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=str(EDGE), headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1200}, device_scale_factor=1)
        page.set_default_timeout(60_000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        response = page.goto("http://127.0.0.1:7860/", wait_until="networkidle", timeout=60_000)
        assert response.status == 200
        try:
            page.get_by_role("heading", name="Bring your words to life.").wait_for()
        except Exception:
            print("Browser errors:", errors, flush=True)
            print("Page content:", page.locator("body").inner_text()[:2000], flush=True)
            page.screenshot(path=str(ARTIFACTS / "browser-failure.png"), full_page=True)
            raise
        choices = page.locator("#character-choices input[type=radio]")
        expect(choices).to_have_count(12, timeout=60_000)
        page.get_by_role("radio", name="Michael", exact=False).check()
        page.get_by_role("button", name="Generate speech · Michael").wait_for()
        assert "Michael" in page.locator(".selected-character").inner_text()
        script = page.locator("#script-editor textarea")
        sample_text = "Welcome to Voice Studio. A character for every story."
        script.fill(sample_text)
        page.wait_for_function(
            "(count) => document.querySelector('.script-statistics strong').textContent === String(count)",
            arg=len(sample_text),
        )
        assert script.get_attribute("maxlength") == "20000"
        page.get_by_role("button", name="Presentation", exact=True).click()
        page.wait_for_function("document.querySelector('#script-editor textarea').value.startsWith('Good morning')")
        preview = page.get_by_role("button", name="Preview this voice", exact=True)
        preview.click()
        page.locator("#speech-status").filter(has_text="Voice preview").wait_for(timeout=120_000)
        assert script.input_value().startswith("Good morning"), "Preview changed the main script"
        play_button = page.locator("#speech-output").get_by_role("button", name="Play", exact=True)
        play_button.wait_for(state="visible", timeout=30_000)
        play_button.click()
        pause_button = page.locator("#speech-output").get_by_role("button", name="Pause", exact=True)
        pause_button.wait_for(state="visible", timeout=10_000)
        pause_button.click()
        assert page.locator("#speech-download").bounding_box()["height"] < 150, "Download panel is too tall"
        page.screenshot(path=str(ARTIFACTS / "voice-studio-desktop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_function("window.matchMedia('(max-width: 540px)').matches")
        page.screenshot(path=str(ARTIFACTS / "voice-studio-mobile.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Mobile layout overflows"
        assert page.locator("#script-editor").bounding_box()["width"] >= 300, "Mobile editor is too narrow"
        assert page.locator("#character-choices").bounding_box()["y"] < page.locator("#script-editor").bounding_box()["y"], "Mobile character selection should come first"
        page.get_by_role("button", name="Clear script", exact=True).click()
        page.wait_for_function("document.querySelector('#script-editor textarea').value === ''")
        assert not errors, f"Browser errors: {errors}"
        print("Browser checks passed: 12 voices, selection, voice preview/playback, counters, samples, clear, mobile layout.")
        browser.close()


if __name__ == "__main__":
    main()
