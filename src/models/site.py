from pydantic import BaseModel


class IllegalSite(BaseModel):
  domain: str
  notes: str
  path: str
  reason: str


class ReportedIllegalSite(BaseModel):
  domain: str
  notes: str
  path: str
  reason: str
  token: str
