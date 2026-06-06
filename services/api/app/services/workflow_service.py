from __future__ import annotations

from app.schemas import WorkflowRunResponse
from app.services.project_service import project_service
from app.services.storage_service import storage_service
from app.tools.audit_log import append_audit_event
from app.tools.run_history import append_run_history, utc_now
from app.workflows.research_workflow import ResearchWorkflow
from app.workflows.state import ResearchState


class UnknownWorkflowStepError(ValueError):
    pass


class WorkflowService:
    def __init__(self) -> None:
        self.workflow = ResearchWorkflow()

    def run_workflow(self, project_id: str) -> WorkflowRunResponse:
        state = self._build_state(project_id)
        project_dir = storage_service.project_dir(project_id)
        start_time = utc_now()
        project_service.update_workflow_state(project_id, "running", "workflow_started")
        try:
            state = self.workflow.run(
                state,
                before_step=lambda step: project_service.update_workflow_state(
                    project_id, "running", step
                ),
            )
            status = "completed"
            current_step = "completed"
        except Exception as exc:
            state.errors.append(str(exc))
            status = "failed"
            current_step = state.current_step

        self._persist_outputs(project_id, state)
        project_service.update_workflow_state(project_id, status, current_step)
        outputs = sorted({output.relative_path for output in state.outputs})
        end_time = utc_now()
        append_run_history(
            project_dir,
            "workflow",
            None,
            status,
            start_time,
            end_time,
            outputs,
            state.errors,
            [],
        )
        append_audit_event(
            project_dir,
            project_id,
            "run_workflow",
            f"Workflow run {status}.",
            {
                "status": status,
                "current_step": current_step,
                "outputs": outputs,
                "error_count": len(state.errors),
            },
            source="api",
        )
        return WorkflowRunResponse(
            project_id=project_id,
            workflow_status=status,
            current_step=current_step,
            outputs=project_service.list_outputs(project_id),
            errors=state.errors,
        )

    def run_step(self, project_id: str, step: str) -> WorkflowRunResponse:
        if step not in self.workflow.step_names():
            raise UnknownWorkflowStepError(f"未知 Agent 步骤：{step}")

        state = self._build_state(project_id)
        project_dir = storage_service.project_dir(project_id)
        start_time = utc_now()
        project_service.update_workflow_state(project_id, "running", step)
        try:
            state = self.workflow.run_step(state, step)
            status = "completed"
            current_step = step
        except Exception as exc:
            state.errors.append(str(exc))
            status = "failed"
            current_step = step

        self._persist_outputs(project_id, state)
        project_service.update_workflow_state(project_id, status, current_step)
        outputs = sorted({output.relative_path for output in state.outputs})
        end_time = utc_now()
        append_run_history(
            project_dir,
            "step",
            step,
            status,
            start_time,
            end_time,
            outputs,
            state.errors,
            [],
        )
        append_audit_event(
            project_dir,
            project_id,
            "run_workflow_step",
            f"Workflow step {step} run {status}.",
            {
                "status": status,
                "step": step,
                "outputs": outputs,
                "error_count": len(state.errors),
            },
            source="api",
        )
        return WorkflowRunResponse(
            project_id=project_id,
            workflow_status=status,
            current_step=current_step,
            outputs=project_service.list_outputs(project_id),
            errors=state.errors,
        )

    def _build_state(self, project_id: str) -> ResearchState:
        project = project_service.require_project(project_id)
        project_dir = storage_service.ensure_project_structure(project_id)
        return ResearchState(
            project_id=project.id,
            project_name=project.name,
            domain=project.domain,
            language=project.language,
            output_format=project.output_format,
            literature_files=[
                path.relative_to(project_dir).as_posix()
                for path in sorted((project_dir / "literature").glob("*"))
                if path.is_file()
            ],
            data_files=[
                path.relative_to(project_dir).as_posix()
                for path in sorted((project_dir / "data").glob("*.csv"))
            ],
            workflow_status=project.workflow_status,
            current_step=project.current_step,
            project_dir=project_dir,
        )

    def _persist_outputs(self, project_id: str, state: ResearchState) -> None:
        for output in state.outputs:
            project_service.register_output(
                project_id=project_id,
                agent_name=output.agent_name,
                kind=output.kind,
                title=output.title,
                relative_path=output.relative_path,
                mime_type=output.mime_type,
            )


workflow_service = WorkflowService()
