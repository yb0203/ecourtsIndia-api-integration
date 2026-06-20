import os
from dataclasses import dataclass
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://webapi.ecourtsindia.com/api/partner"


@dataclass
class CaseDetail:
    cnr: str
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
    orders: list
    hearings: list


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


def build_cnr(court_code: str, case_number: str, year: int) -> str:
    """
    Construct a CNR from court code + case number + year.
    Format: {6-char court code}{case number zero-padded to 6 digits}{4-digit year}
    Example: DLHC01 + 000422 + 2025 → DLHC010004222025
    """
    # Ensure court_code is 6 chars (some codes are shorter like DLHC01)
    code = court_code[:6].ljust(6)
    # Strip non-numeric chars from case number for padding
    num = "".join(filter(str.isdigit, case_number)).zfill(6)
    return f"{code}{num}{year}"


class EcourtsClient:
    def __init__(self) -> None:
        self.api_key = os.environ["ECOURTS_API_KEY"]
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def get_case_by_cnr(self, cnr: str) -> Optional[CaseDetail]:
        """Fetch full case data by CNR number."""
        resp = requests.get(
            f"{BASE_URL}/case/{cnr}",
            headers=self.headers,
            timeout=30,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            return None
        raw = data.get("data", {}).get("courtCaseData", {})
        if not raw:
            return None
        return self._parse_case_detail(cnr, raw)

    def search_case(
        self, court_code: str, case_type: str, case_number: str, year: int
    ) -> Optional[CaseDetail]:
        """
        Search by constructing the CNR from the 4 fields.
        The eCourts search API does not filter by params reliably,
        so we derive the CNR directly.
        """
        cnr = build_cnr(court_code, case_number, year)
        return self.get_case_by_cnr(cnr)

    def _parse_case_detail(self, cnr: str, raw: dict) -> CaseDetail:
        judges = raw.get("judges", [])
        petitioners = raw.get("petitioners", [])
        respondents = raw.get("respondents", [])

        hearings = [
            HearingRecord(
                hearing_date=h.get("hearingDate", h.get("businessOnDate", "")),
                purpose=h.get("purposeOfListing", ""),
                outcome=h.get("businessOnDate", ""),
            )
            for h in raw.get("historyOfCaseHearings", [])
            if h.get("hearingDate") or h.get("businessOnDate")
        ]

        orders = [
            Order(
                order_date=o.get("orderDate", ""),
                order_number=str(i + 1),
                pdf_url=o.get("orderUrl", ""),
            )
            for i, o in enumerate(raw.get("judgmentOrders", []))
        ]

        filing_date = raw.get("filingDate")
        cnr_year = int(cnr[-4:]) if len(cnr) >= 4 and cnr[-4:].isdigit() else None
        year = cnr_year or (int(filing_date[:4]) if filing_date else 0)

        return CaseDetail(
            cnr=cnr,
            court_code=raw.get("cnrCourtCode", raw.get("courtComplexCode", "")),
            case_type=raw.get("caseType", raw.get("caseTypeRaw", "")),
            case_number=raw.get("cnrCaseNumber", raw.get("registrationNumber", "")),
            year=year,
            court_name=raw.get("courtName", ""),
            state=raw.get("state", raw.get("stateCode", "")),
            petitioner=", ".join(petitioners) if petitioners else "",
            respondent=", ".join(respondents) if respondents else "",
            judge=", ".join(judges) if judges else "",
            filing_date=filing_date,
            next_hearing_date=raw.get("nextHearingDate"),
            court_status=raw.get("caseStatus", ""),
            orders=orders,
            hearings=hearings,
        )

    def refresh_case_by_cnr(self, cnr: str) -> Optional[CaseDetail]:
        return self.get_case_by_cnr(cnr)

    def get_order_summary(self, cnr: str, order_number: str) -> str:
        resp = requests.get(
            f"{BASE_URL}/order-summary",
            params={"cnr": cnr, "orderNumber": order_number},
            headers=self.headers,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("summary", "")

    def get_enums(self) -> dict:
        resp = requests.get(
            f"{BASE_URL}/enums", headers=self.headers, timeout=30
        )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("enums", {})
