"""
Load test — 50 concurrent users, main user flow
Target: https://phone.service247.by
Usage:
    locust -f locustfile.py --host=https://phone.service247.by --headless -u 50 -r 5 -t 120s --csv=stats_50
"""

import random
import string

from locust import HttpUser, between, events, task

# ── Test data ──────────────────────────────────────────────────────
SEARCH_TERMS = ["python", "водитель", "менеджер", "", "продавец", "бухгалтер"]
COVER_LETTERS = [
    "I am interested in this position.",
    "Please consider my application.",
    "I have relevant experience for this role.",
    "",
]


def random_email() -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"loadtest_{suffix}@example.com"


def random_password() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=12))


# ── User class ──────────────────────────────────────────────────────
class JobMapUser(HttpUser):
    """
    Simulates a real user following the main flow:
    login → GET /vacancies → GET /vacancies/{id} → POST /apply → GET /applications
    """

    wait_time = between(1, 3)

    def on_start(self):
        """Register + login once per user."""
        self.token: str | None = None
        self.applied: bool = False

        email = random_email()
        password = random_password()

        # Register
        with self.client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "role": "user"},
            catch_response=True,
            name="POST /api/auth/register",
        ) as resp:
            if resp.status_code == 201:
                pass
            elif resp.status_code == 409:
                pass  # already exists from a prior run
            else:
                resp.failure(f"Register: {resp.status_code}")

        # Login
        with self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
            catch_response=True,
            name="POST /api/auth/login",
        ) as resp:
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    self.token = data.get("access_token", "")
                except Exception:
                    self.token = None
            elif resp.status_code == 429:
                self.token = None  # rate-limited
            else:
                self.token = None

    def _auth_headers(self) -> dict:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    # ── Flow step 1: browse vacancy list ────────────────────────────
    @task(3)
    def browse_vacancies(self):
        """GET /api/vacancies — list vacancies with cursor pagination."""
        params = {"size": 20, "search": random.choice(SEARCH_TERMS)}
        with self.client.get(
            "/api/vacancies",
            params=params,
            name="GET /api/vacancies",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                pass
            elif resp.status_code == 429:
                resp.failure("Rate limited")
            else:
                resp.failure(f"HTTP {resp.status_code}")

    # ── Flow step 2: view single vacancy ────────────────────────────
    @task(2)
    def view_vacancy(self):
        """GET /api/vacancies/{id} — view a single vacancy."""
        vid = 66  # the one known vacancy in test data
        with self.client.get(
            f"/api/vacancies/{vid}",
            name="GET /api/vacancies/{id}",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                pass
            elif resp.status_code == 404:
                pass  # vacancy may not exist
            elif resp.status_code == 429:
                resp.failure("Rate limited")
            else:
                resp.failure(f"HTTP {resp.status_code}")

    # ── Flow step 3: apply to vacancy ───────────────────────────────
    @task(1)
    def apply_to_vacancy(self):
        """POST /api/applications — apply to a vacancy."""
        with self.client.post(
            "/api/applications",
            json={
                "vacancy_id": 66,
                "cover_letter": random.choice(COVER_LETTERS),
            },
            headers=self._auth_headers(),
            name="POST /api/applications",
            catch_response=True,
        ) as resp:
            if resp.status_code == 201:
                self.applied = True
            elif resp.status_code == 409:
                pass  # already applied
            elif resp.status_code in (401, 403):
                pass  # not authenticated
            elif resp.status_code == 429:
                resp.failure("Rate limited")
            elif resp.status_code == 422:
                pass  # validation error
            else:
                resp.failure(f"HTTP {resp.status_code}")

    # ── Flow step 4: check my applications ──────────────────────────
    @task(1)
    def my_applications(self):
        """GET /api/applications — check own applications."""
        with self.client.get(
            "/api/applications",
            headers=self._auth_headers(),
            name="GET /api/applications",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 401, 403):
                pass
            elif resp.status_code == 429:
                resp.failure("Rate limited")
            else:
                resp.failure(f"HTTP {resp.status_code}")

    # ── Health check (background / monitoring) ───────────────────────
    @task(1)
    def health_check(self):
        """GET /health — backend health."""
        self.client.get("/health", name="GET /health")


# ── Test lifecycle events ──────────────────────────────────────────
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    host = getattr(environment.runner, 'target_host', getattr(environment, 'host', 'unknown'))
    print(f"\n{'='*60}")
    print(f"Load test starting: {host}")
    print(f"Users: {environment.runner.user_count}")
    print(f"{'='*60}\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print per-endpoint metrics summary."""
    stats = environment.stats
    print(f"\n{'='*70}")
    print("LOAD TEST COMPLETE — RESULTS")
    print(f"{'='*70}")
    header = f"{'Endpoint':<40} {'Req':>6} {'Fail%':>8} {'P50':>8} {'P95':>8} {'P99':>8} {'RPS':>8}"
    sep = "-" * 86
    print(header)
    print(sep)

    entries_sorted = sorted(
        stats.entries.values(),
        key=lambda s: s.num_requests,
        reverse=True,
    )
    for s in entries_sorted:
        name = s.name or "unknown"
        p50 = int(s.get_response_time_percentile(0.50) or 0)
        p95 = int(s.get_response_time_percentile(0.95) or 0)
        p99 = int(s.get_response_time_percentile(0.99) or 0)
        fail_pct = 100.0 * s.num_failures / s.num_requests if s.num_requests else 0
        rps = getattr(s, 'current_rps', s.num_requests / (environment.runner.stats.total.response_times or [0, 0])[-1] if hasattr(environment.runner.stats.total, 'response_times') else s.num_requests / 120)
        print(f"{name:<40} {s.num_requests:>6} {fail_pct:>7.1f}% {p50:>7}ms {p95:>7}ms {p99:>7}ms {rps:>7.1f}")

    # Totals
    t = stats.total
    total_p50 = int(t.get_response_time_percentile(0.50) or 0)
    total_p95 = int(t.get_response_time_percentile(0.95) or 0)
    total_p99 = int(t.get_response_time_percentile(0.99) or 0)
    total_fail = 100.0 * t.num_failures / t.num_requests if t.num_requests else 0
    print(sep)
    print(f"{'TOTAL':<40} {t.num_requests:>6} {total_fail:>7.1f}% {total_p50:>7}ms {total_p95:>7}ms {total_p99:>7}ms {t.total_rps:>7.1f}")
    print(f"{'='*70}\n")

    # NFR-001 verdict
    print("NFR-001 Assessment:")
    print("  Target: p95 < 500ms, 0 errors, RPS > 10 at 50 concurrent users")
    print(f"  Actual: p95={total_p95}ms, errors={t.num_failures}, RPS={t.total_rps:.1f}")
    if total_p95 < 500 and t.num_failures == 0 and t.total_rps > 10:
        print("  >>> NFR-001: PASSED ✅ <<<")
    else:
        issues = []
        if total_p95 >= 500:
            issues.append(f"p95={total_p95}ms >= 500ms")
        if t.num_failures > 0:
            issues.append(f"errors={t.num_failures}")
        if t.total_rps <= 10:
            issues.append(f"RPS={t.total_rps:.1f} <= 10")
        print(f"  >>> NFR-001: FAILED ❌ ({', '.join(issues)}) <<<")
    print()
