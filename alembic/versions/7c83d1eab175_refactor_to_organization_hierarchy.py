"""refactor_to_organization_hierarchy

Revision ID: 7c83d1eab175
Revises: 22186259fe47
Create Date: 2025-10-15 20:32:41.890697

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7c83d1eab175'
down_revision: Union[str, Sequence[str], None] = '22186259fe47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade to organization-based hierarchy."""
    
    # 1. Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False, server_default='company'),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('parent_organization_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rag_vector_store_id', sa.String(), nullable=True),
        sa.Column('rag_config', postgresql.JSONB(), nullable=True),
        sa.Column('country', sa.String(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['parent_organization_id'], ['organizations.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_organizations_name', 'organizations', ['name'])
    op.create_index('ix_organizations_parent', 'organizations', ['parent_organization_id'])
    op.create_index('ix_organizations_type', 'organizations', ['type'])
    
    # 2. Create organization_memberships table
    op.create_table(
        'organization_memberships',
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(), nullable=False, server_default='member'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('organization_id', 'user_id')
    )
    
    # 3. Migrate companies to organizations (if companies table exists)
    connection = op.get_bind()
    if connection.dialect.has_table(connection, 'companies'):
        op.execute("""
            INSERT INTO organizations (id, name, type, description, location, created_at)
            SELECT id, name, 'company', description, location, NOW()
            FROM companies
        """)
        
        # 4. Migrate company_memberships to organization_memberships
        op.execute("""
            INSERT INTO organization_memberships (organization_id, user_id, role, joined_at)
            SELECT company_id, user_id, role, joined_at
            FROM company_memberships
        """)
    
    # 5. Update projects table - Add new columns
    op.add_column('projects', sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('projects', sa.Column('rag_enabled', sa.Boolean(), server_default='true'))
    op.add_column('projects', sa.Column('rag_vector_store_id', sa.String(), nullable=True))
    op.add_column('projects', sa.Column('rag_chunk_size', sa.Integer(), server_default='1000'))
    op.add_column('projects', sa.Column('rag_chunk_overlap', sa.Integer(), server_default='200'))
    op.add_column('projects', sa.Column('rag_config', postgresql.JSONB(), nullable=True))
    op.add_column('projects', sa.Column('rules', postgresql.JSONB(), nullable=True))
    op.add_column('projects', sa.Column('default_model', sa.String(), server_default='gpt-4'))
    op.add_column('projects', sa.Column('system_prompt', sa.String(), nullable=True))
    
    # Add timestamps if they don't exist
    try:
        op.add_column('projects', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
        op.add_column('projects', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    except:
        pass  # Columns might already exist
    
    # 6. Migrate company_id to organization_id in projects
    if connection.dialect.has_table(connection, 'companies'):
        op.execute("""
            UPDATE projects
            SET organization_id = company_id
            WHERE company_id IS NOT NULL
        """)
    
    # 7. Make organization_id NOT NULL and add FK
    op.alter_column('projects', 'organization_id', nullable=False)
    op.create_foreign_key('fk_projects_organization', 'projects', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_projects_organization', 'projects', ['organization_id'])
    
    # 8. Drop old company_id from projects if it exists
    try:
        op.drop_constraint('projects_company_id_fkey', 'projects', type_='foreignkey')
        op.drop_column('projects', 'company_id')
    except:
        pass  # Column might not exist
    
    # 9. Update documents table
    op.add_column('documents', sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('documents', sa.Column('file_path', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('file_type', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('filename', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('file_size_bytes', sa.Integer(), nullable=True))
    op.add_column('documents', sa.Column('vector_embedding', postgresql.ARRAY(sa.Float()), nullable=True))
    
    # Add updated_at if it doesn't exist
    try:
        op.add_column('documents', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()))
    except:
        pass
    
    # 10. Migrate documents from project_documents join table if it exists
    if connection.dialect.has_table(connection, 'project_documents'):
        op.execute("""
            UPDATE documents d
            SET project_id = (
                SELECT pd.project_id
                FROM project_documents pd
                WHERE d.id = pd.document_id
                LIMIT 1
            )
            WHERE EXISTS (SELECT 1 FROM project_documents pd WHERE d.id = pd.document_id)
        """)
    
    # 11. Make project_id NOT NULL and add FK
    op.alter_column('documents', 'project_id', nullable=False)
    op.create_foreign_key('fk_documents_project', 'documents', 'projects', ['project_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_documents_project', 'documents', ['project_id'])
    
    # 12. Drop company_id from documents if it exists
    try:
        op.drop_constraint('documents_company_id_fkey', 'documents', type_='foreignkey')
        op.drop_column('documents', 'company_id')
    except:
        pass
    
    # 13. Update conversations table - handle orphaned conversations and make project_id NOT NULL
    # Delete conversations that don't have a project_id (orphaned conversations)
    connection.execute(sa.text("""
        DELETE FROM conversations WHERE project_id IS NULL
    """))
    
    op.alter_column('conversations', 'project_id', nullable=False)
    op.create_index('ix_conversations_project', 'conversations', ['project_id'])
    
    # 14. Drop company_id from conversations if it exists
    try:
        op.drop_constraint('conversations_company_id_fkey', 'conversations', type_='foreignkey')
        op.drop_column('conversations', 'company_id')
    except:
        pass
    
    # 15. Update messages table - add vector_embedding and tool_calls_json
    op.add_column('messages', sa.Column('vector_embedding', postgresql.ARRAY(sa.Float()), nullable=True))
    op.add_column('messages', sa.Column('tool_calls_json', postgresql.JSONB(), nullable=True))
    
    # 16. Update assistant_presets table
    op.add_column('assistant_presets', sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Migrate company_id to organization_id
    if connection.dialect.has_table(connection, 'companies'):
        op.execute("""
            UPDATE assistant_presets
            SET organization_id = company_id
            WHERE company_id IS NOT NULL
        """)
    
    op.alter_column('assistant_presets', 'organization_id', nullable=False)
    op.create_foreign_key('fk_assistant_presets_organization', 'assistant_presets', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_assistant_presets_organization', 'assistant_presets', ['organization_id'])
    
    # Drop old company_id
    try:
        op.drop_constraint('assistant_presets_company_id_fkey', 'assistant_presets', type_='foreignkey')
        op.drop_column('assistant_presets', 'company_id')
    except:
        pass
    
    # 17. Drop old join tables
    op.drop_table('project_conversations', if_exists=True)
    op.drop_table('project_documents', if_exists=True)
    
    # 18. Drop old tables
    op.drop_table('company_memberships', if_exists=True)
    op.drop_table('companies', if_exists=True)


def downgrade() -> None:
    """Downgrade back to company-based schema (NOT RECOMMENDED - will lose hierarchy data)."""
    
    # Recreate companies table
    op.create_table(
        'companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), unique=True, nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
    )
    
    # Migrate top-level organizations back to companies
    op.execute("""
        INSERT INTO companies (id, name, description, location)
        SELECT id, name, description, location
        FROM organizations
        WHERE parent_organization_id IS NULL AND type = 'company'
    """)
    
    # Recreate company_memberships
    op.create_table(
        'company_memberships',
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('company_id', 'user_id')
    )
    
    # Migrate organization_memberships back
    op.execute("""
        INSERT INTO company_memberships (company_id, user_id, role, joined_at)
        SELECT organization_id, user_id, role, joined_at
        FROM organization_memberships om
        JOIN organizations o ON om.organization_id = o.id
        WHERE o.parent_organization_id IS NULL AND o.type = 'company'
    """)
    
    # Revert projects table
    op.add_column('projects', sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE projects SET company_id = organization_id")
    op.create_foreign_key('projects_company_id_fkey', 'projects', 'companies', ['company_id'], ['id'], ondelete='CASCADE')
    
    op.drop_constraint('fk_projects_organization', 'projects', type_='foreignkey')
    op.drop_index('ix_projects_organization', 'projects')
    op.drop_column('projects', 'organization_id')
    op.drop_column('projects', 'rag_enabled')
    op.drop_column('projects', 'rag_vector_store_id')
    op.drop_column('projects', 'rag_chunk_size')
    op.drop_column('projects', 'rag_chunk_overlap')
    op.drop_column('projects', 'rag_config')
    op.drop_column('projects', 'rules')
    op.drop_column('projects', 'default_model')
    op.drop_column('projects', 'system_prompt')
    
    # Revert documents
    op.add_column('documents', sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.drop_constraint('fk_documents_project', 'documents', type_='foreignkey')
    op.drop_index('ix_documents_project', 'documents')
    op.drop_column('documents', 'project_id')
    op.drop_column('documents', 'file_path')
    op.drop_column('documents', 'file_type')
    op.drop_column('documents', 'filename')
    op.drop_column('documents', 'file_size_bytes')
    op.drop_column('documents', 'vector_embedding')
    
    # Revert conversations
    op.add_column('conversations', sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.alter_column('conversations', 'project_id', nullable=True)
    op.drop_index('ix_conversations_project', 'conversations')
    
    # Revert messages
    op.drop_column('messages', 'vector_embedding')
    op.drop_column('messages', 'tool_calls_json')
    
    # Revert assistant_presets
    op.add_column('assistant_presets', sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE assistant_presets SET company_id = organization_id")
    op.create_foreign_key('assistant_presets_company_id_fkey', 'assistant_presets', 'companies', ['company_id'], ['id'], ondelete='CASCADE')
    
    op.drop_constraint('fk_assistant_presets_organization', 'assistant_presets', type_='foreignkey')
    op.drop_index('ix_assistant_presets_organization', 'assistant_presets')
    op.drop_column('assistant_presets', 'organization_id')
    
    # Drop organization tables
    op.drop_table('organization_memberships')
    op.drop_table('organizations')

