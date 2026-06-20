import os
from dataclasses import dataclass
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.ecourtsindia.com/api/partner"


@dataclass
class CaseSearchResult:
    court_code: str
    case_type: str
    case_number: str
    year: int
    court_name: str
    state: str
    petitioner: str
    respondent: str
    judge: str
    filing_date: Optional[str]
    next_hearing_date: Optional[str]
    court_status: str


@dataclass
class Order:
    order_date: str
    order_number: str
    pdf_url: str
    ai_summary: Optional[str] = None


@dataclass
class HearingRecord:
    hearing_date: str
    purpose: str
    outcome: str


class EcourtsClient:
    def __init__(self) -> None:
        self.api_key = os.environ["ECOURTS_API_KEY"]
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def search_case(
        self, court_code: str, case_type: str, case_number: str, year: int
    ) -> Optional[CaseSearchResult]:
        resp = requests.get(
            f"{BASE_URL}/search",
            params={
                "court_code": court_code,
                "case_type": case_type,
                "case_number": case_number,
                "year": year,
            },
            headers=self.headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("results"):
            return None
        r = data["results"][0]
        return CaseSearchResult(
            court_code=court_code,
            case_type=case_type,
            case_number=case_number,
            year=year,
            court_name=r.get("court_name", ""),
            state=r.get("state", ""),
            petitioner=r.get("petitioner", ""),
            respondent=r.get("respondent", ""),
            judge=r.get("judge", ""),
            filing_date=r.get("filing_date"),
            next_hearing_date=r.get("next_hearing_date"),
            court_status=r.get("status", ""),
        )

    def get_case_detail(
        self, court_code: str, case_type: str, case_number: str, year: int
    ) -> dict:
        resp = requests.get(
            f"{BASE_URL}/case",
            params={
                "court_code": court_code,
                "case_type": case_type,
                "case_number": case_number,
                "year": year,
            },
            headers=self.headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def refresh_case(
        self, court_code: str, case_type: str, case_number: str, year: int
    ) -> dict:
        resp = requests.post(
            f"{BASE_URL}/refresh",
            json={
                "court_code": court_code,
                "case_type": case_type,
                "case_number": case_number,
                "year": year,
            },
            headers=self.headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def get_orders(
        self, court_code: str, case_type: str, case_number: str, year: int
    ) -> list[Order]:
        resp = requests.get(
            f"{BASE_URL}/orders",
            params={
                "court_code": court_code,
                "case_type": case_type,
                "case_number": case_number,
                "year": year,
            },
            headers=self.headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            Order(
                order_date=o.get("date", ""),
                order_number=o.get("number", ""),
                pdf_url=o.get("pdf_url", ""),
            )
            for o in data.get("orders", [])
        ]

    def get_order_summary(self, order_number: str, court_code: str) -> str:
        resp = requests.get(
            f"{BASE_URL}/order-summary",
            params={"order_number": order_number, "court_code": court_code},
            headers=self.headers,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("summary", "")

    def get_hearing_history(
        self, court_code: str, case_type: str, case_number: str, year: int
    ) -> list[HearingRecord]:
        detail = self.get_case_detail(court_code, case_type, case_number, year)
        return [
            HearingRecord(
                hearing_date=h.get("date", ""),
                purpose=h.get("purpose", ""),
                outcome=h.get("outcome", ""),
            )
            for h in detail.get("hearing_history", [])
        ]

    def get_court_structure(self) -> dict:
        resp = requests.get(
            f"{BASE_URL}/court-structure", headers=self.headers, timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    def get_enums(self) -> dict:
        resp = requests.get(
            f"{BASE_URL}/enums", headers=self.headers, timeout=30
        )
        resp.raise_for_status()
        return resp.json()
