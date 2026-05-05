from datetime import date
from pydantic import BaseModel, Field


class ClaimData(BaseModel):
    patientName: str
    dob: date
    policyNumber: str
    diagnosisCode: str
    diagnosisDesc: str
    cptCode: str
    provider: str
    totalBilled: float = Field(ge=0)
    approvedAmount: float = Field(ge=0)
    patientResponsibility: float = Field(ge=0)
    dateOfService: date


class RiskContribution(BaseModel):
    rule: str
    delta: float
    reason: str


class RiskModelInfo(BaseModel):
    engine: str = "rules"
    modelName: str = "deterministic-rules-v1"
    baseScore: float = Field(ge=0, le=1)
    maxIssuePenalty: float = Field(ge=0, le=1)
    issuePenaltyPerItem: float = Field(ge=0, le=1)
    thresholds: dict[str, float]
    contributions: list[RiskContribution]


class ProcessResponse(BaseModel):
    claimData: ClaimData
    riskScore: float = Field(ge=0, le=1)
    riskLabel: str
    recommendation: str
    riskReasons: list[str] = Field(default_factory=list)
    extractionIssues: list[str] = Field(default_factory=list)
    extractionTextPreview: str = ""
    riskModel: RiskModelInfo
    email: str
    whatsapp: str
