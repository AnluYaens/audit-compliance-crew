import ast
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from schemas.audit_response import AuditResponseRequest, AuditResponseResult
from schemas.contracts import (
    ClientCRMReadRequest,
    IngestionToolOutput,
    PartnerIndependenceRequest,
    RiskEvaluationInput,
    RiskScoringOutput,
    ScreeningResponse,
    WatchlistScanRequest,
)
from schemas.evidence import AuditPlanningEvidenceBundle
from schemas.financial_statements import (
    FinancialLineItemExtraction,
    FinancialStatementNormalizationRequest,
    FinancialStatementNormalizationResult,
    FinancialStatementPeriod,
    SourceReference,
    StatementType,
)
from schemas.materiality import MaterialityRequest, MaterialityResult
from schemas.risk_assessment import (
    AuditAssertion,
    FinancialStatementArea,
    RiskAssessmentRequest,
    RiskAssessmentResult,
    RiskIndicator,
)
from schemas.source_registry import (
    SourceRecord,
    SourceRegistry,
    SourceRegistryScoringResult,
    SourceType,
)
from services.audit_planning_pipeline_service import run_audit_planning_pipeline
from services.audit_response_service import design_audit_response
from services.financial_normalization_service import normalize_financial_statement
from services.ingestion_service import read_client_crm_data_service
from services.materiality_service import calculate_materiality
from services.risk_assessment_service import assess_audit_risks
from services.risk_scoring_service import calculate_weighted_risk_score_service
from services.screening_service import (
    check_partner_independence_service,
    scan_sanctions_watchlist_service,
)
from services.source_scoring_service import score_source_registry


def round_trip(model, model_type):
    payload = json.loads(model.model_dump_json(exclude_computed_fields=True))
    json.dumps(payload)
    return model_type.model_validate(payload)


def materiality_request() -> MaterialityRequest:
    return MaterialityRequest(
        target_company="GreenLeaf Organics",
        benchmark_type="profit_before_tax",
        benchmark_amount=1_000_000,
        overall_materiality_percentage=0.05,
        performance_materiality_percentage=0.75,
        clearly_trivial_percentage=0.05,
        rationale="Profit before tax is stable and appropriate for this prototype.",
    )


def risk_assessment_request() -> RiskAssessmentRequest:
    return RiskAssessmentRequest(
        target_company="GreenLeaf Organics",
        indicators=[
            RiskIndicator(
                area=FinancialStatementArea.CASH,
                assertion=AuditAssertion.EXISTENCE,
                description="Cash balance is simple and reconciled.",
                likelihood=1,
                magnitude=2,
            )
        ],
    )


def source_record() -> SourceRecord:
    return SourceRecord(
        url="https://example.com/regulatory-filing",
        source_type=SourceType.REGULATORY,
        publisher="Example Regulator",
        retrieval_date=datetime(2026, 5, 20, tzinfo=timezone.utc),
        confidence=0.95,
        freshness_days=90,
        relevance=0.9,
        notes="Regulatory filing metadata captured for deterministic scoring.",
    )


def financial_statement_request() -> FinancialStatementNormalizationRequest:
    reference = SourceReference(
        document_id="FS-2025-AUDITED",
        page_number=4,
        section="Balance sheet",
    )
    return FinancialStatementNormalizationRequest(
        statement_type=StatementType.BALANCE_SHEET,
        period=FinancialStatementPeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            fiscal_year=2025,
        ),
        currency="EUR",
        source_reference=reference,
        confidence=0.95,
        line_items=[
            FinancialLineItemExtraction(
                source_label="Cash and bank balances",
                amount=Decimal("100000"),
                source_reference=reference,
                confidence=0.95,
            ),
            FinancialLineItemExtraction(
                source_label="Total assets",
                amount=Decimal("1000000"),
                source_reference=reference,
                confidence=0.95,
            ),
            FinancialLineItemExtraction(
                source_label="Total liabilities",
                amount=Decimal("400000"),
                source_reference=reference,
                confidence=0.95,
            ),
            FinancialLineItemExtraction(
                source_label="Shareholders' equity",
                amount=Decimal("600000"),
                source_reference=reference,
                confidence=0.95,
            ),
        ],
    )


def test_activity_request_payloads_are_json_serializable():
    assessment_result = assess_audit_risks(risk_assessment_request())

    request_boundaries = [
        (ClientCRMReadRequest(company_name="GreenLeaf Organics"), ClientCRMReadRequest),
        (
            PartnerIndependenceRequest(company_name="GreenLeaf Organics"),
            PartnerIndependenceRequest,
        ),
        (
            WatchlistScanRequest(
                ceo_name="Elena Green",
                company_name="GreenLeaf Organics",
                global_offices=["Germany"],
            ),
            WatchlistScanRequest,
        ),
        (
            RiskEvaluationInput(
                industry_level="Low",
                geography_level="Low",
                financial_level="Low",
            ),
            RiskEvaluationInput,
        ),
        (
            SourceRegistry(
                run_id="LOCAL-greenleaf-organics",
                target_company="GreenLeaf Organics",
                records=[source_record()],
            ),
            SourceRegistry,
        ),
        (financial_statement_request(), FinancialStatementNormalizationRequest),
        (materiality_request(), MaterialityRequest),
        (risk_assessment_request(), RiskAssessmentRequest),
        (
            AuditResponseRequest(
                target_company="GreenLeaf Organics",
                assessed_risks=assessment_result.assessed_risks,
            ),
            AuditResponseRequest,
        ),
    ]

    for payload, model_type in request_boundaries:
        parsed = round_trip(payload, model_type)
        assert parsed.model_dump(mode="json") == payload.model_dump(mode="json")


def test_activity_response_payloads_are_json_serializable_and_schema_valid():
    ingestion = IngestionToolOutput.model_validate_json(
        read_client_crm_data_service("GreenLeaf Organics")
    )
    independence = ScreeningResponse.model_validate_json(
        check_partner_independence_service("GreenLeaf Organics")
    )
    sanctions = ScreeningResponse.model_validate_json(
        scan_sanctions_watchlist_service(
            ceo_name="Elena Green",
            company_name="GreenLeaf Organics",
            global_offices=["Germany"],
        )
    )
    risk_score = RiskScoringOutput.model_validate_json(
        calculate_weighted_risk_score_service(
            industry_level="Low",
            geography_level="Low",
            financial_level="Low",
        )
    )
    source_scoring = score_source_registry(
        SourceRegistry(
            run_id="LOCAL-greenleaf-organics",
            target_company="GreenLeaf Organics",
            records=[source_record()],
        ),
        scoring_datetime=datetime(2026, 6, 12, tzinfo=timezone.utc),
    )
    financial_normalization = normalize_financial_statement(financial_statement_request())
    materiality = calculate_materiality(materiality_request())
    risk_assessment = assess_audit_risks(risk_assessment_request())
    audit_response = design_audit_response(
        AuditResponseRequest(
            target_company="GreenLeaf Organics",
            assessed_risks=risk_assessment.assessed_risks,
        )
    )

    response_boundaries = [
        (ingestion, IngestionToolOutput),
        (independence, ScreeningResponse),
        (sanctions, ScreeningResponse),
        (risk_score, RiskScoringOutput),
        (source_scoring, SourceRegistryScoringResult),
        (financial_normalization, FinancialStatementNormalizationResult),
        (materiality, MaterialityResult),
        (risk_assessment, RiskAssessmentResult),
        (audit_response, AuditResponseResult),
    ]

    for payload, model_type in response_boundaries:
        parsed = round_trip(payload, model_type)
        assert parsed.model_dump(mode="json") == payload.model_dump(mode="json")


def test_full_pipeline_boundary_input_and_output_stay_schema_valid():
    future_orchestrator_payload = {
        "company_name": "GreenLeaf Organics",
        "materiality_request": materiality_request().model_dump(mode="json"),
        "risk_assessment_request": risk_assessment_request().model_dump(mode="json"),
        "source_records": [source_record().model_dump(mode="json")],
        "require_source_support": True,
    }
    json_payload = json.loads(json.dumps(future_orchestrator_payload))

    bundle = run_audit_planning_pipeline(
        company_name=json_payload["company_name"],
        materiality_request=MaterialityRequest.model_validate(
            json_payload["materiality_request"]
        ),
        risk_assessment_request=RiskAssessmentRequest.model_validate(
            json_payload["risk_assessment_request"]
        ),
        source_records=[
            SourceRecord.model_validate(record)
            for record in json_payload["source_records"]
        ],
        require_source_support=json_payload["require_source_support"],
    )

    parsed_bundle = round_trip(bundle, AuditPlanningEvidenceBundle)

    assert parsed_bundle.target_company == "GreenLeaf Organics"
    assert parsed_bundle.source_registry_scoring_result is not None
    assert parsed_bundle.model_dump(mode="json") == bundle.model_dump(mode="json")


def test_function_boundary_contract_tests_do_not_import_azure_sdk():
    source = Path(__file__).read_text(encoding="utf-8")
    imported_roots: set[str] = set()

    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_roots.add(node.module.split(".")[0])

    assert "azure" not in imported_roots
