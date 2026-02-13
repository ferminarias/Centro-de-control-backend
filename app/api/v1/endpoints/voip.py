"""
VoIP / Call Center API endpoints.

Covers: SIP Providers, SIP Trunks, PBX Nodes, Agents, Dispositions,
Campaigns (CRUD + state + agents + leads), Call Records, DNC, Dialer control.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_admin_key
from app.models.account import Account
from app.models.lead import Lead
from app.models.voip import (
    Agent, AgentStatus, CallEvent, CallRecord, Campaign, CampaignAgent,
    CampaignLead, CampaignLeadStatus, CampaignStatus, Disposition,
    DncEntry, PbxNode, SipProvider, SipTrunk,
)
from app.schemas.voip import (
    AgentCreate, AgentListResponse, AgentResponse, AgentStatusUpdate, AgentUpdate,
    CallEventResponse, CallRecordListResponse, CallRecordResponse,
    CampaignCreate, CampaignLeadAdd, CampaignLeadBulkAdd, CampaignLeadDisposition,
    CampaignLeadListResponse, CampaignLeadResponse, CampaignListResponse, CampaignResponse,
    CampaignStatsResponse, CampaignUpdate,
    DispositionCreate, DispositionListResponse, DispositionResponse, DispositionUpdate,
    DncCreate, DncListResponse, DncResponse,
    ManualCallRequest, ManualCallResponse,
    PbxNodeCreate, PbxNodeListResponse, PbxNodeResponse, PbxNodeUpdate,
    SipProviderCreate, SipProviderListResponse, SipProviderResponse, SipProviderUpdate,
    SipTrunkCreate, SipTrunkListResponse, SipTrunkResponse, SipTrunkUpdate,
)
from app.services.ami_manager import ami_manager
from app.services.dialer_engine import manual_call, update_campaign_stats

router = APIRouter(dependencies=[Depends(verify_admin_key)])


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_account(db: Session, account_id: uuid.UUID) -> Account:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


# ═══════════════════════════════════════════════════════════════════════════════
# SIP Providers
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/accounts/{account_id}/sip-providers",
    response_model=SipProviderResponse,
    status_code=201,
    summary="Create a SIP provider",
)
def create_sip_provider(
    account_id: uuid.UUID, body: SipProviderCreate, db: Session = Depends(get_db),
):
    _get_account(db, account_id)
    provider = SipProvider(cuenta_id=account_id, nombre=body.nombre, pais=body.pais, notas=body.notas)
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


@router.get(
    "/accounts/{account_id}/sip-providers",
    response_model=SipProviderListResponse,
    summary="List SIP providers",
)
def list_sip_providers(account_id: uuid.UUID, db: Session = Depends(get_db)):
    _get_account(db, account_id)
    items = db.query(SipProvider).filter(SipProvider.cuenta_id == account_id).order_by(SipProvider.created_at).all()
    return {"items": items, "total": len(items)}


@router.put(
    "/sip-providers/{provider_id}",
    response_model=SipProviderResponse,
    summary="Update a SIP provider",
)
def update_sip_provider(provider_id: uuid.UUID, body: SipProviderUpdate, db: Session = Depends(get_db)):
    provider = db.query(SipProvider).filter(SipProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="SIP provider not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(provider, field, value)
    db.commit()
    db.refresh(provider)
    return provider


@router.delete("/sip-providers/{provider_id}", status_code=204, summary="Delete a SIP provider")
def delete_sip_provider(provider_id: uuid.UUID, db: Session = Depends(get_db)):
    provider = db.query(SipProvider).filter(SipProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="SIP provider not found")
    db.delete(provider)
    db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# SIP Trunks
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/sip-providers/{provider_id}/trunks",
    response_model=SipTrunkResponse,
    status_code=201,
    summary="Create a SIP trunk",
)
def create_sip_trunk(provider_id: uuid.UUID, body: SipTrunkCreate, db: Session = Depends(get_db)):
    provider = db.query(SipProvider).filter(SipProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="SIP provider not found")
    trunk = SipTrunk(cuenta_id=provider.cuenta_id, provider_id=provider_id)
    for field, value in body.model_dump(exclude={"provider_id"}).items():
        setattr(trunk, field, value)
    db.add(trunk)
    db.commit()
    db.refresh(trunk)
    return trunk


@router.get(
    "/accounts/{account_id}/sip-trunks",
    response_model=SipTrunkListResponse,
    summary="List all SIP trunks for an account",
)
def list_sip_trunks(account_id: uuid.UUID, db: Session = Depends(get_db)):
    _get_account(db, account_id)
    items = db.query(SipTrunk).filter(SipTrunk.cuenta_id == account_id).order_by(SipTrunk.created_at).all()
    return {"items": items, "total": len(items)}


@router.put("/sip-trunks/{trunk_id}", response_model=SipTrunkResponse, summary="Update a SIP trunk")
def update_sip_trunk(trunk_id: uuid.UUID, body: SipTrunkUpdate, db: Session = Depends(get_db)):
    trunk = db.query(SipTrunk).filter(SipTrunk.id == trunk_id).first()
    if not trunk:
        raise HTTPException(status_code=404, detail="SIP trunk not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(trunk, field, value)
    db.commit()
    db.refresh(trunk)
    return trunk


@router.delete("/sip-trunks/{trunk_id}", status_code=204, summary="Delete a SIP trunk")
def delete_sip_trunk(trunk_id: uuid.UUID, db: Session = Depends(get_db)):
    trunk = db.query(SipTrunk).filter(SipTrunk.id == trunk_id).first()
    if not trunk:
        raise HTTPException(status_code=404, detail="SIP trunk not found")
    db.delete(trunk)
    db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# PBX Nodes
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/accounts/{account_id}/pbx-nodes",
    response_model=PbxNodeResponse,
    status_code=201,
    summary="Create a PBX node",
)
def create_pbx_node(account_id: uuid.UUID, body: PbxNodeCreate, db: Session = Depends(get_db)):
    _get_account(db, account_id)
    node = PbxNode(cuenta_id=account_id)
    for field, value in body.model_dump().items():
        setattr(node, field, value)
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


@router.get(
    "/accounts/{account_id}/pbx-nodes",
    response_model=PbxNodeListResponse,
    summary="List PBX nodes",
)
def list_pbx_nodes(account_id: uuid.UUID, db: Session = Depends(get_db)):
    _get_account(db, account_id)
    items = db.query(PbxNode).filter(PbxNode.cuenta_id == account_id).order_by(PbxNode.created_at).all()
    return {"items": items, "total": len(items)}


@router.put("/pbx-nodes/{node_id}", response_model=PbxNodeResponse, summary="Update a PBX node")
def update_pbx_node(node_id: uuid.UUID, body: PbxNodeUpdate, db: Session = Depends(get_db)):
    node = db.query(PbxNode).filter(PbxNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="PBX node not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(node, field, value)
    db.commit()
    db.refresh(node)
    return node


@router.delete("/pbx-nodes/{node_id}", status_code=204, summary="Delete a PBX node")
def delete_pbx_node(node_id: uuid.UUID, db: Session = Depends(get_db)):
    node = db.query(PbxNode).filter(PbxNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="PBX node not found")
    db.delete(node)
    db.commit()


@router.post("/pbx-nodes/{node_id}/health-check", summary="Check PBX node health")
def check_pbx_node_health(node_id: uuid.UUID, db: Session = Depends(get_db)):
    node = db.query(PbxNode).filter(PbxNode.id == node_id).first()
    if not node:
        raise HTTPException(status_code=404, detail="PBX node not found")
    result = ami_manager.check_pbx_health(node)
    node.last_health_check = datetime.now(timezone.utc)
    node.health_status = result["status"]
    db.commit()
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Agents
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/accounts/{account_id}/agents",
    response_model=AgentResponse,
    status_code=201,
    summary="Create an agent",
)
def create_agent(account_id: uuid.UUID, body: AgentCreate, db: Session = Depends(get_db)):
    _get_account(db, account_id)
    # Check extension uniqueness within account
    existing = db.query(Agent).filter(
        Agent.cuenta_id == account_id, Agent.extension == body.extension
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Extension already in use in this account")
    agent = Agent(cuenta_id=account_id)
    for field, value in body.model_dump().items():
        setattr(agent, field, value)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.get(
    "/accounts/{account_id}/agents",
    response_model=AgentListResponse,
    summary="List agents",
)
def list_agents(account_id: uuid.UUID, db: Session = Depends(get_db)):
    _get_account(db, account_id)
    items = db.query(Agent).filter(Agent.cuenta_id == account_id).order_by(Agent.created_at).all()
    return {"items": items, "total": len(items)}


@router.get("/agents/{agent_id}", response_model=AgentResponse, summary="Get agent details")
def get_agent(agent_id: uuid.UUID, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.put("/agents/{agent_id}", response_model=AgentResponse, summary="Update an agent")
def update_agent(agent_id: uuid.UUID, body: AgentUpdate, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    update_data = body.model_dump(exclude_unset=True)
    if "extension" in update_data:
        existing = db.query(Agent).filter(
            Agent.cuenta_id == agent.cuenta_id,
            Agent.extension == update_data["extension"],
            Agent.id != agent_id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Extension already in use")
    for field, value in update_data.items():
        setattr(agent, field, value)
    db.commit()
    db.refresh(agent)
    return agent


@router.put("/agents/{agent_id}/status", response_model=AgentResponse, summary="Update agent status")
def update_agent_status(agent_id: uuid.UUID, body: AgentStatusUpdate, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    valid_states = {s.value for s in AgentStatus}
    if body.estado not in valid_states:
        raise HTTPException(status_code=400, detail=f"Invalid state. Must be one of: {', '.join(sorted(valid_states))}")
    agent.estado = body.estado
    agent.pause_reason = body.pause_reason if body.estado == AgentStatus.PAUSED.value else None
    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/agents/{agent_id}", status_code=204, summary="Delete an agent")
def delete_agent(agent_id: uuid.UUID, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    db.delete(agent)
    db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# Dispositions
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/accounts/{account_id}/dispositions",
    response_model=DispositionResponse,
    status_code=201,
    summary="Create a disposition",
)
def create_disposition(account_id: uuid.UUID, body: DispositionCreate, db: Session = Depends(get_db)):
    _get_account(db, account_id)
    existing = db.query(Disposition).filter(
        Disposition.cuenta_id == account_id, Disposition.codigo == body.codigo
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Disposition code already exists")
    disposition = Disposition(cuenta_id=account_id)
    for field, value in body.model_dump().items():
        setattr(disposition, field, value)
    db.add(disposition)
    db.commit()
    db.refresh(disposition)
    return disposition


@router.get(
    "/accounts/{account_id}/dispositions",
    response_model=DispositionListResponse,
    summary="List dispositions",
)
def list_dispositions(account_id: uuid.UUID, db: Session = Depends(get_db)):
    _get_account(db, account_id)
    items = db.query(Disposition).filter(Disposition.cuenta_id == account_id).order_by(Disposition.created_at).all()
    return {"items": items, "total": len(items)}


@router.put("/dispositions/{disposition_id}", response_model=DispositionResponse, summary="Update a disposition")
def update_disposition(disposition_id: uuid.UUID, body: DispositionUpdate, db: Session = Depends(get_db)):
    d = db.query(Disposition).filter(Disposition.id == disposition_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Disposition not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(d, field, value)
    db.commit()
    db.refresh(d)
    return d


@router.delete("/dispositions/{disposition_id}", status_code=204, summary="Delete a disposition")
def delete_disposition(disposition_id: uuid.UUID, db: Session = Depends(get_db)):
    d = db.query(Disposition).filter(Disposition.id == disposition_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Disposition not found")
    db.delete(d)
    db.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# Campaigns
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/accounts/{account_id}/campaigns",
    response_model=CampaignResponse,
    status_code=201,
    summary="Create a campaign",
)
def create_campaign(account_id: uuid.UUID, body: CampaignCreate, db: Session = Depends(get_db)):
    _get_account(db, account_id)
    campaign = Campaign(cuenta_id=account_id)
    for field, value in body.model_dump().items():
        setattr(campaign, field, value)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get(
    "/accounts/{account_id}/campaigns",
    response_model=CampaignListResponse,
    summary="List campaigns",
)
def list_campaigns(account_id: uuid.UUID, db: Session = Depends(get_db)):
    _get_account(db, account_id)
    items = db.query(Campaign).filter(Campaign.cuenta_id == account_id).order_by(Campaign.created_at.desc()).all()
    return {"items": items, "total": len(items)}


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse, summary="Get campaign details")
def get_campaign(campaign_id: uuid.UUID, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse, summary="Update a campaign")
def update_campaign(campaign_id: uuid.UUID, body: CampaignUpdate, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.estado == CampaignStatus.RUNNING.value:
        raise HTTPException(status_code=400, detail="Cannot update a running campaign. Pause it first.")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(campaign, field, value)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.delete("/campaigns/{campaign_id}", status_code=204, summary="Delete a campaign")
def delete_campaign(campaign_id: uuid.UUID, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.estado == CampaignStatus.RUNNING.value:
        raise HTTPException(status_code=400, detail="Cannot delete a running campaign")
    db.delete(campaign)
    db.commit()


# ─── Campaign state transitions ──────────────────────────────────────────────

@router.post("/campaigns/{campaign_id}/start", response_model=CampaignResponse, summary="Start a campaign")
def start_campaign(campaign_id: uuid.UUID, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.estado not in (CampaignStatus.DRAFT.value, CampaignStatus.PAUSED.value, CampaignStatus.STOPPED.value):
        raise HTTPException(status_code=400, detail=f"Cannot start campaign in state '{campaign.estado}'")
    # Validate requirements
    if campaign.dialer_mode != "manual":
        agents_count = db.query(CampaignAgent).filter(CampaignAgent.campaign_id == campaign_id).count()
        if agents_count == 0:
            raise HTTPException(status_code=400, detail="Assign at least one agent before starting")
    leads_count = db.query(CampaignLead).filter(CampaignLead.campaign_id == campaign_id).count()
    if leads_count == 0:
        raise HTTPException(status_code=400, detail="Add at least one lead before starting")
    campaign.estado = CampaignStatus.RUNNING.value
    update_campaign_stats(db, campaign_id)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.post("/campaigns/{campaign_id}/pause", response_model=CampaignResponse, summary="Pause a campaign")
def pause_campaign(campaign_id: uuid.UUID, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.estado != CampaignStatus.RUNNING.value:
        raise HTTPException(status_code=400, detail="Campaign is not running")
    campaign.estado = CampaignStatus.PAUSED.value
    db.commit()
    db.refresh(campaign)
    return campaign


@router.post("/campaigns/{campaign_id}/stop", response_model=CampaignResponse, summary="Stop a campaign")
def stop_campaign(campaign_id: uuid.UUID, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.estado not in (CampaignStatus.RUNNING.value, CampaignStatus.PAUSED.value):
        raise HTTPException(status_code=400, detail="Campaign is not running or paused")
    campaign.estado = CampaignStatus.STOPPED.value
    db.commit()
    db.refresh(campaign)
    return campaign


# ─── Campaign Agents ──────────────────────────────────────────────────────────

@router.post(
    "/campaigns/{campaign_id}/agents/{agent_id}",
    status_code=201,
    summary="Assign agent to campaign",
)
def assign_agent_to_campaign(
    campaign_id: uuid.UUID,
    agent_id: uuid.UUID,
    prioridad: int = 0,
    db: Session = Depends(get_db),
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.cuenta_id == campaign.cuenta_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found in this account")
    existing = db.query(CampaignAgent).filter(
        CampaignAgent.campaign_id == campaign_id, CampaignAgent.agent_id == agent_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Agent already assigned to this campaign")
    ca = CampaignAgent(campaign_id=campaign_id, agent_id=agent_id, prioridad=prioridad)
    db.add(ca)
    db.commit()
    return {"message": "Agent assigned", "campaign_id": campaign_id, "agent_id": agent_id}


@router.delete(
    "/campaigns/{campaign_id}/agents/{agent_id}",
    status_code=204,
    summary="Remove agent from campaign",
)
def remove_agent_from_campaign(campaign_id: uuid.UUID, agent_id: uuid.UUID, db: Session = Depends(get_db)):
    ca = db.query(CampaignAgent).filter(
        CampaignAgent.campaign_id == campaign_id, CampaignAgent.agent_id == agent_id
    ).first()
    if not ca:
        raise HTTPException(status_code=404, detail="Agent not assigned to this campaign")
    db.delete(ca)
    db.commit()


@router.get("/campaigns/{campaign_id}/agents", summary="List agents assigned to campaign")
def list_campaign_agents(campaign_id: uuid.UUID, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    cas = (
        db.query(CampaignAgent)
        .filter(CampaignAgent.campaign_id == campaign_id)
        .order_by(CampaignAgent.prioridad)
        .all()
    )
    items = []
    for ca in cas:
        agent = db.query(Agent).filter(Agent.id == ca.agent_id).first()
        if agent:
            items.append({
                "agent_id": agent.id,
                "nombre": agent.nombre,
                "extension": agent.extension,
                "estado": agent.estado,
                "prioridad": ca.prioridad,
            })
    return {"items": items, "total": len(items)}


# ─── Campaign Leads ──────────────────────────────────────────────────────────

@router.post(
    "/campaigns/{campaign_id}/leads",
    response_model=CampaignLeadResponse,
    status_code=201,
    summary="Add a lead to a campaign",
)
def add_campaign_lead(campaign_id: uuid.UUID, body: CampaignLeadAdd, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    lead = db.query(Lead).filter(Lead.id == body.lead_id, Lead.cuenta_id == campaign.cuenta_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found in this account")
    existing = db.query(CampaignLead).filter(
        CampaignLead.campaign_id == campaign_id, CampaignLead.lead_id == body.lead_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Lead already in this campaign")
    # Check DNC
    is_dnc = db.query(DncEntry).filter(
        DncEntry.cuenta_id == campaign.cuenta_id, DncEntry.telefono == body.telefono
    ).first()
    cl = CampaignLead(
        campaign_id=campaign_id,
        lead_id=body.lead_id,
        telefono=body.telefono,
        estado=CampaignLeadStatus.DNC.value if is_dnc else CampaignLeadStatus.PENDING.value,
    )
    db.add(cl)
    update_campaign_stats(db, campaign_id)
    db.commit()
    db.refresh(cl)
    return cl


@router.post(
    "/campaigns/{campaign_id}/leads/bulk",
    summary="Bulk add leads from a lead base or lote",
)
def bulk_add_campaign_leads(campaign_id: uuid.UUID, body: CampaignLeadBulkAdd, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Get leads from source
    query = db.query(Lead).filter(Lead.cuenta_id == campaign.cuenta_id)
    if body.source_type == "lead_base":
        query = query.filter(Lead.lead_base_id == body.source_id)
    elif body.source_type == "lote":
        query = query.filter(Lead.lote_id == body.source_id)
    else:
        raise HTTPException(status_code=400, detail="source_type must be 'lead_base' or 'lote'")

    leads = query.all()
    if not leads:
        raise HTTPException(status_code=404, detail="No leads found in the specified source")

    # Load existing campaign leads to avoid duplicates
    existing_lead_ids = set(
        row[0] for row in
        db.query(CampaignLead.lead_id).filter(CampaignLead.campaign_id == campaign_id).all()
    )

    # Load DNC numbers
    dnc_numbers = set(
        row[0] for row in
        db.query(DncEntry.telefono).filter(DncEntry.cuenta_id == campaign.cuenta_id).all()
    )

    added = 0
    skipped = 0
    dnc_count = 0

    for lead in leads:
        if lead.id in existing_lead_ids:
            skipped += 1
            continue

        # Extract phone from datos
        telefono = None
        if lead.datos and isinstance(lead.datos, dict):
            telefono = lead.datos.get(body.campo_telefono)
        if not telefono:
            skipped += 1
            continue

        telefono = str(telefono).strip()
        is_dnc = telefono in dnc_numbers

        cl = CampaignLead(
            campaign_id=campaign_id,
            lead_id=lead.id,
            telefono=telefono,
            estado=CampaignLeadStatus.DNC.value if is_dnc else CampaignLeadStatus.PENDING.value,
        )
        db.add(cl)
        if is_dnc:
            dnc_count += 1
        else:
            added += 1

    update_campaign_stats(db, campaign_id)
    db.commit()

    return {"added": added, "skipped": skipped, "dnc": dnc_count, "total_processed": len(leads)}


@router.get(
    "/campaigns/{campaign_id}/leads",
    response_model=CampaignLeadListResponse,
    summary="List campaign leads",
)
def list_campaign_leads(
    campaign_id: uuid.UUID,
    estado: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    query = db.query(CampaignLead).filter(CampaignLead.campaign_id == campaign_id)
    if estado:
        query = query.filter(CampaignLead.estado == estado)
    total = query.count()
    items = query.order_by(CampaignLead.created_at).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total}


@router.post(
    "/campaign-leads/{cl_id}/disposition",
    response_model=CampaignLeadResponse,
    summary="Set disposition on a campaign lead",
)
def set_campaign_lead_disposition(
    cl_id: uuid.UUID,
    body: CampaignLeadDisposition,
    db: Session = Depends(get_db),
):
    cl = db.query(CampaignLead).filter(CampaignLead.id == cl_id).first()
    if not cl:
        raise HTTPException(status_code=404, detail="Campaign lead not found")
    disposition = db.query(Disposition).filter(Disposition.id == body.disposition_id).first()
    if not disposition:
        raise HTTPException(status_code=404, detail="Disposition not found")

    cl.disposition_id = disposition.id
    cl.disposition_nota = body.nota

    if disposition.requiere_reagendamiento and body.callback_at:
        cl.callback_at = body.callback_at
        cl.estado = CampaignLeadStatus.SCHEDULED.value
    elif disposition.es_final:
        cl.estado = CampaignLeadStatus.COMPLETED.value
    elif disposition.es_contacto:
        cl.estado = CampaignLeadStatus.CONTACTED.value
    else:
        cl.estado = CampaignLeadStatus.CONTACTED.value

    # Also update the call record if agent has an active call
    if cl.assigned_agent_id:
        agent = db.query(Agent).filter(Agent.id == cl.assigned_agent_id).first()
        if agent and agent.current_call_id:
            call = db.query(CallRecord).filter(CallRecord.id == agent.current_call_id).first()
            if call:
                call.disposition_id = disposition.id
                call.disposition_nota = body.nota
                db.add(CallEvent(
                    call_record_id=call.id,
                    evento="disposition",
                    detalle={"disposition_code": disposition.codigo, "nota": body.nota},
                ))

    update_campaign_stats(db, cl.campaign_id)
    db.commit()
    db.refresh(cl)
    return cl


# ─── Campaign Stats ──────────────────────────────────────────────────────────

@router.get(
    "/campaigns/{campaign_id}/stats",
    response_model=CampaignStatsResponse,
    summary="Get campaign statistics",
)
def get_campaign_stats(campaign_id: uuid.UUID, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    def _count_estado(estado: str) -> int:
        return db.query(func.count(CampaignLead.id)).filter(
            CampaignLead.campaign_id == campaign_id, CampaignLead.estado == estado
        ).scalar() or 0

    total = db.query(func.count(CampaignLead.id)).filter(
        CampaignLead.campaign_id == campaign_id
    ).scalar() or 0

    pending = _count_estado(CampaignLeadStatus.PENDING.value)
    contacted = _count_estado(CampaignLeadStatus.CONTACTED.value)
    no_answer = _count_estado(CampaignLeadStatus.NO_ANSWER.value)
    busy = _count_estado(CampaignLeadStatus.BUSY.value)
    failed = _count_estado(CampaignLeadStatus.FAILED.value)
    completed = _count_estado(CampaignLeadStatus.COMPLETED.value)
    dialing = _count_estado(CampaignLeadStatus.DIALING.value)

    # Available agents
    agent_ids = [row[0] for row in db.query(CampaignAgent.agent_id).filter(
        CampaignAgent.campaign_id == campaign_id
    ).all()]
    available_agents = db.query(func.count(Agent.id)).filter(
        Agent.id.in_(agent_ids), Agent.estado == AgentStatus.AVAILABLE.value
    ).scalar() or 0 if agent_ids else 0

    # ASR (answered / total attempted)
    total_attempted = contacted + no_answer + busy + failed + completed
    asr = (contacted + completed) / total_attempted if total_attempted > 0 else None

    # AHT (average handle time from call records)
    avg_billsec = db.query(func.avg(CallRecord.billsec)).filter(
        CallRecord.campaign_id == campaign_id, CallRecord.billsec > 0
    ).scalar()
    aht = float(avg_billsec) if avg_billsec else None

    contact_rate = (contacted + completed) / total if total > 0 else None

    return CampaignStatsResponse(
        campaign_id=campaign_id,
        estado=campaign.estado,
        total_leads=total,
        leads_pending=pending,
        leads_contacted=contacted,
        leads_no_answer=no_answer,
        leads_busy=busy,
        leads_failed=failed,
        leads_completed=completed,
        active_calls=dialing,
        available_agents=available_agents,
        asr=asr,
        aht=aht,
        contact_rate=contact_rate,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Dialer / Call Control
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/campaigns/{campaign_id}/manual-call",
    response_model=ManualCallResponse,
    summary="Manual click-to-call",
)
def make_manual_call(campaign_id: uuid.UUID, body: ManualCallRequest, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    result = manual_call(
        db,
        cuenta_id=campaign.cuenta_id,
        agent_id=body.agent_id,
        campaign_lead_id=body.campaign_lead_id,
    )

    return ManualCallResponse(
        call_id=result.call_record_id or uuid.uuid4(),
        uniqueid=result.uniqueid,
        status="success" if result.success else "error",
        message=result.message,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Call Records (CDR)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/accounts/{account_id}/call-records",
    response_model=CallRecordListResponse,
    summary="List call records (CDR)",
)
def list_call_records(
    account_id: uuid.UUID,
    campaign_id: uuid.UUID | None = None,
    agent_id: uuid.UUID | None = None,
    resultado: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    _get_account(db, account_id)
    query = db.query(CallRecord).filter(CallRecord.cuenta_id == account_id)
    if campaign_id:
        query = query.filter(CallRecord.campaign_id == campaign_id)
    if agent_id:
        query = query.filter(CallRecord.agent_id == agent_id)
    if resultado:
        query = query.filter(CallRecord.resultado == resultado)
    total = query.count()
    items = query.order_by(CallRecord.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total}


@router.get("/call-records/{record_id}", response_model=CallRecordResponse, summary="Get call record details")
def get_call_record(record_id: uuid.UUID, db: Session = Depends(get_db)):
    record = db.query(CallRecord).filter(CallRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Call record not found")
    return record


@router.get("/call-records/{record_id}/events", summary="Get call events timeline")
def get_call_events(record_id: uuid.UUID, db: Session = Depends(get_db)):
    record = db.query(CallRecord).filter(CallRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Call record not found")
    events = db.query(CallEvent).filter(
        CallEvent.call_record_id == record_id
    ).order_by(CallEvent.timestamp).all()
    return {"items": [CallEventResponse.model_validate(e) for e in events], "total": len(events)}


# ═══════════════════════════════════════════════════════════════════════════════
# DNC (Do Not Call)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/accounts/{account_id}/dnc",
    response_model=DncResponse,
    status_code=201,
    summary="Add number to DNC list",
)
def add_dnc(account_id: uuid.UUID, body: DncCreate, db: Session = Depends(get_db)):
    _get_account(db, account_id)
    existing = db.query(DncEntry).filter(
        DncEntry.cuenta_id == account_id, DncEntry.telefono == body.telefono
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Number already in DNC list")
    dnc = DncEntry(cuenta_id=account_id, telefono=body.telefono, motivo=body.motivo)
    db.add(dnc)
    db.commit()
    db.refresh(dnc)
    return dnc


@router.get(
    "/accounts/{account_id}/dnc",
    response_model=DncListResponse,
    summary="List DNC entries",
)
def list_dnc(
    account_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    _get_account(db, account_id)
    query = db.query(DncEntry).filter(DncEntry.cuenta_id == account_id)
    total = query.count()
    items = query.order_by(DncEntry.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total}


@router.delete("/dnc/{dnc_id}", status_code=204, summary="Remove number from DNC list")
def remove_dnc(dnc_id: uuid.UUID, db: Session = Depends(get_db)):
    dnc = db.query(DncEntry).filter(DncEntry.id == dnc_id).first()
    if not dnc:
        raise HTTPException(status_code=404, detail="DNC entry not found")
    db.delete(dnc)
    db.commit()
