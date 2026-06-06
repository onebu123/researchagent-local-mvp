from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.schemas import AnalysisCompareRequest, EvidenceClaim, FigureProvenanceRecord, OutputContent, OutputItem
from app.services.project_service import OutputNotFoundError, ProjectNotFoundError, project_service
from app.services.storage_service import storage_service
from app.tools.analysis_compare import (
    generate_analysis_comparison,
    list_analysis_comparisons,
    load_analysis_comparison,
)
from app.tools.analysis_timeline import generate_analysis_timeline

router = APIRouter()


def _read_project_json_any(project_id: str, relative_path: str) -> Any:
    try:
        project_service.require_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    project_dir = storage_service.project_dir(project_id)
    path = storage_service.ensure_inside_project(project_id, project_dir / relative_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File does not exist: {relative_path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {relative_path}") from exc


def _read_project_json_list(project_id: str, relative_path: str) -> list[dict[str, Any]]:
    payload = _read_project_json_any(project_id, relative_path)
    if not isinstance(payload, list):
        raise HTTPException(status_code=400, detail=f"JSON file must be a list: {relative_path}")
    return payload


def _read_project_json_object(project_id: str, relative_path: str) -> dict[str, Any]:
    payload = _read_project_json_any(project_id, relative_path)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail=f"JSON file must be an object: {relative_path}")
    return payload


@router.get("/projects/{project_id}/outputs", response_model=list[OutputItem])
def list_outputs(project_id: str) -> list[OutputItem]:
    try:
        project_service.require_project(project_id)
        return project_service.list_outputs(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/projects/{project_id}/outputs/{output_id}", response_model=OutputContent)
def get_output(project_id: str, output_id: str) -> OutputContent:
    try:
        return project_service.read_output(project_id, output_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OutputNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/projects/{project_id}/outputs/{output_id}/file")
def get_output_file(project_id: str, output_id: str) -> FileResponse:
    try:
        path, record = project_service.output_file_path(project_id, output_id)
        return FileResponse(path, media_type=record.mime_type, filename=path.name)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OutputNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/projects/{project_id}/evidence", response_model=list[EvidenceClaim])
def get_project_evidence(project_id: str) -> list[dict[str, Any]]:
    return _read_project_json_list(project_id, "provenance/evidence.json")


@router.get("/projects/{project_id}/figures/provenance", response_model=list[FigureProvenanceRecord])
def get_project_figure_provenance(project_id: str) -> list[dict[str, Any]]:
    return _read_project_json_list(project_id, "figures/figure_provenance.json")


@router.get("/projects/{project_id}/claim-alignment")
def get_project_claim_alignment(project_id: str) -> dict[str, Any]:
    return _read_project_json_object(project_id, "provenance/claim_alignment.json")


@router.get("/projects/{project_id}/analysis/provenance")
def get_project_analysis_provenance(project_id: str) -> dict[str, Any]:
    return _read_project_json_object(project_id, "analysis/analysis_provenance.json")


@router.post("/projects/{project_id}/analysis/compare")
def compare_project_analysis(project_id: str, payload: AnalysisCompareRequest) -> dict[str, Any]:
    try:
        project_service.require_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    project_dir = storage_service.project_dir(project_id)
    try:
        storage_service.ensure_inside_project(project_id, project_dir / payload.base_provenance)
        storage_service.ensure_inside_project(project_id, project_dir / payload.target_provenance)
        return generate_analysis_comparison(
            project_dir,
            project_id,
            payload.base_provenance,
            payload.target_provenance,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/projects/{project_id}/analysis/comparisons")
def get_project_analysis_comparisons(project_id: str) -> list[dict[str, Any]]:
    try:
        project_service.require_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return list_analysis_comparisons(storage_service.project_dir(project_id))


@router.get("/projects/{project_id}/analysis/comparisons/{comparison_id}")
def get_project_analysis_comparison(project_id: str, comparison_id: str) -> dict[str, Any]:
    try:
        project_service.require_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        return load_analysis_comparison(storage_service.project_dir(project_id), comparison_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/projects/{project_id}/analysis/timeline")
def get_project_analysis_timeline(project_id: str) -> dict[str, Any]:
    try:
        project_service.require_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        return generate_analysis_timeline(storage_service.project_dir(project_id), project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/projects/{project_id}/review/sentence-issues")
def get_project_sentence_issues(project_id: str) -> list[dict[str, Any]]:
    review = _read_project_json_object(project_id, "reviews/review_report.json")
    sentence_issues = review.get("sentence_issues", [])
    if not isinstance(sentence_issues, list):
        raise HTTPException(status_code=400, detail="review_report.json sentence_issues must be a list")
    return sentence_issues
