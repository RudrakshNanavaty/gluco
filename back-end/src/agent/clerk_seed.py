"""Seed Clerk with one account per demo participant, plus a few doctors.

    just seed-clerk --dry-run     # show what would happen
    just seed-clerk               # create or update the accounts
    just seed-clerk --full-roster # ... for all 66 people, even unpublished ones

Idempotent: accounts are matched on the `uuid` in their public_metadata, which is
derived from the participant id, so a rerun creates nothing twice and never resets
a password. Clerk is the only user store; `public_metadata` (writable only with
the secret key) carries `{uuid, role, participant_id, display_name}`.
"""

import argparse
import csv
import sys
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from faker import Faker

from agent.config import Settings
from agent.data.factory import build_source
from agent.store import WindowStore

CLERK_API = "https://api.clerk.com/v1"
NAMESPACE = uuid.UUID("5d0c3b8e-6a4f-4c52-9d1e-2f7b8a9c0e11")
PAGE = 500
DEFAULT_CSV = Path("var/clerk-seed.csv")


@dataclass(frozen=True)
class Account:
    uuid: str
    role: str
    participant_id: str | None
    first_name: str
    last_name: str
    username: str

    @property
    def display_name(self) -> str:
        prefix = "Dr. " if self.role == "clinician" else ""
        return f"{prefix}{self.first_name} {self.last_name}"

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            "uuid": self.uuid,
            "role": self.role,
            "participant_id": self.participant_id,
            "display_name": self.display_name,
        }


def full_roster() -> list[str]:
    """The 66-person `continuous-oct4-v1` cohort: 16 BIG IDEAs plus 50 IMU50.

    Mirrors the frozen roster in databricks/tiger/register_overnight.py. Tiger may
    publish only part of it (the 17-person smoke session), so this lets accounts
    exist before every participant's data does.
    """
    return [f"demo:big_ideas:{n:03d}" for n in range(1, 17)] + [
        f"demo:imu50:{n:02d}" for n in range(50)
    ]


def _name(key: str) -> tuple[str, str]:
    """A fake name that depends only on `key`, so it is stable across runs."""
    fake = Faker("en_US")
    fake.seed_instance(uuid.uuid5(NAMESPACE, key).int % 2**32)
    return fake.first_name(), fake.last_name()


def _slug(text: str) -> str:
    return "".join(c for c in text.lower() if c.isalnum())


def plan_accounts(
    participants: Iterable[str],
    doctors: int,
    taken_usernames: Iterable[str] = (),
    known: dict[str, str] | None = None,
) -> list[Account]:
    """Every account the demo should have, in a stable order.

    `known` maps uuid -> username of accounts that already exist; they keep their
    username. New accounts get `firstname-lastname` (Clerk allows only letters, numbers,
    `-` and `_`), with a number on a clash.
    """
    known = known or {}
    taken = {u.lower() for u in taken_usernames}
    accounts: list[Account] = []

    def build(key: str, role: str, pid: str | None, prefix: str = "") -> None:
        ident = str(uuid.uuid5(NAMESPACE, key))
        first, last = _name(key)
        username = known.get(ident)
        if username is None:
            base = f"{prefix}{_slug(first)}-{_slug(last)}"
            username, n = base, 1
            while username in taken:
                n += 1
                username = f"{base}{n}"
            taken.add(username)
        accounts.append(Account(ident, role, pid, first, last, username))

    for index in range(1, doctors + 1):
        build(f"clinician:{index}", "clinician", None, prefix="dr-")
    for pid in sorted(participants):
        build(f"patient:{pid}", "patient", pid)
    return accounts


class ClerkClient:
    def __init__(self, secret_key: str, http: httpx.Client | None = None) -> None:
        self._http = http or httpx.Client(
            base_url=CLERK_API,
            headers={"Authorization": f"Bearer {secret_key}"},
            timeout=30,
        )

    def users(self) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        while True:
            response = self._http.get(
                "/users", params={"limit": PAGE, "offset": len(found)}
            )
            response.raise_for_status()
            page = response.json()
            found.extend(page)
            if len(page) < PAGE:
                return found

    def create(self, account: Account, password: str) -> None:
        response = self._http.post(
            "/users",
            json={
                "username": account.username,
                "password": password,
                "first_name": account.first_name,
                "last_name": account.last_name,
                "public_metadata": account.metadata,
            },
        )
        if response.is_error:
            raise RuntimeError(
                f"creating {account.username!r} failed: "
                f"{response.status_code} {response.text}"
            )

    def update_metadata(self, clerk_id: str, account: Account) -> None:
        response = self._http.patch(
            f"/users/{clerk_id}/metadata",
            json={"public_metadata": account.metadata},
        )
        response.raise_for_status()


def sync(
    client: ClerkClient,
    accounts_for: Callable[[set[str], dict[str, str]], list[Account]],
    password: str | None,
    dry_run: bool,
) -> list[Account]:
    """Create missing accounts and fix drifted metadata; returns every account."""
    existing = client.users()
    by_uuid = {(u.get("public_metadata") or {}).get("uuid"): u for u in existing}
    accounts = accounts_for(
        {u["username"] for u in existing if u.get("username")},
        {
            ident: u["username"]
            for ident, u in by_uuid.items()
            if ident and u.get("username")
        },
    )
    created = updated = 0
    for account in accounts:
        current = by_uuid.get(account.uuid)
        if current is None:
            created += 1
            if not dry_run:
                if not password:
                    raise RuntimeError("CLERK_DEMO_PASSWORD is required")
                client.create(account, password)
        elif current.get("public_metadata") != account.metadata:
            updated += 1
            if not dry_run:
                client.update_metadata(current["id"], account)
    verb = "would create" if dry_run else "created"
    print(
        f"{verb} {created}, {'would update' if dry_run else 'updated'} {updated}, "
        f"unchanged {len(accounts) - created - updated}",
        file=sys.stderr,
    )
    return accounts


def write_csv(path: Path, accounts: Iterable[Account]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        out = csv.writer(handle)
        out.writerow(["username", "role", "uuid", "participant_id", "display_name"])
        for a in accounts:
            out.writerow(
                [a.username, a.role, a.uuid, a.participant_id or "", a.display_name]
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seed Clerk with one account per demo participant."
    )
    parser.add_argument("--dry-run", action="store_true", help="change nothing")
    parser.add_argument("--doctors", type=int, default=3)
    parser.add_argument(
        "--full-roster",
        action="store_true",
        help="also seed the whole 66-person cohort, not just what Tiger has published",
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args(argv)

    settings = Settings()  # pyright: ignore[reportCallIssue]
    secret = settings.clerk_secret_key
    if secret is None:
        print("CLERK_SECRET_KEY is not set (.env or environment)", file=sys.stderr)
        return 1
    password = settings.clerk_demo_password
    if password is None and not args.dry_run:
        print("CLERK_DEMO_PASSWORD is not set (.env or environment)", file=sys.stderr)
        return 1

    participants = WindowStore(build_source(settings)).participants()
    print(f"{len(participants)} participants in the data source", file=sys.stderr)
    if args.full_roster:
        participants = sorted({*participants, *full_roster()})
        print(f"{len(participants)} with the full roster", file=sys.stderr)

    accounts = sync(
        ClerkClient(secret.get_secret_value()),
        lambda taken, known: plan_accounts(participants, args.doctors, taken, known),
        password.get_secret_value() if password else None,
        args.dry_run,
    )
    if args.dry_run:
        for a in accounts:
            print(f"{a.role:9} {a.username}")
    else:
        write_csv(args.csv, accounts)
        print(f"wrote {args.csv}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
