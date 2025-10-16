# scripts/erd_mermaid.py
from importlib import import_module
from sqlalchemy import MetaData
from app.models.base import Base

# Import all models to register tables
modules = [
    "app.identity.models.user_model",
    "app.identity.models.auth_model",
    "app.org.models.organization_model",
    "app.org.models.organization_membership_model",
    "app.workspace.models.project_model",
    "app.content.models.document_model",
    "app.messaging.models.conversation_model",
    "app.messaging.models.message_model",
    "app.messaging.models.message_attachment_model",
    "app.messaging.models.message_citation_model",
    "app.assistants.models.assistant_preset_model",
]
for m in modules: import_module(m)

md: MetaData = Base.metadata

lines = ["erDiagram"]
for t in md.tables.values():
    cols = []
    for c in t.columns:
        typ = str(c.type).split("(")[0]
        pk = " PK" if c.primary_key else ""
        cols.append(f"  {t.name} {{ {typ} {c.name}{pk} }}")
    lines.extend(cols)

# relationships
for t in md.tables.values():
    for fk in t.foreign_keys:
        a = fk.column.table.name.upper()
        b = t.name.upper()
        lines.append(f"  {a} ||--o{{ {b} : has")

print("\n".join(dict.fromkeys(lines)))