"""NorthBridge Bank AML seed data generator.

Generates the four historical (batch) source datasets for the AML monitoring
lakehouse project. Plain Python standard library on purpose: no pip installs
needed, just `python generate_seed_data.py`.

Outputs (into ./data):
  customers.csv                  8,000 customers
  branches.csv                   30 branches
  accounts.csv                   ~10,500 accounts (some customers hold 2-3)
  transactions.csv               ~180,000 transactions, Jan 1 - Jun 30 2026
                                  (intentionally dirty: duplicate txn rows,
                                  mixed-case currency codes, mixed timestamp
                                  formats/timezones, nulls, plus deliberately
                                  injected structuring and rapid in-out
                                  patterns for downstream AML rule-building)

Every table carries lineage/audit columns (created_at, created_by /
source_system) so you can practice building an ingestion audit trail on
top of this.

NOTE: all customer identity fields (name, dob, ssn_hash) are synthetic /
randomly generated. No real personal data is used anywhere in this script.
"""

import csv
import os
import random
import uuid
from datetime import datetime, timedelta

random.seed(42)  # same data for every run

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

FIRST_NAMES = [
    "Aarav", "Priya", "Rahul", "Sneha", "Vikram", "Ananya", "Karan", "Divya",
    "Arjun", "Meera", "Rohan", "Isha", "Aditya", "Pooja", "Nikhil", "Riya",
    "James", "Emma", "Liam", "Olivia", "Noah", "Ava", "Ethan", "Sophia",
    "Lucas", "Mia", "Mason", "Amelia", "Diego", "Lucia", "Wei", "Yuki",
    "Fatima", "Omar", "Layla", "Hassan", "Elena", "Ivan", "Chen", "Mei",
]
LAST_NAMES = [
    "Sharma", "Patel", "Singh", "Kumar", "Gupta", "Reddy", "Nair", "Mehta",
    "Smith", "Johnson", "Brown", "Garcia", "Miller", "Davis", "Chen", "Tanaka",
    "Wilson", "Anderson", "Martinez", "Lopez", "Al-Sayed", "Khan", "Zhang", "Ivanov",
]

COUNTRIES = ["IN", "US", "CN", "AE", "GB", "SG", "DE", "CA", "NG", "RU", "AU"]
HIGH_RISK_COUNTRIES = {"RU", "NG"}  # used later to seed high_risk_country flags

RISK_RATINGS = ["low", "low", "low", "medium", "medium", "high"]
KYC_STATUSES = ["verified", "verified", "verified", "pending", "expired"]

REGIONS = {
    "IN": "APAC", "CN": "APAC", "SG": "APAC", "AU": "APAC",
    "US": "AMER", "CA": "AMER",
    "GB": "EMEA", "DE": "EMEA", "RU": "EMEA",
    "AE": "MEA", "NG": "MEA",
}
CITY_BY_COUNTRY = {
    "IN": ["Mumbai", "Bengaluru", "Delhi", "Hyderabad", "Pune"],
    "US": ["New York", "San Francisco", "Chicago", "Austin", "Miami"],
    "CN": ["Shanghai", "Beijing", "Shenzhen"],
    "AE": ["Dubai", "Abu Dhabi"],
    "GB": ["London", "Manchester"],
    "SG": ["Singapore"],
    "DE": ["Berlin", "Frankfurt"],
    "CA": ["Toronto", "Vancouver"],
    "NG": ["Lagos", "Abuja"],
    "RU": ["Moscow", "St Petersburg"],
    "AU": ["Sydney", "Melbourne"],
}

ACCOUNT_TYPES = ["checking", "savings", "business"]
CURRENCY_BY_COUNTRY = {
    "IN": "INR", "US": "USD", "CN": "CNY", "AE": "AED", "GB": "GBP",
    "SG": "SGD", "DE": "EUR", "CA": "CAD", "NG": "NGN", "RU": "RUB", "AU": "AUD",
}
CHANNELS = ["branch", "atm", "mobile", "wire", "online"]
TXN_TYPES = ["deposit", "withdrawal", "transfer_in", "transfer_out", "wire_in", "wire_out"]

SOURCE_SYSTEMS = ["CORE_BANKING_V2", "MOBILE_GATEWAY", "BRANCH_POS", "WIRE_SWIFT_GW"]

REPORTING_THRESHOLD = {
    "USD": 10000, "EUR": 10000, "GBP": 8000, "INR": 800000, "CNY": 65000,
    "AED": 36000, "SGD": 13500, "CAD": 13500, "NGN": 4500000, "RUB": 900000,
    "AUD": 15000,
}


def now_iso():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def rand_date(start_year, start_month, start_day, end_year, end_month, end_day):
    start = datetime(start_year, start_month, start_day)
    end = datetime(end_year, end_month, end_day)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, max(delta, 0)))


def fake_ssn_hash():
    return uuid.uuid4().hex[:12]


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

def gen_customers(n=8000):
    rows = []
    for i in range(1, n + 1):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        country = random.choice(COUNTRIES)
        dob = rand_date(1955, 1, 1, 2005, 12, 31)
        created_at = rand_date(2018, 1, 1, 2026, 6, 30)

        risk_rating = random.choice(RISK_RATINGS)
        kyc_status = random.choice(KYC_STATUSES)

        # ~3% missing risk_rating (not yet scored), ~2% missing kyc_status
        if random.random() < 0.03:
            risk_rating = ""
        if random.random() < 0.02:
            kyc_status = ""
        # ~1% missing country (bad upstream capture)
        row_country = country if random.random() > 0.01 else ""

        row = {
            "customer_id": f"CUST{i:06d}",
            "name": f"{first} {last}",
            "dob": dob.strftime("%Y-%m-%d"),
            "ssn_hash": fake_ssn_hash(),
            "risk_rating": risk_rating,
            "kyc_status": kyc_status,
            "country": row_country,
            "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "created_by": "CUSTOMER_ONBOARDING_SVC",
        }
        rows.append(row)
        # ~1% duplicate customer record (simulates re-sent onboarding event)
        if random.random() < 0.01:
            dup = dict(row)
            dup["created_at"] = (created_at + timedelta(minutes=random.randint(1, 90))).strftime("%Y-%m-%d %H:%M:%S")
            rows.append(dup)
    return rows


# ---------------------------------------------------------------------------
# Branches
# ---------------------------------------------------------------------------

def gen_branches():
    rows = []
    bid = 1
    for country in COUNTRIES:
        cities = CITY_BY_COUNTRY[country]
        n_branches = random.randint(2, 4)
        for _ in range(n_branches):
            city = random.choice(cities)
            row = {
                "branch_id": f"BR{bid:04d}",
                "branch_name": f"{city} {random.choice(['Downtown', 'Central', 'North', 'Marina', 'Fort', 'Plaza'])}",
                "city": city,
                "country": country,
                "region_code": REGIONS[country],
                "created_at": rand_date(2015, 1, 1, 2020, 1, 1).strftime("%Y-%m-%d %H:%M:%S"),
                "created_by": "BRANCH_REGISTRY_SVC",
            }
            rows.append(row)
            bid += 1
    # a couple of duplicate branch rows (registry re-published same branch)
    for _ in range(2):
        rows.append(dict(random.choice(rows)))
    return rows


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

def gen_accounts(customers, branches):
    rows = []
    aid = 1
    branches_by_country = {}
    for b in branches:
        branches_by_country.setdefault(b["country"], []).append(b)

    for cust in customers:
        country = cust["country"] or random.choice(COUNTRIES)
        n_accounts = random.choices([1, 2, 3], weights=[70, 24, 6])[0]
        for _ in range(n_accounts):
            local_branches = branches_by_country.get(country) or branches
            branch = random.choice(local_branches)
            open_date = rand_date(2018, 1, 1, 2026, 6, 1)
            status = random.choices(["active", "active", "active", "dormant", "closed"], weights=[70, 10, 10, 5, 5])[0]

            # ~2% missing branch_id (bad legacy migration), ~1.5% missing status
            row_branch_id = branch["branch_id"] if random.random() > 0.02 else ""
            row_status = status if random.random() > 0.015 else ""

            row = {
                "account_id": f"ACC{aid:07d}",
                "customer_id": cust["customer_id"],
                "account_type": random.choice(ACCOUNT_TYPES),
                "currency": CURRENCY_BY_COUNTRY[country],
                "branch_id": row_branch_id,
                "open_date": open_date.strftime("%Y-%m-%d"),
                "status": row_status,
                "created_at": open_date.strftime("%Y-%m-%d %H:%M:%S"),
                "created_by": "ACCOUNT_OPENING_SVC",
            }
            rows.append(row)
            aid += 1
            # ~1% duplicate account row (retry on account-opening event)
            if random.random() < 0.01:
                rows.append(dict(row))
    return rows


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

def make_ts(base_dt, iso_with_tz=False):
    """Return a timestamp string, sometimes plain, sometimes ISO8601+offset —
    deliberately inconsistent to force timezone-normalization work."""
    if iso_with_tz:
        offset_hours = random.choice([-8, -5, 0, 1, 3, 5.5, 8])
        sign = "+" if offset_hours >= 0 else "-"
        oh = abs(int(offset_hours))
        om = 30 if offset_hours % 1 else 0
        return base_dt.strftime(f"%Y-%m-%dT%H:%M:%S{sign}{oh:02d}:{om:02d}")
    return base_dt.strftime("%Y-%m-%d %H:%M:%S")


def gen_transactions(accounts, n_transactions=170000):
    rows = []
    txn_seq = 1
    active_accounts = [a for a in accounts if a["status"] in ("active", "")]

    def next_txn_id():
        nonlocal txn_seq
        tid = f"TXN{txn_seq:08d}"
        txn_seq += 1
        return tid

    # ---- baseline random transactions ----
    for _ in range(n_transactions):
        acct = random.choice(active_accounts)
        currency = acct["currency"]
        base_dt = rand_date(2026, 1, 1, 2026, 6, 30) + timedelta(
            hours=random.randint(0, 23), minutes=random.randint(0, 59), seconds=random.randint(0, 59)
        )
        txn_type = random.choice(TXN_TYPES)
        threshold = REPORTING_THRESHOLD.get(currency, 10000)
        amount = round(random.uniform(10, threshold * 0.6), 2)

        # occasional wrong-case currency code (data quality bug to catch in silver)
        row_currency = currency if random.random() > 0.05 else currency.lower()

        # some txns are cash and have no counterparty account
        counterparty = f"EXT-{random.randint(10000, 99999)}" if random.random() > 0.15 else ""

        channel = random.choice(CHANNELS)
        # ~2% missing channel
        row_channel = channel if random.random() > 0.02 else ""

        # ~12% of timestamps come through as ISO8601+offset (wire/mobile gateway), rest plain
        iso_tz = random.random() < 0.12
        ts = make_ts(base_dt, iso_with_tz=iso_tz)

        row = {
            "txn_id": next_txn_id(),
            "account_id": acct["account_id"],
            "txn_ts": ts,
            "txn_type": txn_type,
            "amount": amount,
            "currency": row_currency,
            "counterparty_acct": counterparty,
            "channel": row_channel,
            "created_at": (base_dt + timedelta(seconds=random.randint(1, 30))).strftime("%Y-%m-%d %H:%M:%S"),
            "source_system": random.choice(SOURCE_SYSTEMS),
        }
        rows.append(row)

        # ~1.5% duplicate transaction (upstream double-fire, same txn_id)
        if random.random() < 0.015:
            rows.append(dict(row))

    # ---- injected structuring pattern: ~2.5% of accounts get 3-5 deposits
    #      just under the reporting threshold, within a 24-72h window ----
    structuring_accounts = random.sample(active_accounts, k=max(1, int(len(active_accounts) * 0.025)))
    for acct in structuring_accounts:
        currency = acct["currency"]
        threshold = REPORTING_THRESHOLD.get(currency, 10000)
        window_start = rand_date(2026, 1, 5, 2026, 6, 20)
        n_deposits = random.randint(3, 5)
        for i in range(n_deposits):
            dt = window_start + timedelta(hours=random.randint(1, 60))
            amount = round(threshold * random.uniform(0.90, 0.98), 2)
            row = {
                "txn_id": next_txn_id(),
                "account_id": acct["account_id"],
                "txn_ts": make_ts(dt),
                "txn_type": "deposit",
                "amount": amount,
                "currency": currency,
                "counterparty_acct": f"EXT-{random.randint(10000, 99999)}",
                "channel": random.choice(["branch", "atm"]),
                "created_at": (dt + timedelta(seconds=random.randint(1, 30))).strftime("%Y-%m-%d %H:%M:%S"),
                "source_system": random.choice(SOURCE_SYSTEMS),
            }
            rows.append(row)

    # ---- injected rapid in-out pattern: ~1.5% of accounts get a large
    #      deposit followed by a near-equal withdrawal within hours ----
    rapid_accounts = random.sample(active_accounts, k=max(1, int(len(active_accounts) * 0.015)))
    for acct in rapid_accounts:
        currency = acct["currency"]
        threshold = REPORTING_THRESHOLD.get(currency, 10000)
        dt_in = rand_date(2026, 1, 5, 2026, 6, 20) + timedelta(hours=random.randint(0, 23))
        amount = round(threshold * random.uniform(1.2, 3.0), 2)
        dt_out = dt_in + timedelta(hours=random.randint(2, 30))

        deposit = {
            "txn_id": next_txn_id(),
            "account_id": acct["account_id"],
            "txn_ts": make_ts(dt_in),
            "txn_type": "wire_in",
            "amount": amount,
            "currency": currency,
            "counterparty_acct": f"EXT-{random.randint(10000, 99999)}",
            "channel": "wire",
            "created_at": (dt_in + timedelta(seconds=20)).strftime("%Y-%m-%d %H:%M:%S"),
            "source_system": "WIRE_SWIFT_GW",
        }
        withdrawal = {
            "txn_id": next_txn_id(),
            "account_id": acct["account_id"],
            "txn_ts": make_ts(dt_out),
            "txn_type": "wire_out",
            "amount": round(amount * random.uniform(0.92, 0.99), 2),
            "currency": currency,
            "counterparty_acct": f"EXT-{random.randint(10000, 99999)}",
            "channel": "wire",
            "created_at": (dt_out + timedelta(seconds=20)).strftime("%Y-%m-%d %H:%M:%S"),
            "source_system": "WIRE_SWIFT_GW",
        }
        rows.append(deposit)
        rows.append(withdrawal)

    random.shuffle(rows)
    return rows


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def write_csv(name, rows):
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows):>7} rows -> {path}")


if __name__ == "__main__":
    customers = gen_customers()
    branches = gen_branches()
    accounts = gen_accounts(customers, branches)
    transactions = gen_transactions(accounts)

    write_csv("customers.csv", customers)
    write_csv("branches.csv", branches)
    write_csv("accounts.csv", accounts)
    write_csv("transactions.csv", transactions)

    print("\nDone. Structuring pattern and rapid in-out pattern were injected")
    print("into a subset of accounts for downstream AML rule-building —")
    print("nothing labels them, that's the detection logic you build in PySpark.")
