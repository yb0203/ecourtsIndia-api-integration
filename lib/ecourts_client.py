import os
from dataclasses import dataclass
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://webapi.ecourtsindia.com/api/partner"


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
    cnr: Optional[str] = None


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
        results = data.get("data", {}).get("results", [])
        if not results:
            return None
        r = results[0]
        return CaseSearchResult(
            court_code=r.get("courtCode", court_code),
            case_type=r.get("caseType", case_type),
            case_number=case_number,
            year=year,
            court_name=r.get("courtName", ""),
            state=r.get("stateCode", ""),
            petitioner=", ".join(r.get("petitioners", [])),
            respondent=", ".join(r.get("respondents", [])),
            judge=", ".join(r.get("judges", [])),
            filing_date=r.get("filingDate"),
            next_hearing_date=r.get("nextHearingDate"),
            court_status=r.get("caseStatus", ""),
            cnr=r.get("cnr"),
        )

    def get_case_detail(self, cnr: str) -> dict:
        resp = requests.get(
            f"{BASE_URL}/case",
            params={"cnr": cnr},
            headers=self.headers,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("data", {})

    def refresh_case(
        self, court_code: str, case_type: str, case_number: str, year: int
    ) -> dict:
        resp = requests.post(
            f"{BASE_URL}/refresh",
            json={
                "courtCode": court_code,
                "caseType": case_type,
                "caseNumber": case_number,
                "year": year,
            },
            headers=self.headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        # Normalise to snake_case for db layer
        return {
            "next_hearing_date": data.get("nextHearingDate"),
            "status": data.get("caseStatus"),
        }

    def get_orders(self, cnr: str) -> list[Order]:
        resp = requests.get(
            f"{BASE_URL}/orders",
            params={"cnr": cnr},
            headers=self.headers,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return [
            Order(
                order_date=o.get("date", o.get("orderDate", "")),
                order_number=o.get("orderNumber", o.get("number", "")),
                pdf_url=o.get("pdfUrl", o.get("pdf_url", "")),
            )
            for o in data.get("orders", [])
        ]

    def get_order_summary(self, cnr: str, order_number: str) -> str:
        resp = requests.get(
            f"{BASE_URL}/order-summary",
            params={"cnr": cnr, "orderNumber": order_number},
            headers=self.headers,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("summary", "")

    def get_hearing_history(self, cnr: str) -> list[HearingRecord]:
        detail = self.get_case_detail(cnr)
        return [
            HearingRecord(
                hearing_date=h.get("date", h.get("hearingDate", "")),
                purpose=h.get("purpose", ""),
                outcome=h.get("outcome", ""),
            )
            for h in detail.get("hearingHistory", detail.get("hearing_history", []))
        ]

    def get_enums(self) -> dict:
        resp = requests.get(
            f"{BASE_URL}/enums", headers=self.headers, timeout=30
        )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("enums", {})
