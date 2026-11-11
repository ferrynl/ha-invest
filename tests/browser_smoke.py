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
