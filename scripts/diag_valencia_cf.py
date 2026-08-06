"""One-off Valencia CF diagnostic (run on Pi)."""

from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright

URL = "https://valencia.pasport.org.ua/solutions/e-queue"


async def probe(headless: bool, ua: str, wait_extra_ms: int) -> None:
    print(f"\n=== headless={headless} wait_extra_ms={wait_extra_ms} ===")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        context = await browser.new_context(
            user_agent=ua,
            locale="uk-UA",
            viewport={"width": 1280, "height": 720},
            extra_http_headers={"Accept-Language": "uk-UA,uk;q=0.9,en;q=0.8"},
        )
        page = await context.new_page()
        resp = await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        print("goto", resp.status if resp else None, page.url)
        await page.wait_for_timeout(wait_extra_ms)
        # Try waiting for either marker or CF clear
        try:
            await page.wait_for_function(
                """() => {
                  const t = document.body ? document.body.innerText : '';
                  return t.includes('Наразі всі місця зайняті')
                    || t.includes('Оберіть послугу')
                    || t.includes('Выберите услугу')
                    || document.querySelector('[name=services], #form_queue, form');
                }""",
                timeout=20000,
            )
            print("wait_for_function: content ready")
        except Exception as exc:
            print("wait_for_function:", type(exc).__name__, str(exc)[:120])

        html = await page.content()
        title = await page.title()
        lower = html.lower()
        text = await page.inner_text("body")
        markers = {
            "just_a_moment": "just a moment" in lower,
            "cf_challenge": "cf-challenge" in lower or "challenge-platform" in lower,
            "no_slots": "наразі всі місця зайняті" in text.lower(),
            "choose_service": "оберіть послугу" in text.lower() or "выберите услугу" in text.lower(),
            "services": 'name="services"' in lower or "form_queue" in lower,
            "turnstile": "turnstile" in lower or "cf-turnstile" in lower,
        }
        print("title", title)
        print("final_url", page.url)
        print("html_len", len(html), "markers", markers)
        print("text_snip", " ".join(text.split())[:300])
        path = f"/tmp/valencia_{'hl' if headless else 'headed'}.html"
        open(path, "w", encoding="utf-8").write(html)
        print("saved", path)
        await browser.close()


async def main() -> None:
    ua_chrome = (
        "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    await probe(True, ua_chrome, 3000)
    await probe(True, ua_chrome, 12000)


if __name__ == "__main__":
    asyncio.run(main())
