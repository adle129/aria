from app.services.rfq_text_extractor import extract_rfq_from_text

SAMPLE_RFQ_TEXT = """
RFQ — Mock Chassis Development Project

Customer: Mock Auto GmbH
Platform: MEB Electric Vehicle Platform
Project Duration: 20 months

Scope of Work — Functions:
1. Project Management (PM)
2. Chassis — Front Suspension Design & Development
3. Chassis — Rear Suspension Design & Development

Deliverables:
- M1: Concept 3D data release
- M2: Detailed 3D CAD data (Front/Rear suspension)

Milestones:
P1: 2026-03-01 | P2: 2026-07-01 | P3: 2026-11-01
P4: 2027-03-01 | P5: 2027-07-01 | SOP: 2027-10-01

Technical Requirements:
- Platform sharing with existing MEB derivatives
- Suspension: MacPherson front, multi-link rear
"""


def test_extract_customer_and_platform():
    result = extract_rfq_from_text(SAMPLE_RFQ_TEXT)
    assert result["customer"] == "Mock Auto GmbH"
    assert result["platform_type"] == "MEB"
    assert result["timeline_months"] == 20


def test_extract_milestones_and_modules():
    result = extract_rfq_from_text(SAMPLE_RFQ_TEXT)
    assert "P1" in result["milestones"]
    assert result["milestones"]["P1"] == "2026-03-01"
    functions = result["functions_in_scope"]
    assert "PM" in functions
    assert "Chassis" in functions
    assert len(result["modules"]) >= 2


def test_new_project_profile_populated():
    result = extract_rfq_from_text(SAMPLE_RFQ_TEXT)
    profile = result["new_project_profile"]
    assert profile["平台类型"] == "MEB"
    assert "项" in profile["交付物数量"]
