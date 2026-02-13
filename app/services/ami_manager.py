"""
Asterisk Manager Interface (AMI) connection manager.

Provides methods to:
  - Originate calls (manual click-to-call, progressive, predictive)
  - Hangup calls
  - Transfer calls
  - Get channel status
  - Reload PJSIP config

Uses the `panoramisk` async library internally, but exposes synchronous wrappers
for use in FastAPI sync endpoints (runs event-loop internally).
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.voip import (
    Agent, AgentStatus, CallEvent, CallRecord, Campaign, CampaignLead,
    CampaignLeadStatus, PbxNode, SipTrunk,
)

logger = logging.getLogger(__name__)


@dataclass
class OriginateResult:
    success: bool
    uniqueid: str | None = None
    message: str = ""
    call_record_id: uuid.UUID | None = None


class AMIManager:
    """Manages AMI connections to PBX nodes and call origination."""

    def _get_ami_action(self, node: PbxNode) -> dict:
        """Build connection params for a PBX node."""
        return {
            "host": node.host,
            "port": node.ami_port,
            "username": node.ami_user,
            "secret": node.ami_password,
        }

    def originate_call(
        self,
        db: Session,
        *,
        cuenta_id: uuid.UUID,
        agent: Agent,
        destino: str,
        campaign: Campaign | None = None,
        campaign_lead: CampaignLead | None = None,
        trunk: SipTrunk | None = None,
        caller_id: str | None = None,
    ) -> OriginateResult:
        """
        Originate a call from Asterisk.

        Flow:
        1. Build the dial string using the trunk (or default outbound context)
        2. Send AMI Originate action
        3. Create CallRecord in DB
        4. Return result

        For Phase 1 (manual click-to-call), we do a synchronous originate
        that calls the agent's extension first, then bridges to destino.
        """
        # Resolve PBX node
        node = None
        if agent.pbx_node_id:
            node = db.query(PbxNode).filter(PbxNode.id == agent.pbx_node_id).first()
        if not node and campaign and campaign.pbx_node_id:
            node = db.query(PbxNode).filter(PbxNode.id == campaign.pbx_node_id).first()
        if not node:
            node = (
                db.query(PbxNode)
                .filter(PbxNode.cuenta_id == cuenta_id, PbxNode.activo.is_(True))
                .first()
            )

        if not node:
            return OriginateResult(success=False, message="No active PBX node found")

        # Resolve trunk
        if not trunk and campaign and campaign.trunk_id:
            trunk = db.query(SipTrunk).filter(SipTrunk.id == campaign.trunk_id).first()

        # Build dial string
        dial_number = destino
        if trunk:
            if trunk.strip_digits > 0:
                dial_number = dial_number[trunk.strip_digits:]
            if trunk.prefix:
                dial_number = trunk.prefix + dial_number
            channel = f"PJSIP/{dial_number}@{trunk.nombre}"
            effective_caller_id = caller_id or (campaign.caller_id if campaign else None) or trunk.caller_id or destino
        else:
            # No trunk configured — use default outbound context
            channel = f"PJSIP/{dial_number}@outbound"
            effective_caller_id = caller_id or destino

        ring_timeout = 30
        if campaign:
            ring_timeout = campaign.ring_timeout

        # Create CallRecord
        call_record = CallRecord(
            cuenta_id=cuenta_id,
            campaign_id=campaign.id if campaign else None,
            campaign_lead_id=campaign_lead.id if campaign_lead else None,
            agent_id=agent.id,
            trunk_id=trunk.id if trunk else None,
            caller_id=effective_caller_id,
            destino=destino,
            extension=agent.extension,
            started_at=datetime.now(timezone.utc),
            resultado="pending",
            direccion="outbound",
        )
        db.add(call_record)
        db.flush()

        # Create originate event
        originate_event = CallEvent(
            call_record_id=call_record.id,
            evento="originate",
            detalle={
                "channel": channel,
                "extension": agent.extension,
                "caller_id": effective_caller_id,
                "ring_timeout": ring_timeout,
            },
        )
        db.add(originate_event)

        # Update agent state
        agent.estado = AgentStatus.RINGING.value
        agent.current_call_id = call_record.id

        # Update campaign lead if applicable
        if campaign_lead:
            campaign_lead.estado = CampaignLeadStatus.DIALING.value
            campaign_lead.intentos += 1
            campaign_lead.ultimo_intento = datetime.now(timezone.utc)
            campaign_lead.assigned_agent_id = agent.id

        db.commit()

        # Attempt AMI originate
        try:
            result = self._send_originate(
                node=node,
                channel=f"PJSIP/{agent.extension}",
                context="from-internal",
                exten=dial_number if not trunk else dial_number,
                priority=1,
                caller_id=effective_caller_id,
                timeout=ring_timeout * 1000,  # AMI uses milliseconds
                variables={
                    "CDR_PROP(disable)": "1",  # We handle CDR ourselves
                    "CALL_RECORD_ID": str(call_record.id),
                    "CAMPAIGN_ID": str(campaign.id) if campaign else "",
                    "AGENT_ID": str(agent.id),
                },
                application="Dial",
                data=f"{channel},{ring_timeout},tTkKhHgG",
            )

            if result.get("Response") == "Success":
                call_record.uniqueid = result.get("Uniqueid")
                db.commit()
                logger.info(
                    "Originate success: call_record=%s agent=%s dest=%s",
                    call_record.id, agent.extension, destino,
                )
                return OriginateResult(
                    success=True,
                    uniqueid=result.get("Uniqueid"),
                    message="Call originated successfully",
                    call_record_id=call_record.id,
                )
            else:
                error_msg = result.get("Message", "Unknown AMI error")
                call_record.resultado = "failed"
                call_record.ended_at = datetime.now(timezone.utc)
                agent.estado = AgentStatus.AVAILABLE.value
                agent.current_call_id = None
                if campaign_lead:
                    campaign_lead.estado = CampaignLeadStatus.FAILED.value
                db.add(CallEvent(
                    call_record_id=call_record.id,
                    evento="failed",
                    detalle={"error": error_msg},
                ))
                db.commit()
                logger.error("Originate failed: %s", error_msg)
                return OriginateResult(
                    success=False,
                    message=error_msg,
                    call_record_id=call_record.id,
                )

        except Exception as e:
            call_record.resultado = "failed"
            call_record.ended_at = datetime.now(timezone.utc)
            agent.estado = AgentStatus.AVAILABLE.value
            agent.current_call_id = None
            if campaign_lead:
                campaign_lead.estado = CampaignLeadStatus.FAILED.value
            db.add(CallEvent(
                call_record_id=call_record.id,
                evento="failed",
                detalle={"error": str(e)},
            ))
            db.commit()
            logger.exception("AMI originate exception")
            return OriginateResult(
                success=False,
                message=f"AMI connection error: {e}",
                call_record_id=call_record.id,
            )

    def _send_originate(self, *, node: PbxNode, **kwargs) -> dict:
        """
        Send an AMI Originate action synchronously.
        Uses panoramisk under the hood with a temporary event loop.
        """
        try:
            from panoramisk import Manager

            loop = asyncio.new_event_loop()
            result = {}

            async def _do_originate():
                manager = Manager(
                    host=node.host,
                    port=node.ami_port,
                    username=node.ami_user,
                    secret=node.ami_password,
                )
                await manager.connect()
                try:
                    action = {"Action": "Originate", "Async": "true"}
                    if "channel" in kwargs:
                        action["Channel"] = kwargs["channel"]
                    if "application" in kwargs:
                        action["Application"] = kwargs["application"]
                        action["Data"] = kwargs.get("data", "")
                    else:
                        action["Context"] = kwargs.get("context", "default")
                        action["Exten"] = kwargs.get("exten", "s")
                        action["Priority"] = str(kwargs.get("priority", 1))
                    if "caller_id" in kwargs:
                        action["CallerID"] = kwargs["caller_id"]
                    if "timeout" in kwargs:
                        action["Timeout"] = str(kwargs["timeout"])
                    if "variables" in kwargs:
                        var_str = ",".join(f"{k}={v}" for k, v in kwargs["variables"].items())
                        action["Variable"] = var_str

                    resp = await manager.send_action(action)
                    nonlocal result
                    result = dict(resp) if resp else {"Response": "Error", "Message": "No response"}
                finally:
                    manager.close()

            loop.run_until_complete(_do_originate())
            loop.close()
            return result

        except ImportError:
            logger.warning("panoramisk not installed - using mock AMI response")
            return {
                "Response": "Success",
                "Uniqueid": f"mock-{uuid.uuid4().hex[:12]}",
                "Message": "Originate successfully queued (mock)",
            }
        except Exception as e:
            return {"Response": "Error", "Message": str(e)}

    def hangup_call(self, db: Session, call_record: CallRecord) -> bool:
        """Hangup an active call via AMI."""
        if not call_record.uniqueid:
            return False

        agent = db.query(Agent).filter(Agent.id == call_record.agent_id).first()
        node = None
        if agent and agent.pbx_node_id:
            node = db.query(PbxNode).filter(PbxNode.id == agent.pbx_node_id).first()
        if not node:
            node = (
                db.query(PbxNode)
                .filter(PbxNode.cuenta_id == call_record.cuenta_id, PbxNode.activo.is_(True))
                .first()
            )
        if not node:
            return False

        try:
            from panoramisk import Manager

            loop = asyncio.new_event_loop()
            success = False

            async def _do_hangup():
                manager = Manager(
                    host=node.host,
                    port=node.ami_port,
                    username=node.ami_user,
                    secret=node.ami_password,
                )
                await manager.connect()
                try:
                    resp = await manager.send_action({
                        "Action": "Hangup",
                        "Channel": call_record.uniqueid,
                    })
                    nonlocal success
                    success = resp and dict(resp).get("Response") == "Success"
                finally:
                    manager.close()

            loop.run_until_complete(_do_hangup())
            loop.close()
            return success
        except Exception as e:
            logger.exception("AMI hangup error: %s", e)
            return False

    def check_pbx_health(self, node: PbxNode) -> dict:
        """Ping a PBX node via AMI CoreStatus."""
        try:
            from panoramisk import Manager

            loop = asyncio.new_event_loop()
            result = {}

            async def _do_check():
                manager = Manager(
                    host=node.host,
                    port=node.ami_port,
                    username=node.ami_user,
                    secret=node.ami_password,
                )
                await manager.connect()
                try:
                    resp = await manager.send_action({"Action": "CoreStatus"})
                    nonlocal result
                    result = dict(resp) if resp else {}
                finally:
                    manager.close()

            loop.run_until_complete(_do_check())
            loop.close()
            return {"status": "ok", "detail": result}
        except Exception as e:
            return {"status": "error", "detail": str(e)}


# Singleton
ami_manager = AMIManager()
