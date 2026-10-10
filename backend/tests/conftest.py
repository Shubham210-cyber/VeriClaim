import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="cp_tests_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_tmp / 'test.db').as_posix()}"
os.environ["STORAGE_DIR"] = str(_tmp / "storage")
os.environ["AI_PROVIDER"] = "mock"
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.models import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.policies.catalog import seed_policies  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        seed_policies(s)
        yield s


@pytest.fixture()
def client(db):
    return TestClient(app)


INVOICE = (b"Product Model: Northstar N14\nSerial Number: NS-N14-000123\n"
           b"Purchase Date: 2026-06-01\nTotal Amount: INR 65000.00\n")

WAR_LAPTOP = dict(product_type="LAPTOP", product_brand="Northstar", product_model="N14", device_identifier="NS-N14-000123",
                  claim_type="WARRANTY", policy_id="SYN-WAR-LAPTOP-01", event_type="HARDWARE_FAILURE",
                  incident_date="2026-06-20", damage_or_failure_description="Stopped powering on")


def make_claim(client, **over):
    r = client.post("/api/v1/claims", json={**WAR_LAPTOP, **over})
    assert r.status_code == 201, r.text
    return r.json()


def upload(client, claim_id, data=INVOICE, name="inv.txt", etype="PURCHASE_INVOICE", mime="text/plain"):
    return client.post(f"/api/v1/claims/{claim_id}/evidence", files={"file": (name, data, mime)}, data={"evidence_type": etype})
