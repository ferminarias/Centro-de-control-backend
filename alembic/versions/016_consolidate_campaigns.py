"""
Consolidate campaigns tables - Merge campaigns (VoIP) into campanias

Revision ID: 016
Revises: 015
Create Date: 2026-02-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '016'
down_revision: Union[str, None] = '015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Merge campaigns table into campanias.
    This migration:
    1. Adds VoIP-specific columns to campanias
    2. Migrates data from campaigns to campanias
    3. Updates foreign keys in campaign_agents, campaign_leads, call_records
    4. Drops the old campaigns table
    """
    
    # ─────────────────────────────────────────────────────────────────────────
    # 1. Add VoIP columns to campanias
    # ─────────────────────────────────────────────────────────────────────────
    
    op.add_column('campanias', sa.Column('trunk_id', postgresql.UUID(as_uuid=True), 
                                         sa.ForeignKey('sip_trunks.id', ondelete='SET NULL'), 
                                         nullable=True))
    op.add_column('campanias', sa.Column('pbx_node_id', postgresql.UUID(as_uuid=True), 
                                         sa.ForeignKey('pbx_nodes.id', ondelete='SET NULL'), 
                                         nullable=True))
    op.add_column('campanias', sa.Column('caller_id', sa.String(50), nullable=True))
    op.add_column('campanias', sa.Column('max_concurrent_calls', sa.Integer(), nullable=False, server_default='5'))
    op.add_column('campanias', sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'))
    op.add_column('campanias', sa.Column('retry_delay_minutes', sa.Integer(), nullable=False, server_default='60'))
    op.add_column('campanias', sa.Column('ring_timeout', sa.Integer(), nullable=False, server_default='30'))
    op.add_column('campanias', sa.Column('abandon_timeout', sa.Integer(), nullable=False, server_default='5'))
    op.add_column('campanias', sa.Column('predictive_ratio', sa.Float(), nullable=False, server_default='1.2'))
    op.add_column('campanias', sa.Column('total_leads', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('campanias', sa.Column('leads_contacted', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('campanias', sa.Column('leads_pending', sa.Integer(), nullable=False, server_default='0'))
    
    # Create indexes for new columns
    op.create_index('ix_campanias_trunk_id', 'campanias', ['trunk_id'])
    op.create_index('ix_campanias_pbx_node_id', 'campanias', ['pbx_node_id'])
    
    # ─────────────────────────────────────────────────────────────────────────
    # 2. Migrate data from campaigns to campanias
    # ─────────────────────────────────────────────────────────────────────────
    
    # Map estado from campaigns to campanias
    # campaigns: draft, running, paused, completed, stopped
    # campanias: borrador, activa, pausada, finalizada
    op.execute("""
        INSERT INTO campanias (
            id, cuenta_id, nombre, descripcion, estado,
            trunk_id, pbx_node_id, caller_id,
            tipo_discador, config_discador,
            max_concurrent_calls, max_retries, retry_delay_minutes,
            ring_timeout, abandon_timeout, predictive_ratio,
            total_leads, leads_contacted, leads_pending,
            created_at, updated_at
        )
        SELECT 
            c.id, c.cuenta_id, c.nombre, c.descripcion,
            CASE c.estado
                WHEN 'draft' THEN 'borrador'
                WHEN 'running' THEN 'activa'
                WHEN 'paused' THEN 'pausada'
                WHEN 'completed' THEN 'finalizada'
                WHEN 'stopped' THEN 'finalizada'
                ELSE 'borrador'
            END,
            c.trunk_id, c.pbx_node_id, c.caller_id,
            CASE c.dialer_mode
                WHEN 'manual' THEN 'sin_discador'
                WHEN 'progressive' THEN 'progresivo'
                WHEN 'predictive' THEN 'predictivo'
                ELSE 'sin_discador'
            END,
            jsonb_build_object(
                'hora_inicio', c.hora_inicio,
                'hora_fin', c.hora_fin,
                'timezone', c.timezone,
                'dias_semana', c.dias_semana
            ),
            c.max_concurrent_calls, c.max_retries, c.retry_delay_minutes,
            c.ring_timeout, c.abandon_timeout, c.predictive_ratio,
            c.total_leads, c.leads_contacted, c.leads_pending,
            c.created_at, c.updated_at
        FROM campaigns c
        WHERE c.id NOT IN (SELECT id FROM campanias)
    """)
    
    # ─────────────────────────────────────────────────────────────────────────
    # 3. Update foreign keys in related tables
    # ─────────────────────────────────────────────────────────────────────────
    
    # Update campaign_agents
    op.drop_constraint('campaign_agents_campaign_id_fkey', 'campaign_agents', type_='foreignkey')
    op.create_foreign_key('campaign_agents_campaign_id_fkey', 'campaign_agents', 'campanias', 
                          ['campaign_id'], ['id'], ondelete='CASCADE')
    
    # Update campaign_leads
    op.drop_constraint('campaign_leads_campaign_id_fkey', 'campaign_leads', type_='foreignkey')
    op.create_foreign_key('campaign_leads_campaign_id_fkey', 'campaign_leads', 'campanias', 
                          ['campaign_id'], ['id'], ondelete='CASCADE')
    
    # Update call_records
    op.drop_constraint('call_records_campaign_id_fkey', 'call_records', type_='foreignkey')
    op.create_foreign_key('call_records_campaign_id_fkey', 'call_records', 'campanias', 
                          ['campaign_id'], ['id'], ondelete='SET NULL')
    
    # ─────────────────────────────────────────────────────────────────────────
    # 4. Drop old campaigns table (commented for safety - run manually after verification)
    # ─────────────────────────────────────────────────────────────────────────
    # op.drop_table('campaigns')
    
    # Instead, rename it as backup
    op.rename_table('campaigns', 'campaigns_backup')
    

def downgrade() -> None:
    """Reverse the migration."""
    
    # Restore campaigns table
    op.rename_table('campaigns_backup', 'campaigns')
    
    # Restore foreign keys (pointing back to campaigns)
    op.drop_constraint('campaign_agents_campaign_id_fkey', 'campaign_agents', type_='foreignkey')
    op.create_foreign_key('campaign_agents_campaign_id_fkey', 'campaign_agents', 'campaigns', 
                          ['campaign_id'], ['id'], ondelete='CASCADE')
    
    op.drop_constraint('campaign_leads_campaign_id_fkey', 'campaign_leads', type_='foreignkey')
    op.create_foreign_key('campaign_leads_campaign_id_fkey', 'campaign_leads', 'campaigns', 
                          ['campaign_id'], ['id'], ondelete='CASCADE')
    
    op.drop_constraint('call_records_campaign_id_fkey', 'call_records', type_='foreignkey')
    op.create_foreign_key('call_records_campaign_id_fkey', 'call_records', 'campaigns', 
                          ['campaign_id'], ['id'], ondelete='SET NULL')
    
    # Drop VoIP columns from campanias
    op.drop_column('campanias', 'trunk_id')
    op.drop_column('campanias', 'pbx_node_id')
    op.drop_column('campanias', 'caller_id')
    op.drop_column('campanias', 'max_concurrent_calls')
    op.drop_column('campanias', 'max_retries')
    op.drop_column('campanias', 'retry_delay_minutes')
    op.drop_column('campanias', 'ring_timeout')
    op.drop_column('campanias', 'abandon_timeout')
    op.drop_column('campanias', 'predictive_ratio')
    op.drop_column('campanias', 'total_leads')
    op.drop_column('campanias', 'leads_contacted')
    op.drop_column('campanias', 'leads_pending')
