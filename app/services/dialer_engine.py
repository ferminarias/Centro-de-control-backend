"""
Dialer Engine — orchestrates call campaigns.

Modes:
  - Manual: Agent clicks "call" → originate via AMI
  - Progressive: System dials next lead when agent becomes available (1:1 ratio)
  - Predictive: System dials multiple leads per available agent (ratio-based)

This module provides synchronous helpers called from API endpoints.
The automatic dialer (progressive/predictive) is designed to be invoked
periodically by a scheduler (e.g., Celery beat, APScheduler, or cron).
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.voip import (
    Agent, AgentStatus, Campaign, CampaignAgent, CampaignLead,
    CampaignLeadStatus, CampaignStatus, DncEntry,
)
from app.services.ami_manager import OriginateResult, ami_manager

logger = logging.getLogger(__name__)


def manual_call(
    db: Session,
    *,
    cuenta_id: uuid.UUID,
    agent_id: uuid.UUID,
    campaign_lead_id: uuid.UUID,
) -> OriginateResult:
    """
    Manual click-to-call: agent selects a lead and clicks "call".
    Validates agent state, DNC, and originates.
    """
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.cuenta_id == cuenta_id,
        Agent.activo.is_(True),
    ).first()
    if not agent:
        return OriginateResult(success=False, message="Agent not found or inactive")

    if agent.estado not in (AgentStatus.AVAILABLE.value, AgentStatus.WRAP_UP.value):
        return OriginateResult(success=False, message=f"Agent is not available (current: {agent.estado})")

    cl = db.query(CampaignLead).filter(CampaignLead.id == campaign_lead_id).first()
    if not cl:
        return OriginateResult(success=False, message="Campaign lead not found")

    campaign = db.query(Campaign).filter(Campaign.id == cl.campaign_id).first()
    if not campaign:
        return OriginateResult(success=False, message="Campaign not found")

    # Check DNC
    is_dnc = db.query(DncEntry).filter(
        DncEntry.cuenta_id == cuenta_id,
        DncEntry.telefono == cl.telefono,
    ).first()
    if is_dnc:
        cl.estado = CampaignLeadStatus.DNC.value
        db.commit()
        return OriginateResult(success=False, message="Number is on DNC list")

    # Check max retries
    if cl.intentos >= campaign.max_retries:
        return OriginateResult(success=False, message="Max retries reached for this lead")

    return ami_manager.originate_call(
        db,
        cuenta_id=cuenta_id,
        agent=agent,
        destino=cl.telefono,
        campaign=campaign,
        campaign_lead=cl,
    )


def get_next_lead(db: Session, campaign: Campaign) -> CampaignLead | None:
    """
    Get the next lead to dial for a campaign.
    Priority: callbacks first, then scheduled retries, then pending.
    """
    now = datetime.now(timezone.utc)

    # 1. Scheduled callbacks that are due
    callback_lead = (
        db.query(CampaignLead)
        .filter(
            CampaignLead.campaign_id == campaign.id,
            CampaignLead.estado == CampaignLeadStatus.SCHEDULED.value,
            CampaignLead.callback_at <= now,
        )
        .order_by(CampaignLead.callback_at)
        .first()
    )
    if callback_lead:
        return callback_lead

    # 2. Leads that need retry and enough time has passed
    retry_lead = (
        db.query(CampaignLead)
        .filter(
            CampaignLead.campaign_id == campaign.id,
            CampaignLead.estado.in_([
                CampaignLeadStatus.NO_ANSWER.value,
                CampaignLeadStatus.BUSY.value,
                CampaignLeadStatus.FAILED.value,
            ]),
            CampaignLead.intentos < campaign.max_retries,
            CampaignLead.proximo_intento <= now,
        )
        .order_by(CampaignLead.proximo_intento)
        .first()
    )
    if retry_lead:
        return retry_lead

    # 3. Fresh pending leads
    pending_lead = (
        db.query(CampaignLead)
        .filter(
            CampaignLead.campaign_id == campaign.id,
            CampaignLead.estado == CampaignLeadStatus.PENDING.value,
        )
        .order_by(CampaignLead.created_at)
        .first()
    )
    return pending_lead


def get_available_agents(db: Session, campaign_id: uuid.UUID) -> list[Agent]:
    """Get agents assigned to a campaign that are currently available."""
    agent_ids = (
        db.query(CampaignAgent.agent_id)
        .filter(CampaignAgent.campaign_id == campaign_id)
        .subquery()
    )
    return (
        db.query(Agent)
        .filter(
            Agent.id.in_(agent_ids),
            Agent.activo.is_(True),
            Agent.estado == AgentStatus.AVAILABLE.value,
        )
        .all()
    )


def get_active_calls_count(db: Session, campaign_id: uuid.UUID) -> int:
    """Count currently dialing/active calls for a campaign."""
    return (
        db.query(CampaignLead)
        .filter(
            CampaignLead.campaign_id == campaign_id,
            CampaignLead.estado == CampaignLeadStatus.DIALING.value,
        )
        .count()
    )


def is_campaign_in_schedule(campaign: Campaign) -> bool:
    """Check if the current time is within the campaign's schedule window."""
    if not campaign.hora_inicio or not campaign.hora_fin:
        return True  # No schedule restriction

    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo(campaign.timezone)
    except Exception:
        tz = timezone.utc

    now = datetime.now(tz)
    current_time = now.time()
    current_dow = now.isoweekday()  # 1=Mon, 7=Sun

    if campaign.dias_semana and current_dow not in campaign.dias_semana:
        return False

    return campaign.hora_inicio <= current_time <= campaign.hora_fin


def run_progressive_dialer(db: Session, campaign: Campaign) -> list[OriginateResult]:
    """
    Progressive dialer: 1 call per available agent.
    Called periodically by a scheduler.
    """
    if campaign.estado != CampaignStatus.RUNNING.value:
        return []

    if not is_campaign_in_schedule(campaign):
        return []

    available = get_available_agents(db, campaign.id)
    if not available:
        return []

    active_calls = get_active_calls_count(db, campaign.id)
    max_new = campaign.max_concurrent_calls - active_calls
    if max_new <= 0:
        return []

    results = []
    for agent in available[:max_new]:
        lead = get_next_lead(db, campaign)
        if not lead:
            break

        # Check DNC
        is_dnc = db.query(DncEntry).filter(
            DncEntry.cuenta_id == campaign.cuenta_id,
            DncEntry.telefono == lead.telefono,
        ).first()
        if is_dnc:
            lead.estado = CampaignLeadStatus.DNC.value
            db.commit()
            continue

        result = ami_manager.originate_call(
            db,
            cuenta_id=campaign.cuenta_id,
            agent=agent,
            destino=lead.telefono,
            campaign=campaign,
            campaign_lead=lead,
        )
        results.append(result)

    return results


def run_predictive_dialer(db: Session, campaign: Campaign) -> list[OriginateResult]:
    """
    Predictive dialer: dials (ratio * available_agents) calls.
    Excess answered calls queue for next available agent.
    """
    if campaign.estado != CampaignStatus.RUNNING.value:
        return []

    if not is_campaign_in_schedule(campaign):
        return []

    available_count = len(get_available_agents(db, campaign.id))
    if available_count == 0:
        return []

    active_calls = get_active_calls_count(db, campaign.id)
    target_calls = int(available_count * campaign.predictive_ratio)
    max_new = min(target_calls - active_calls, campaign.max_concurrent_calls - active_calls)
    if max_new <= 0:
        return []

    # For predictive, we get all available agents and cycle through them
    agents = get_available_agents(db, campaign.id)
    results = []
    agent_idx = 0

    for _ in range(max_new):
        lead = get_next_lead(db, campaign)
        if not lead:
            break

        # Check DNC
        is_dnc = db.query(DncEntry).filter(
            DncEntry.cuenta_id == campaign.cuenta_id,
            DncEntry.telefono == lead.telefono,
        ).first()
        if is_dnc:
            lead.estado = CampaignLeadStatus.DNC.value
            db.commit()
            continue

        agent = agents[agent_idx % len(agents)]
        agent_idx += 1

        result = ami_manager.originate_call(
            db,
            cuenta_id=campaign.cuenta_id,
            agent=agent,
            destino=lead.telefono,
            campaign=campaign,
            campaign_lead=lead,
        )
        results.append(result)

    return results


def update_campaign_stats(db: Session, campaign_id: uuid.UUID) -> None:
    """Recalculate cached campaign metrics from campaign_leads."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        return

    total = db.query(func.count(CampaignLead.id)).filter(
        CampaignLead.campaign_id == campaign_id
    ).scalar() or 0

    contacted = db.query(func.count(CampaignLead.id)).filter(
        CampaignLead.campaign_id == campaign_id,
        CampaignLead.estado == CampaignLeadStatus.CONTACTED.value,
    ).scalar() or 0

    completed = db.query(func.count(CampaignLead.id)).filter(
        CampaignLead.campaign_id == campaign_id,
        CampaignLead.estado == CampaignLeadStatus.COMPLETED.value,
    ).scalar() or 0

    pending = db.query(func.count(CampaignLead.id)).filter(
        CampaignLead.campaign_id == campaign_id,
        CampaignLead.estado == CampaignLeadStatus.PENDING.value,
    ).scalar() or 0

    campaign.total_leads = total
    campaign.leads_contacted = contacted + completed
    campaign.leads_pending = pending
    db.commit()


def set_lead_retry(
    db: Session,
    campaign_lead: CampaignLead,
    campaign: Campaign,
) -> None:
    """Schedule the next retry for a campaign lead."""
    campaign_lead.proximo_intento = datetime.now(timezone.utc) + timedelta(
        minutes=campaign.retry_delay_minutes
    )
    db.commit()
