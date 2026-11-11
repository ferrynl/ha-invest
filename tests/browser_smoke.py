"""Real browser smoke test with an isolated, local portfolio."""
import sys
import tempfile
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "portfolio/app"))
from storage import Store
from security import Auth
from cache import StateCache
from web import make_handler


def main():
    with tempfile.TemporaryDirectory() as folder:
        store = Store(folder)
        auth = Auth(store)
        auth.enable("browseradmin", "Browser-test-password-2026")
        handler = make_handler(store, auth, StateCache(), {}, 900,
                               threading.Lock(), threading.Event(), enable_demo=False)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        origin = f"http://127.0.0.1:{server.server_port}"
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page()
                page.set_default_timeout(10000)
                page.set_default_navigation_timeout(12000)
                page.route("**/*", lambda route: route.continue_() if
                           route.request.url.startswith(origin + "/") else route.abort())
                page.goto(origin)
                onboarding = page.get_by_role('dialog', name='Kies je taal / Choose your language / Elige tu idioma')
                expect(onboarding).to_be_visible(timeout=15000)
                onboarding.get_by_role('button', name='Opslaan / Save / Guardar').click()
                expect(onboarding).to_be_hidden(timeout=15000)
                expect(page.locator("#login-panel")).to_be_visible(timeout=15000)
                page.locator("#login-form [name=username]").fill("browseradmin")
                page.locator("#login-form [name=password]").fill("Browser-test-password-2026")
                page.locator("#login-form button[type=submit]").click()
                expect(page.locator("#login-panel")).to_be_hidden(timeout=15000)
                expect(page.locator("#account-open")).to_be_visible(timeout=15000)
                expect(page.locator('[data-page="home"]')).to_be_visible()
                page.locator('a[data-route="dividend"]').click()
                expect(page).to_have_url(origin + "/#dividend")
                expect(page.locator('[data-page="dividend"]').first).to_be_visible()
                page.locator('a[data-route="transacties"]').click()
                expect(page).to_have_url(origin + "/#transacties")
                expect(page.locator('[data-page="transacties"]').first).to_be_visible()
                # Health Center: admin access, real health response and mobile layout.
                print('Health Center browser: open dashboard', flush=True)
                page.locator('a[data-route="health-center"]').click()
                expect(page).to_have_url(origin + "/#health-center")
                expect(page.locator('[data-page="health-center"]')).to_be_visible()
                expect(page.locator("#health-technical .health-check-item")).to_have_count(5)
                expect(page.locator("#health-financial .health-check-item")).to_have_count(8)
                expect(page.locator('a[data-route="health-center"] svg.nav-icon')).to_have_count(1)
                expect(page.locator("#health-summary")).not_to_have_text("Controles laden…")
                print('Health Center browser: desktop checks passed; resize mobile', flush=True)
                page.set_viewport_size({"width": 390, "height": 844})
                expect(page.locator("#health-technical .health-check-item")).to_have_count(5)
                shell = page.locator(".health-shell").bounding_box()
                assert shell and shell["x"] >= 0 and shell["x"] + shell["width"] <= 391, shell
                refresh = page.locator("#health-refresh").bounding_box()
                assert refresh and 38 <= refresh["height"] <= 52, refresh
                action = page.locator("#health-quotes").bounding_box()
                assert action and action["height"] <= 55, action
                print('Health Center browser: mobile measurements passed', flush=True)
                page.set_viewport_size({"width": 1280, "height": 900})
                print('Health Center browser: open account and logout', flush=True)
                page.locator('a[data-route="account"]').click()
                expect(page.locator("#logout")).to_be_visible()
                page.locator("#logout").click()
                expect(page.locator("#login-panel")).to_be_visible(timeout=15000)
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            worker.join()


if __name__ == "__main__":
    main()
