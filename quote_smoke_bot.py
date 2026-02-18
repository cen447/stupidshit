#!/usr/bin/env python3
"""Smoke-test bot for the Parallel 29 quote form."""

from __future__ import annotations

import argparse
import asyncio
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from time import time_ns

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Page, async_playwright


DEFAULT_URL = "https://www.parallel29.com/quote"
SUCCESS_TEXT = "Request received."
DEFAULT_CHROME_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
)

REASON_LABELS = {
    "relocating": "Select Relocating",
    "new-car-purchase": "Select New car purchase",
    "classic-luxury-car": "Select Classic / luxury car",
    "dealership-transport": "Select Dealership transport",
}

TEAM_NAMES = [
    "Usama Lola",
    "Syed Hurrrr",
    "Zaid Ali T",
    "Daddy Usman",
    "Sahibzada Haider",
    "Syed Asad Abbas",
    "Popalzai Abdullah",
    "Rohan",
]

PAKISTANI_CASTES = [
    "Bhatti",
    "Rana",
    "Junejo",
    "Butt",
    "Mughal",
    "Waraich",
    "Malik",
    "Khan",
    "Sheikh",
    "Rajput",
    "Chaudhry",
    "Awan",
    "Jatt",
    "Arain",
    "Qureshi",
    "Siddiqui",
    "Farooqi",
    "Abbasi",
    "Niazi",
    "Khokhar",
    "Gujjar",
    "Ansari",
    "Mirza",
    "Baloch",
    "Leghari",
    "Mazari",
    "Burki",
    "Afridi",
    "Bangash",
    "Durrani",
    "Tanoli",
    "Khattak",
    "Jamali",
    "Talpur",
    "Brohi",
    "Soomro",
    "Memon",
]

PAKISTANI_MARKET_CARS = [
    ("Suzuki", "Mehran"),
    ("Daihatsu", "Charade"),
    ("Daihatsu", "Cuore"),
    ("Suzuki", "Khyber"),
    ("Suzuki", "Bolan"),
    ("Suzuki", "Ravi"),
    ("Suzuki", "Margalla"),
    ("Hyundai", "Santro"),
    ("KIA", "Classic"),
    ("Nissan", "Sunny"),
    ("Toyota", "Corolla XE"),
    ("Honda", "Civic EXi"),
    ("Suzuki", "Alto"),
    ("Suzuki", "Cultus"),
    ("Suzuki", "Wagon R"),
    ("Suzuki", "Swift"),
    ("Toyota", "Corolla"),
    ("Toyota", "Yaris"),
    ("Honda", "City"),
    ("Honda", "Civic"),
    ("KIA", "Sportage"),
    ("Hyundai", "Elantra"),
    ("Changan", "Alsvin"),
    ("MG", "HS"),
]

US_DOMESTIC_LANES = [
    ("Los Angeles, CA", "Dallas, TX"),
    ("Miami, FL", "Atlanta, GA"),
    ("Seattle, WA", "Phoenix, AZ"),
    ("Chicago, IL", "Denver, CO"),
    ("San Diego, CA", "Houston, TX"),
    ("New York, NY", "Charlotte, NC"),
    ("Orlando, FL", "Nashville, TN"),
    ("Portland, OR", "Las Vegas, NV"),
    ("Boston, MA", "Washington, DC"),
    ("San Jose, CA", "Salt Lake City, UT"),
]


@dataclass
class QuoteData:
    reason: str
    pickup_location: str
    dropoff_location: str
    pickup_date: str
    dropoff_date: str
    vehicle_year: str
    vehicle_make: str
    vehicle_model: str
    notes: str
    trailer_type: str
    contact_name: str
    contact_email: str
    contact_phone: str


@dataclass
class QuoteRunResult:
    run_id: int
    ok: bool
    status: int | None = None
    error: str = ""


async def goto_with_retry(page: Page, url: str, attempts: int = 4) -> None:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=120_000)
            return
        except Exception as exc:  # noqa: BLE001 - surface final error to caller
            last_error = exc
            await page.wait_for_timeout(1200 * attempt)
    raise RuntimeError(f"Unable to open {url}") from last_error


async def wait_for_quote_form_ready(page: Page, timeout_ms: int) -> None:
    reason_button = page.get_by_role("button", name="Select Relocating")
    checkpoint_header = page.get_by_text("We're verifying your browser")
    checkpoint_footer = page.get_by_text("Vercel Security Checkpoint")
    loop = asyncio.get_running_loop()
    deadline = loop.time() + (timeout_ms / 1000)
    polls = 0
    last_state = f"url={page.url}"

    while loop.time() < deadline:
        if await reason_button.count() and await reason_button.first.is_visible():
            return

        if await checkpoint_header.count() or await checkpoint_footer.count():
            last_state = "vercel-security-checkpoint"
        else:
            last_state = f"url={page.url}"

        polls += 1
        if polls % 15 == 0:
            try:
                await page.reload(wait_until="domcontentloaded", timeout=60_000)
            except Exception:
                pass

        await page.wait_for_timeout(1000)

    raise RuntimeError(
        f"Quote form not ready after {timeout_ms}ms. Last observed state: {last_state}"
    )


async def fill_quote(page: Page, data: QuoteData) -> int:
    await page.get_by_role("button", name=REASON_LABELS[data.reason]).click()
    await page.get_by_role("button", name="Next").click()

    await page.fill("input[name='pickup_location']", data.pickup_location)
    await page.fill("input[name='dropoff_location']", data.dropoff_location)
    await page.get_by_role("button", name="Next").click()

    date_inputs = page.locator("input[type='date']")
    if await date_inputs.count() < 2:
        raise RuntimeError("Expected two date inputs in the DATES step.")
    await date_inputs.nth(0).fill(data.pickup_date)
    await date_inputs.nth(1).fill(data.dropoff_date)
    await page.get_by_role("button", name="Next").click()

    await page.fill("input[name='vehicle_year']", data.vehicle_year)
    await page.fill("input[name='vehicle_make']", data.vehicle_make)
    await page.fill("input[name='vehicle_model']", data.vehicle_model)
    await page.fill("textarea[name='notes']", data.notes)
    await page.get_by_role("button", name="Next").click()

    trailer_selector = f"input[name='trailer_type'][value='{data.trailer_type}']"
    await page.locator(trailer_selector).evaluate(
        """el => {
            el.checked = true;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }"""
    )
    await page.get_by_role("button", name="Next").click()

    await page.fill("input[name='contact_name']", data.contact_name)
    await page.fill("input[name='contact_email']", data.contact_email)
    await page.fill("input[name='contact_phone']", data.contact_phone)
    await page.check("input[name='consent']")

    async with page.expect_response("**/api/quote", timeout=30_000) as submit_response:
        await page.get_by_role("button", name="View my quote").click()

    response = await submit_response.value
    return response.status


def build_run_path(base_path: str, run_id: int, total_runs: int) -> str:
    if not base_path:
        return ""
    if total_runs == 1:
        return base_path
    path = Path(base_path)
    return str(path.with_name(f"{path.stem}-run-{run_id:04d}{path.suffix}"))


def build_attempt_path(base_path: str, attempt: int, total_attempts: int) -> str:
    if not base_path:
        return ""
    if total_attempts == 1:
        return base_path
    path = Path(base_path)
    return str(path.with_name(f"{path.stem}-attempt-{attempt:02d}{path.suffix}"))


def build_contact_email(base_email: str, run_id: int, total_runs: int) -> str:
    if base_email:
        if total_runs == 1:
            return base_email
        local, sep, domain = base_email.partition("@")
        if sep:
            return f"{local}+run{run_id}@{domain}"
        return f"{base_email}.run{run_id}"
    return f"smoketest+parallel29-{time_ns()}-{run_id}@example.com"


async def run_once(browser, args: argparse.Namespace, run_id: int) -> QuoteRunResult:
    attempts = args.run_retries + 1
    last_error = ""

    for attempt in range(1, attempts + 1):
        context = await browser.new_context(
            viewport={"width": 1440, "height": 2200},
            locale="en-US",
            user_agent=DEFAULT_CHROME_UA,
        )
        page = await context.new_page()
        page.set_default_timeout(args.action_timeout_ms)
        page.set_default_navigation_timeout(args.navigation_timeout_ms)

        try:
            await goto_with_retry(page, args.url, attempts=args.goto_attempts)
            await page.wait_for_timeout(args.initial_wait_ms)
            await wait_for_quote_form_ready(page, timeout_ms=args.ready_timeout_ms)

            quote_data = build_quote_data(args, run_id)
            if args.log_each or args.runs == 1:
                print(f"[run {run_id}] contact: {quote_data.contact_name}")
                print(
                    f"[run {run_id}] vehicle: "
                    f"{quote_data.vehicle_year} {quote_data.vehicle_make} {quote_data.vehicle_model}"
                )
                print(
                    f"[run {run_id}] lane: "
                    f"{quote_data.pickup_location} -> {quote_data.dropoff_location}"
                )
                print(f"[run {run_id}] trailer: {quote_data.trailer_type}")

            status = await fill_quote(page, quote_data)
            if status != 200:
                raise RuntimeError(f"Quote API returned unexpected status: {status}")

            await page.get_by_text(SUCCESS_TEXT).first.wait_for(timeout=20_000)

            screenshot_path = build_run_path(args.screenshot, run_id, args.runs)
            if screenshot_path:
                await page.screenshot(path=screenshot_path, full_page=True)

            return QuoteRunResult(run_id=run_id, ok=True, status=status)
        except Exception as exc:  # noqa: BLE001 - report run-level failures
            last_error = str(exc)
            failure_path = build_run_path(args.failure_screenshot, run_id, args.runs)
            failure_path = build_attempt_path(failure_path, attempt=attempt, total_attempts=attempts)
            if failure_path:
                await page.screenshot(path=failure_path, full_page=True)

            if attempt < attempts and (args.log_each or args.runs == 1):
                print(f"[run {run_id}] attempt {attempt} failed, retrying: {last_error}")
        finally:
            await context.close()

    return QuoteRunResult(run_id=run_id, ok=False, error=last_error)


async def run(args: argparse.Namespace) -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=not args.headful)
        try:
            if args.runs == 1:
                result = await run_once(browser, args, run_id=1)
                if not result.ok:
                    raise RuntimeError(result.error)
                print("Quote smoke test passed.")
                print(f"POST /api/quote status: {result.status}")
                print(f"Success text found: {SUCCESS_TEXT}")
                return

            semaphore = asyncio.Semaphore(args.concurrency)

            async def bounded_run(run_id: int) -> QuoteRunResult:
                async with semaphore:
                    return await run_once(browser, args, run_id=run_id)

            tasks = [
                asyncio.create_task(bounded_run(run_id))
                for run_id in range(1, args.runs + 1)
            ]
            results: list[QuoteRunResult] = []
            passed = 0
            failed = 0

            for task in asyncio.as_completed(tasks):
                result = await task
                results.append(result)
                if result.ok:
                    passed += 1
                else:
                    failed += 1

                completed = passed + failed
                if completed % args.progress_every == 0 or completed == args.runs:
                    print(
                        "Progress: "
                        f"{completed}/{args.runs} complete (passed={passed}, failed={failed})"
                    )

            print(f"Bulk run complete: total={args.runs}, passed={passed}, failed={failed}")
            if failed:
                failed_ids = [str(result.run_id) for result in results if not result.ok]
                print(f"Failed run IDs: {', '.join(failed_ids[:25])}")
                first_error = next(result.error for result in results if not result.ok)
                raise RuntimeError(f"{failed} run(s) failed. First error: {first_error}")
        finally:
            await browser.close()


def build_quote_data(args: argparse.Namespace, run_id: int) -> QuoteData:
    email = build_contact_email(args.contact_email, run_id=run_id, total_runs=args.runs)

    random_make, random_model = random.choice(PAKISTANI_MARKET_CARS)
    random_year = str(random.randint(2015, date.today().year))
    random_contact_name = f"{random.choice(TEAM_NAMES)} {random.choice(PAKISTANI_CASTES)}"
    random_pickup, random_dropoff = random.choice(US_DOMESTIC_LANES)
    random_trailer_type = random.choice(("open", "enclosed"))

    today = date.today()
    pickup = today + timedelta(days=args.pickup_in_days)
    dropoff = pickup + timedelta(days=args.delivery_after_days)

    return QuoteData(
        reason=args.reason,
        pickup_location=args.pickup_location or random_pickup,
        dropoff_location=args.dropoff_location or random_dropoff,
        pickup_date=pickup.isoformat(),
        dropoff_date=dropoff.isoformat(),
        vehicle_year=args.vehicle_year or random_year,
        vehicle_make=args.vehicle_make or random_make,
        vehicle_model=args.vehicle_model or random_model,
        notes=args.notes,
        trailer_type=(
            random_trailer_type if args.trailer_type == "random" else args.trailer_type
        ),
        contact_name=args.contact_name or random_contact_name,
        contact_email=email,
        contact_phone=args.contact_phone,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test bot for parallel29.com/quote")
    parser.add_argument("--url", default=DEFAULT_URL, help="Quote form URL.")
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Total number of submissions to execute.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="How many submissions to run in parallel.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=10,
        help="Print progress every N completed runs in bulk mode.",
    )
    parser.add_argument(
        "--log-each",
        action="store_true",
        help="Print randomized run details for every run.",
    )
    parser.add_argument(
        "--reason",
        default="relocating",
        choices=tuple(REASON_LABELS.keys()),
        help="Transport reason option.",
    )
    parser.add_argument(
        "--pickup-location",
        default="",
        help="Random US pickup location if omitted (must pair with --dropoff-location).",
    )
    parser.add_argument(
        "--dropoff-location",
        default="",
        help="Random US dropoff location if omitted (must pair with --pickup-location).",
    )
    parser.add_argument("--pickup-in-days", type=int, default=7)
    parser.add_argument("--delivery-after-days", type=int, default=3)
    parser.add_argument("--vehicle-year", default="", help="Random Pakistan-market year if omitted.")
    parser.add_argument("--vehicle-make", default="", help="Random Pakistan-market make if omitted.")
    parser.add_argument(
        "--vehicle-model",
        default="",
        help="Random Pakistan-market model if omitted.",
    )
    parser.add_argument("--notes", default="Automated smoke test submission")
    parser.add_argument(
        "--trailer-type",
        choices=("open", "enclosed", "random"),
        default="random",
        help="Random open/enclosed if omitted.",
    )
    parser.add_argument(
        "--contact-name",
        default="",
        help="Random team name + random Pakistani caste if omitted.",
    )
    parser.add_argument(
        "--contact-email",
        default="",
        help="Defaults to a unique example.com address if omitted.",
    )
    parser.add_argument("--contact-phone", default="4155552671")
    parser.add_argument(
        "--run-retries",
        type=int,
        default=2,
        help="Retry count per run for transient failures.",
    )
    parser.add_argument(
        "--goto-attempts",
        type=int,
        default=4,
        help="Navigation retries before failing an attempt.",
    )
    parser.add_argument(
        "--ready-timeout-ms",
        type=int,
        default=90_000,
        help="How long to wait for the quote form to become interactive.",
    )
    parser.add_argument(
        "--action-timeout-ms",
        type=int,
        default=45_000,
        help="Default timeout for form interactions.",
    )
    parser.add_argument(
        "--navigation-timeout-ms",
        type=int,
        default=120_000,
        help="Default timeout for page navigations.",
    )
    parser.add_argument("--initial-wait-ms", type=int, default=5000)
    parser.add_argument("--headful", action="store_true", help="Run with visible browser.")
    parser.add_argument("--screenshot", default="", help="Write a success screenshot to this path.")
    parser.add_argument(
        "--failure-screenshot",
        default="quote-smoke-failure.png",
        help="Write this screenshot if the run fails.",
    )

    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be >= 1")
    if args.concurrency < 1:
        parser.error("--concurrency must be >= 1")
    if args.run_retries < 0:
        parser.error("--run-retries must be >= 0")
    if args.goto_attempts < 1:
        parser.error("--goto-attempts must be >= 1")
    if args.ready_timeout_ms < 1:
        parser.error("--ready-timeout-ms must be >= 1")
    if args.action_timeout_ms < 1:
        parser.error("--action-timeout-ms must be >= 1")
    if args.navigation_timeout_ms < 1:
        parser.error("--navigation-timeout-ms must be >= 1")
    if args.progress_every < 1:
        parser.error("--progress-every must be >= 1")
    if args.pickup_in_days < 0:
        parser.error("--pickup-in-days must be >= 0")
    if args.delivery_after_days < 0:
        parser.error("--delivery-after-days must be >= 0")
    if args.vehicle_year and not args.vehicle_year.isdigit():
        parser.error("--vehicle-year must be numeric")
    if bool(args.pickup_location) != bool(args.dropoff_location):
        parser.error(
            "Provide both --pickup-location and --dropoff-location, or omit both for random."
        )
    if args.concurrency > args.runs:
        args.concurrency = args.runs

    if args.screenshot:
        Path(args.screenshot).parent.mkdir(parents=True, exist_ok=True)
    if args.failure_screenshot:
        Path(args.failure_screenshot).parent.mkdir(parents=True, exist_ok=True)
    return args


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(run(args))
    except PlaywrightError as exc:
        raise SystemExit(f"Playwright error: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Smoke test failed: {exc}") from exc


if __name__ == "__main__":
    main()
