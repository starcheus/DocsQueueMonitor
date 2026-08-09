"""Scrape DP Dokument centers for Vienna / Bratislava."""

from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="uk-UA",
        )
        page = await ctx.new_page()
        await page.goto(
            "https://berlin.pasport.org.ua/centers",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        await page.wait_for_timeout(5000)
        text = await page.inner_text("body")
        html = await page.content()
        for needle in [
            "Відень",
            "Вена",
            "Wien",
            "Vienna",
            "Австрія",
            "Austria",
            "Братислава",
            "Bratislava",
            "Словач",
        ]:
            hit = needle.lower() in text.lower() or needle.lower() in html.lower()
            print(f"needle {needle!r}: {hit}")

        links = await page.eval_on_selector_all(
            "a[href*='pasport.org.ua']",
            "els => els.map(e => [e.href, (e.innerText || '').trim()])",
        )
        interesting = []
        for href, label in links:
            blob = f"{href} {label}".lower()
            if any(
                k in blob
                for k in (
                    "bratislava",
                    "wien",
                    "vienna",
                    "відень",
                    "австр",
                    "словач",
                )
            ):
                interesting.append((href, " ".join(label.split())[:100]))
        for href, label in sorted(set(interesting)):
            print(f"LINK {href} | {label}")

        for key in ("словач", "австр", "братислав", "відень"):
            idx = text.lower().find(key)
            if idx >= 0:
                print(f"SNIP {key}:", " ".join(text[idx : idx + 350].split()))

        # probe candidate URLs
        for url in (
            "https://bratislava.pasport.org.ua/solutions/e-queue",
            "https://wien.pasport.org.ua/solutions/e-queue",
            "https://vienna.pasport.org.ua/solutions/e-queue",
        ):
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(2000)
            print(
                "PROBE",
                url,
                "status",
                resp.status if resp else None,
                "title",
                await page.title(),
            )
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
