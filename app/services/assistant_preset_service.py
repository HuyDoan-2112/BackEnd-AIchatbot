from typing import Optional, Dict, Any, List

from app.db.postgresql import get_db_connection
from app.repository.assistant_preset_repository import AssistantPresetRepository
from app.core.response_status import ResponseStatus, OK, NotFound, InternalError, Conflict


class AssistantPresetService:
    """
    Service layer for assistant presets, bridging API requests and repository operations.
    """

    def __init__(self):
        self._db_connection = None

    def _get_db(self):
        if self._db_connection is None:
            self._db_connection = get_db_connection()
        return self._db_connection

    async def create_preset(
        self,
        *,
        company_id: str,
        name: str,
        model_label: str,
        project_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        tools: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None,
    ) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = AssistantPresetRepository(session)

                # Ensure uniqueness within project scope
                existing = await repo.list_presets(
                    company_id=company_id,
                    project_id=project_id,
                )
                if any(preset.name == name for preset in existing):
                    return Conflict(message="Preset name already exists for this scope", error_code="4009")

                preset = await repo.create_preset(
                    company_id=company_id,
                    name=name,
                    model_label=model_label,
                    project_id=project_id,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    top_p=top_p,
                    tools_json=tools,
                    created_by=created_by,
                )
                return OK(message="Preset created", data=repo.serialize_preset(preset))
        except Exception as exc:
            return InternalError(message=f"Failed to create preset: {exc}")

    async def list_presets(
        self,
        *,
        company_id: str,
        project_id: Optional[str] = None,
        include_usage: bool = False,
    ) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = AssistantPresetRepository(session)
                presets = await repo.list_presets(
                    company_id=company_id,
                    project_id=project_id,
                    with_usage=include_usage,
                )
                data = [repo.serialize_preset(p, include_usage=include_usage) for p in presets]
                return OK(data=data)
        except Exception as exc:
            return InternalError(message=f"Failed to list presets: {exc}")

    async def get_preset(self, preset_id: str, *, include_usage: bool = False) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = AssistantPresetRepository(session)
                preset = await repo.get_preset(preset_id, with_usage=include_usage)
                if not preset:
                    return NotFound(message="Preset not found", error_code="4004")
                return OK(data=repo.serialize_preset(preset, include_usage=include_usage))
        except Exception as exc:
            return InternalError(message=f"Failed to fetch preset: {exc}")

    async def update_preset(
        self,
        preset_id: str,
        *,
        name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        model_label: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        tools: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
    ) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = AssistantPresetRepository(session)

                updated = await repo.update_preset(
                    preset_id,
                    name=name,
                    system_prompt=system_prompt,
                    model_label=model_label,
                    temperature=temperature,
                    top_p=top_p,
                    tools_json=tools,
                    project_id=project_id,
                )
                if not updated:
                    return NotFound(message="Preset not found", error_code="4004")
                return OK(message="Preset updated", data=repo.serialize_preset(updated))
        except Exception as exc:
            return InternalError(message=f"Failed to update preset: {exc}")

    async def delete_preset(self, preset_id: str) -> ResponseStatus:
        try:
            async for session in self._get_db().get_session():
                repo = AssistantPresetRepository(session)
                removed = await repo.delete_preset(preset_id)
                if not removed:
                    return NotFound(message="Preset not found", error_code="4004")
                return OK(message="Preset deleted")
        except Exception as exc:
            return InternalError(message=f"Failed to delete preset: {exc}")


assistant_preset_service = AssistantPresetService()
