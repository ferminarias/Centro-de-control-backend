"""
Partition leads table by month for scalability (10M+ leads target)

Revision ID: 018
Revises: 017
Create Date: 2026-03-12

Strategy:
- The leads table is converted to a range-partitioned table on created_at.
- Existing rows are preserved by recreating the table and migrating data.
- A default partition catches rows that don't match any explicit range.
- Partitions for the current and next 12 months are created automatically.
- A trigger creates new monthly partitions on demand.

NOTE: This migration requires a maintenance window (~seconds to minutes
      depending on lead count). No data is lost.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Convert leads to a partitioned table.

    Steps:
    1. Rename current leads table to leads_old
    2. Create new partitioned leads table (same schema)
    3. Copy data from leads_old to new leads
    4. Drop leads_old
    5. Create initial monthly partitions (current month + 12 months ahead)
    6. Create a default partition for out-of-range rows
    7. Create function + trigger to auto-create future partitions
    """

    # ── Step 1: Rename existing table ────────────────────────────────────────
    op.execute("ALTER TABLE leads RENAME TO leads_old")

    # ── Step 2: Create partitioned table ─────────────────────────────────────
    # Mirrors the current leads schema + PARTITION BY RANGE (created_at)
    op.execute("""
        CREATE TABLE leads (
            id          UUID NOT NULL DEFAULT gen_random_uuid(),
            id_lead     INTEGER,
            cuenta_id   UUID NOT NULL,
            record_id   UUID,
            lead_base_id UUID,
            lote_id     UUID,
            assigned_to UUID,
            assigned_at TIMESTAMPTZ,
            assigned_by_rule VARCHAR(50),
            tipificacion_id UUID,
            subtipificacion_id UUID,
            ultima_tipificacion JSONB,
            score       INTEGER DEFAULT 0,
            temperatura VARCHAR(20) DEFAULT 'frio',
            datos       JSONB DEFAULT '{}',
            created_at  TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at  TIMESTAMPTZ DEFAULT now(),
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at)
    """)

    # ── Step 3: Re-create indexes on the partitioned table ───────────────────
    # Indexes on partitioned tables are inherited by each partition
    op.execute("CREATE INDEX ix_leads_cuenta_id ON leads (cuenta_id)")
    op.execute("CREATE INDEX ix_leads_lead_base_id ON leads (lead_base_id)")
    op.execute("CREATE INDEX ix_leads_lote_id ON leads (lote_id)")
    op.execute("CREATE INDEX ix_leads_id_lead ON leads (id_lead)")
    op.execute("CREATE INDEX ix_leads_cuenta_created ON leads (cuenta_id, created_at)")
    op.execute("CREATE INDEX ix_leads_cuenta_base ON leads (cuenta_id, lead_base_id)")
    op.execute("CREATE INDEX ix_leads_cuenta_lote ON leads (cuenta_id, lote_id)")
    op.execute("CREATE INDEX ix_leads_cuenta_id_lead ON leads (cuenta_id, id_lead)")
    op.execute("CREATE INDEX ix_leads_datos_gin ON leads USING GIN (datos)")

    # ── Step 4: Create initial monthly partitions (current month + 12 months) ─
    op.execute("""
        DO $$
        DECLARE
            start_date DATE;
            end_date   DATE;
            part_name  TEXT;
        BEGIN
            -- Create partitions from 2024-01 through 13 months from now
            start_date := '2024-01-01'::DATE;
            WHILE start_date <= (DATE_TRUNC('month', NOW()) + INTERVAL '13 months') LOOP
                end_date  := start_date + INTERVAL '1 month';
                part_name := 'leads_' || TO_CHAR(start_date, 'YYYY_MM');

                IF NOT EXISTS (
                    SELECT 1 FROM pg_class
                    WHERE relname = part_name AND relkind = 'r'
                ) THEN
                    EXECUTE FORMAT(
                        'CREATE TABLE %I PARTITION OF leads '
                        'FOR VALUES FROM (%L) TO (%L)',
                        part_name, start_date, end_date
                    );
                END IF;

                start_date := end_date;
            END LOOP;
        END $$
    """)

    # ── Step 5: Default partition for any rows outside defined ranges ─────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS leads_default
            PARTITION OF leads DEFAULT
    """)

    # ── Step 6: Copy data from leads_old ─────────────────────────────────────
    op.execute("""
        INSERT INTO leads (
            id, id_lead, cuenta_id, record_id, lead_base_id, lote_id,
            assigned_to, assigned_at, assigned_by_rule,
            tipificacion_id, subtipificacion_id, ultima_tipificacion,
            score, temperatura, datos, created_at, updated_at
        )
        SELECT
            id, id_lead, cuenta_id, record_id, lead_base_id, lote_id,
            assigned_to, assigned_at, assigned_by_rule,
            tipificacion_id, subtipificacion_id, ultima_tipificacion,
            score, temperatura, datos,
            COALESCE(created_at, NOW()),
            updated_at
        FROM leads_old
    """)

    # ── Step 7: Drop old table ────────────────────────────────────────────────
    op.execute("DROP TABLE leads_old CASCADE")

    # ── Step 8: Auto-partition trigger function ───────────────────────────────
    op.execute("""
        CREATE OR REPLACE FUNCTION leads_create_partition()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        DECLARE
            partition_date DATE := DATE_TRUNC('month', NEW.created_at);
            partition_name TEXT := 'leads_' || TO_CHAR(partition_date, 'YYYY_MM');
            next_date      DATE := partition_date + INTERVAL '1 month';
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_class WHERE relname = partition_name AND relkind = 'r'
            ) THEN
                EXECUTE FORMAT(
                    'CREATE TABLE %I PARTITION OF leads FOR VALUES FROM (%L) TO (%L)',
                    partition_name, partition_date, next_date
                );
            END IF;
            RETURN NEW;
        END $$
    """)

    op.execute("""
        CREATE TRIGGER trg_leads_auto_partition
        BEFORE INSERT ON leads
        FOR EACH ROW
        EXECUTE FUNCTION leads_create_partition()
    """)


def downgrade() -> None:
    """Reverse: convert partitioned table back to a regular table."""

    op.execute("DROP TRIGGER IF EXISTS trg_leads_auto_partition ON leads")
    op.execute("DROP FUNCTION IF EXISTS leads_create_partition()")

    # Create regular table
    op.execute("""
        CREATE TABLE leads_restored (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            id_lead     INTEGER,
            cuenta_id   UUID NOT NULL,
            record_id   UUID,
            lead_base_id UUID,
            lote_id     UUID,
            assigned_to UUID,
            assigned_at TIMESTAMPTZ,
            assigned_by_rule VARCHAR(50),
            tipificacion_id UUID,
            subtipificacion_id UUID,
            ultima_tipificacion JSONB,
            score       INTEGER DEFAULT 0,
            temperatura VARCHAR(20) DEFAULT 'frio',
            datos       JSONB DEFAULT '{}',
            created_at  TIMESTAMPTZ DEFAULT now(),
            updated_at  TIMESTAMPTZ DEFAULT now()
        )
    """)

    op.execute("""
        INSERT INTO leads_restored SELECT * FROM leads
    """)

    op.execute("DROP TABLE leads CASCADE")
    op.execute("ALTER TABLE leads_restored RENAME TO leads")

    # Restore indexes
    op.execute("CREATE INDEX ix_leads_cuenta_id ON leads (cuenta_id)")
    op.execute("CREATE INDEX ix_leads_lead_base_id ON leads (lead_base_id)")
    op.execute("CREATE INDEX ix_leads_lote_id ON leads (lote_id)")
    op.execute("CREATE INDEX ix_leads_id_lead ON leads (id_lead)")
