"""Tests for the /process endpoint to prevent regressions."""

import io
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_pdf_bytes():
    """Create minimal valid PDF bytes for testing."""
    # Minimal PDF structure that pypdf can parse.
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< >>
stream
BT
/F1 12 Tf
100 700 Td
(Patient Name: John Doe) Tj
(Policy Number: POL123456) Tj
(DOB: 03/14/1985) Tj
(Date of Service: 04/10/2026) Tj
(Diagnosis: Pneumonia) Tj
(ICD-10: J18.9) Tj
(CPT Code: 99213) Tj
(Provider: SUMMIT HEALTH CLINIC) Tj
(Total Billed: 4250.00) Tj
(Approved: 3000.00) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000204 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
557
%%EOF
"""
    return pdf_content


class TestProcessEndpoint:
    """Test suite for the /process endpoint."""

    def test_health_endpoint(self, client):
        """Test that health check endpoint works."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_process_missing_file(self, client):
        """Test that /process rejects request without file."""
        response = client.post("/process")
        assert response.status_code == 422  # Pydantic validation error

    def test_process_unsupported_file_type(self, client):
        """Test that /process rejects non-PDF/image files."""
        response = client.post(
            "/process",
            files={"file": ("test.txt", b"Not a PDF", "text/plain")},
        )
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_process_empty_pdf(self, client):
        """Test that /process handles PDFs with no extractable text gracefully."""
        response = client.post(
            "/process",
            files={
                "file": (
                    "empty.pdf",
                    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/MediaBox[0 0 612 792]/Contents 5 0 R>>endobj\n4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n5 0 obj<</Length 0>>stream\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f\n0000000009 00000 n\n0000000074 00000 n\n0000000133 00000 n\n0000000229 00000 n\n0000000297 00000 n\ntrailer<</Size 6/Root 1 0 R>>\nstartxref\n355\n%%EOF",
                    "application/pdf",
                )
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["claimData"]["patientName"] == "Unknown Patient"
        assert data["claimData"]["policyNumber"] == "UNKNOWN-POLICY"
        assert data["riskLabel"] in ["LOW", "MEDIUM", "HIGH"]

    def test_process_valid_pdf_with_claim_data(self, client, sample_pdf_bytes):
        """Test that /process returns valid response structure for claim data."""
        response = client.post(
            "/process",
            files={"file": ("claim.pdf", sample_pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200

        data = response.json()

        # Validate response structure matches ProcessResponse model
        assert "claimData" in data
        assert "riskScore" in data
        assert "riskLabel" in data
        assert "recommendation" in data
        assert "email" in data
        assert "whatsapp" in data

        # Validate claimData fields
        claim = data["claimData"]
        assert "patientName" in claim
        assert "policyNumber" in claim
        assert "diagnosisCode" in claim
        assert "cptCode" in claim
        assert "provider" in claim
        assert "totalBilled" in claim
        assert "approvedAmount" in claim
        assert "patientResponsibility" in claim

        # Validate risk score range
        assert 0 <= data["riskScore"] <= 1
        assert data["riskLabel"] in ["LOW", "MEDIUM", "HIGH"]
        assert data["recommendation"] in ["APPROVE", "REVIEW", "REJECT"]

    def test_process_pdf_with_missing_fields(self, client):
        """Test that /process handles PDFs with missing or minimal data."""
        minimal_pdf = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/MediaBox[0 0 612 792]/Contents 5 0 R>>endobj
4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
5 0 obj<</Length 50>>stream
BT
/F1 12 Tf
100 700 Td
(Some minimal text) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000074 00000 n
0000000133 00000 n
0000000229 00000 n
0000000297 00000 n
trailer<</Size 6/Root 1 0 R>>
startxref
396
%%EOF"""

        response = client.post(
            "/process",
            files={"file": ("minimal.pdf", minimal_pdf, "application/pdf")},
        )
        assert response.status_code == 200

        data = response.json()
        # Should have fallback values for missing fields
        assert data["claimData"]["policyNumber"] == "UNKNOWN-POLICY"
        assert data["claimData"]["provider"] == "Unknown Provider"
        # Risk score is in the root response, not in claimData
        assert "riskScore" in data
        assert data["riskScore"] >= 0

    def test_process_database_persistence_not_required(self, client, sample_pdf_bytes):
        """Test that /process succeeds even if Supabase persistence fails (gracefully skipped)."""
        response = client.post(
            "/process",
            files={"file": ("claim.pdf", sample_pdf_bytes, "application/pdf")},
        )
        # Should succeed regardless of DB persistence
        assert response.status_code == 200


class TestPipelineLogic:
    """Test suite for claim pipeline logic via API."""

    def test_risk_score_range(self, client, sample_pdf_bytes):
        """Test that risk score is always between 0 and 1."""
        response = client.post(
            "/process",
            files={"file": ("claim.pdf", sample_pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200

        data = response.json()
        assert 0 <= data["riskScore"] <= 1

    def test_risk_label_validity(self, client, sample_pdf_bytes):
        """Test that risk label is one of the valid values."""
        response = client.post(
            "/process",
            files={"file": ("claim.pdf", sample_pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["riskLabel"] in ["LOW", "MEDIUM", "HIGH"]

    def test_recommendation_validity(self, client, sample_pdf_bytes):
        """Test that recommendation is one of the valid values."""
        response = client.post(
            "/process",
            files={"file": ("claim.pdf", sample_pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["recommendation"] in ["APPROVE", "REVIEW", "REJECT"]

    def test_email_draft_not_empty(self, client, sample_pdf_bytes):
        """Test that email draft is generated and not empty."""
        response = client.post(
            "/process",
            files={"file": ("claim.pdf", sample_pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data["email"], str)
        assert len(data["email"]) > 20
        assert "Subject:" in data["email"]

    def test_whatsapp_draft_not_empty(self, client, sample_pdf_bytes):
        """Test that WhatsApp draft is generated and not empty."""
        response = client.post(
            "/process",
            files={"file": ("claim.pdf", sample_pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data["whatsapp"], str)
        assert len(data["whatsapp"]) > 10
