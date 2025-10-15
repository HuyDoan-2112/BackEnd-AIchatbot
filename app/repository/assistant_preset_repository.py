from typing import Optional, List, Dict, Any

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assistant_preset_model import AssistantPreset
from app.models.conversation_model import Conversation


class AssistantPresetRepository:
    """
    Repository for managing assistant presets (system prompts, tool configs, etc.).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def serialize_preset(preset: AssistantPreset, include_usage: bool = False) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "id": str(preset.id),
            "company_id": str(preset.company_id),
            "project_id": str(preset.project_id) if preset.project_id else None,
            "name": preset.name,
            "system_prompt": preset.system_prompt,
            "model_label": preset.model_label,
            "temperature": preset.temperature,
            "top_p": preset.top_p,
            "tools": preset.tools_json,
            "created_by": str(preset.created_by) if preset.created_by else None,
            "created_at": preset.created_at,
        }
        if include_usage:
            payload["conversation_ids"] = [
                str(conv.conversation_id) for conv in preset.conversations
            ]
        return payload

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
        tools_json: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None,
    ) -> AssistantPreset:
        preset = AssistantPreset(
            company_id=company_id,
            project_id=project_id,
            name=name,
            system_prompt=system_prompt,
            model_label=model_label,
            temperature=temperature,
            top_p=top_p,
            tools_json=tools_json,
            created_by=created_by,
        )
        self.db.add(preset)
        await self.db.commit()
        await self.db.refresh(preset)
        return preset

    async def get_preset(self, preset_id: str, *, with_usage: bool = False) -> Optional[AssistantPreset]:
        stmt = select(AssistantPreset).where(AssistantPreset.id == preset_id)
        if with_usage:
            stmt = stmt.options(selectinload(AssistantPreset.conversations))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_presets(
        self,
        *,
        company_id: str,
        project_id: Optional[str] = None,
        with_usage: bool = False,
    ) -> List[AssistantPreset]:
        stmt = select(AssistantPreset).where(AssistantPreset.company_id == company_id)
        if project_id is not None:
            stmt = stmt.where(
                (AssistantPreset.project_id == project_id) | (AssistantPreset.project_id.is_(None))
            )
        if with_usage:
            stmt = stmt.options(selectinload(AssistantPreset.conversations))
        result = await self.db.execute(stmt.order_by(AssistantPreset.created_at.desc()))
        return result.scalars().all()

    async def update_preset(
        self,
        preset_id: str,
        *,
        name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        model_label: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        tools_json: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
    ) -> Optional[AssistantPreset]:
        changes: Dict[str, Any] = {}
        if name is not None:
            changes["name"] = name
        if system_prompt is not None:
            changes["system_prompt"] = system_prompt
        if model_label is not None:
            changes["model_label"] = model_label
        if temperature is not None:
            changes["temperature"] = temperature
        if top_p is not None:
            changes["top_p"] = top_p
        if tools_json is not None:
            changes["tools_json"] = tools_json
        if project_id is not None:
            changes["project_id"] = project_id

        if not changes:
            return await self.get_preset(preset_id, with_usage=False)

        stmt = (
            update(AssistantPreset)
            .where(AssistantPreset.id == preset_id)
            .values(**changes)
            .returning(AssistantPreset)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    async def delete_preset(self, preset_id: str) -> bool:
        stmt = delete(AssistantPreset).where(AssistantPreset.id == preset_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0
