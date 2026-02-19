from app.models.account import Account
from app.models.automation import Automation, AutomationAction, AutomationCondition, AutomationLog
from app.models.field import CustomField, FieldType
from app.models.lead import Lead
from app.models.lead_base import LeadBase
from app.models.lote import Lote
from app.models.record import Record
from app.models.role import Role
from app.models.ui_module import UIModule, RoleModulePermission
from app.models.tipificacion import Tipificacion, Subtipificacion
from app.models.campaign import (
    Campania, CampaniaAgente, CampaniaBase, ColaLead, AgenteCampaniaLog,
    TipoDiscador, EstadoCampania, EstadoCola, EstadoAgenteEnCampania,
)
from app.models.crm_extras import Actividad, Tarea, Nota, AuditLog, Tag, LeadTag
from app.models.routing_rule import RoutingRule
from app.models.user import User
from app.models.voip import (
    Agent, CallEvent, CallRecord, Campaign as VoipCampaign, CampaignAgent, CampaignLead,
    Disposition, DncEntry, PbxNode, SipProvider, SipTrunk,
)
from app.models.webhook import Webhook, WebhookLog

__all__ = [
    # Campaigns (Nuevo)
    "Campania", "CampaniaAgente", "CampaniaBase", "ColaLead", "AgenteCampaniaLog",
    "TipoDiscador", "EstadoCampania", "EstadoCola", "EstadoAgenteEnCampania",
    # VoIP
    "Agent", "CallEvent", "CallRecord", "VoipCampaign", "CampaignAgent", "CampaignLead",
    "Disposition", "DncEntry", "PbxNode", "SipProvider", "SipTrunk",
    # Core
    "Account", "Actividad", "Agent", "AuditLog", "Automation", "AutomationAction", "AutomationCondition", "AutomationLog",
    "CallEvent", "CallRecord", "CustomField", "Disposition", "DncEntry", "FieldType",
    "Lead", "LeadBase", "LeadTag", "Lote", "Nota", "Record",
    "Role", "RoleModulePermission", "RoutingRule", "Subtipificacion", "Tag", "Tarea", 
    "Tipificacion", "UIModule", "User", "Webhook", "WebhookLog",
]
