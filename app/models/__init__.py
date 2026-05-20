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
from app.models.ficha_config import FichaConfig
from app.models.routing_rule import RoutingRule
from app.models.tipificacion_externa import TipificacionExterna
from app.models.user import User
from app.models.voip import (
    Agent, AgentStatus, CallEvent, CallRecord, CampaignAgent, CampaignLead,
    CampaignLeadStatus, CampaignStatus, DialerMode, Disposition, DncEntry, 
    PbxNode, SipProvider, SipTrunk,
)
from app.models.webhook import Webhook, WebhookLog
from app.prode.models import ProdeUser

__all__ = [
    # Campaigns (consolidado VoIP + Contact Center)
    "Campania", "CampaniaAgente", "CampaniaBase", "ColaLead", "AgenteCampaniaLog",
    "TipoDiscador", "EstadoCampania", "EstadoCola", "EstadoAgenteEnCampania",
    "CampaignAgent", "CampaignLead", "CampaignStatus", "CampaignLeadStatus", "DialerMode",
    # VoIP
    "Agent", "AgentStatus", "CallEvent", "CallRecord",
    "Disposition", "DncEntry", "PbxNode", "SipProvider", "SipTrunk",
    # Core
    "Account", "Actividad", "Agent", "AuditLog", "Automation", "AutomationAction", "AutomationCondition", "AutomationLog",
    "CallEvent", "CallRecord", "CustomField", "Disposition", "DncEntry", "FieldType",
    "FichaConfig",
    "Lead", "LeadBase", "LeadTag", "Lote", "Nota", "Record",
    "Role", "RoleModulePermission", "RoutingRule", "Subtipificacion", "Tag", "Tarea", 
    "Tipificacion", "TipificacionExterna", "UIModule", "User", "Webhook", "WebhookLog",
    "ProdeUser",
]
