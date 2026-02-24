"""
Add performance indexes for critical queries

Revision ID: 017
Revises: 016
Create Date: 2026-02-24
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '017'
down_revision: Union[str, None] = '016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes for frequently queried columns."""
    
    # ─────────────────────────────────────────────────────────────────────────
    # Leads indexes
    # ─────────────────────────────────────────────────────────────────────────
    
    # Compound index for tenant + created_at (most common query pattern)
    op.create_index(
        'ix_leads_cuenta_created',
        'leads',
        ['cuenta_id', 'created_at'],
        postgresql_using='btree'
    )
    
    # Index for lead_base lookups
    op.create_index(
        'ix_leads_cuenta_base',
        'leads',
        ['cuenta_id', 'lead_base_id'],
        postgresql_using='btree'
    )
    
    # Index for lote lookups
    op.create_index(
        'ix_leads_cuenta_lote',
        'leads',
        ['cuenta_id', 'lote_id'],
        postgresql_using='btree'
    )
    
    # GIN index for JSONB datos (enables efficient JSON queries)
    op.create_index(
        'ix_leads_datos_gin',
        'leads',
        ['datos'],
        postgresql_using='gin'
    )
    
    # Index for id_lead lookups within account
    op.create_index(
        'ix_leads_cuenta_id_lead',
        'leads',
        ['cuenta_id', 'id_lead'],
        unique=True,
        postgresql_using='btree'
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Records indexes
    # ─────────────────────────────────────────────────────────────────────────
    
    # Compound index for records by account and date
    op.create_index(
        'ix_records_cuenta_created',
        'records',
        ['cuenta_id', 'created_at'],
        postgresql_using='btree'
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Campaign leads indexes (for dialer performance)
    # ─────────────────────────────────────────────────────────────────────────
    
    # Index for pending leads to dial (critical for dialer performance)
    op.create_index(
        'ix_campaign_leads_pending',
        'campaign_leads',
        ['campaign_id', 'estado', 'proximo_intento'],
        postgresql_where="estado = 'pending'",
        postgresql_using='btree'
    )
    
    # Index for leads by phone number
    op.create_index(
        'ix_campaign_leads_telefono',
        'campaign_leads',
        ['campaign_id', 'telefono'],
        postgresql_using='btree'
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Call records indexes
    # ─────────────────────────────────────────────────────────────────────────
    
    # Index for CDR queries by account and date
    op.create_index(
        'ix_call_records_cuenta_date',
        'call_records',
        ['cuenta_id', 'created_at'],
        postgresql_using='btree'
    )
    
    # Index for agent performance queries
    op.create_index(
        'ix_call_records_agente',
        'call_records',
        ['agent_id', 'created_at'],
        postgresql_using='btree'
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Audit logs indexes
    # ─────────────────────────────────────────────────────────────────────────
    
    # Index for audit queries by entity
    op.create_index(
        'ix_audit_logs_entity',
        'audit_logs',
        ['tabla', 'record_id'],
        postgresql_using='btree'
    )
    
    # Index for recent audit logs
    op.create_index(
        'ix_audit_logs_created',
        'audit_logs',
        ['created_at'],
        postgresql_using='btree'
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Automation logs indexes
    # ─────────────────────────────────────────────────────────────────────────
    
    # Index for automation logs by lead
    op.create_index(
        'ix_automation_logs_lead',
        'automation_logs',
        ['lead_id', 'created_at'],
        postgresql_using='btree'
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Cola leads indexes (contact center)
    # ─────────────────────────────────────────────────────────────────────────
    
    # Index for pending leads in queue
    op.create_index(
        'ix_cola_leads_pendientes',
        'cola_leads',
        ['campania_id', 'estado', 'prioridad'],
        postgresql_where="estado = 'pendiente'",
        postgresql_using='btree'
    )


def downgrade() -> None:
    """Remove the performance indexes."""
    
    # Leads indexes
    op.drop_index('ix_leads_cuenta_created', table_name='leads')
    op.drop_index('ix_leads_cuenta_base', table_name='leads')
    op.drop_index('ix_leads_cuenta_lote', table_name='leads')
    op.drop_index('ix_leads_datos_gin', table_name='leads')
    op.drop_index('ix_leads_cuenta_id_lead', table_name='leads')
    
    # Records indexes
    op.drop_index('ix_records_cuenta_created', table_name='records')
    
    # Campaign leads indexes
    op.drop_index('ix_campaign_leads_pending', table_name='campaign_leads')
    op.drop_index('ix_campaign_leads_telefono', table_name='campaign_leads')
    
    # Call records indexes
    op.drop_index('ix_call_records_cuenta_date', table_name='call_records')
    op.drop_index('ix_call_records_agente', table_name='call_records')
    
    # Audit logs indexes
    op.drop_index('ix_audit_logs_entity', table_name='audit_logs')
    op.drop_index('ix_audit_logs_created', table_name='audit_logs')
    
    # Automation logs indexes
    op.drop_index('ix_automation_logs_lead', table_name='automation_logs')
    
    # Cola leads indexes
    op.drop_index('ix_cola_leads_pendientes', table_name='cola_leads')
