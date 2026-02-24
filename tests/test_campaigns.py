"""
Tests for campaigns (consolidated VoIP + Contact Center).
"""
import pytest
from fastapi.testclient import TestClient


class TestCampaignCRUD:
    """Test campaign CRUD operations."""
    
    def test_create_campaign(self, client: TestClient, test_account, auth_headers):
        """Test creating a campaign."""
        response = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/campaigns",
            headers=auth_headers,
            json={
                "nombre": "Campaña de Prueba",
                "descripcion": "Descripción de prueba",
                "estado": "borrador",
                "tipo_discador": "sin_discador"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == "Campaña de Prueba"
        assert data["estado"] == "borrador"
        assert data["cuenta_id"] == str(test_account.id)
    
    def test_list_campaigns(self, client: TestClient, test_account, auth_headers):
        """Test listing campaigns."""
        # Create a campaign first
        client.post(
            f"/api/v1/admin/accounts/{test_account.id}/campaigns",
            headers=auth_headers,
            json={"nombre": "Test Campaign", "estado": "borrador", "tipo_discador": "sin_discador"}
        )
        
        response = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/campaigns",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) >= 1
    
    def test_update_campaign(self, client: TestClient, test_account, auth_headers):
        """Test updating a campaign."""
        # Create campaign
        create_resp = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/campaigns",
            headers=auth_headers,
            json={"nombre": "Original Name", "estado": "borrador", "tipo_discador": "sin_discador"}
        )
        campaign_id = create_resp.json()["id"]
        
        # Update it
        response = client.put(
            f"/api/v1/admin/campaigns/{campaign_id}",
            headers=auth_headers,
            json={"nombre": "Updated Name"}
        )
        
        assert response.status_code == 200
        assert response.json()["nombre"] == "Updated Name"
    
    def test_delete_campaign(self, client: TestClient, test_account, auth_headers):
        """Test deleting a campaign."""
        # Create campaign
        create_resp = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/campaigns",
            headers=auth_headers,
            json={"nombre": "To Delete", "estado": "borrador", "tipo_discador": "sin_discador"}
        )
        campaign_id = create_resp.json()["id"]
        
        # Delete it
        response = client.delete(
            f"/api/v1/admin/campaigns/{campaign_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204


class TestCampaignStateTransitions:
    """Test campaign state transitions."""
    
    def test_start_campaign(self, client: TestClient, test_account, auth_headers):
        """Test starting a campaign."""
        # Create campaign
        create_resp = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/campaigns",
            headers=auth_headers,
            json={"nombre": "Test", "estado": "borrador", "tipo_discador": "sin_discador"}
        )
        campaign_id = create_resp.json()["id"]
        
        # Start it
        response = client.post(
            f"/api/v1/admin/campaigns/{campaign_id}/start",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["estado"] == "activa"
    
    def test_pause_running_campaign(self, client: TestClient, test_account, auth_headers):
        """Test pausing a running campaign."""
        # Create and start campaign
        create_resp = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/campaigns",
            headers=auth_headers,
            json={"nombre": "Test", "estado": "borrador", "tipo_discador": "sin_discador"}
        )
        campaign_id = create_resp.json()["id"]
        
        client.post(
            f"/api/v1/admin/campaigns/{campaign_id}/start",
            headers=auth_headers
        )
        
        # Pause it
        response = client.post(
            f"/api/v1/admin/campaigns/{campaign_id}/pause",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["estado"] == "pausada"
    
    def test_cannot_update_running_campaign(self, client: TestClient, test_account, auth_headers):
        """Test that running campaigns cannot be updated."""
        # Create and start campaign
        create_resp = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/campaigns",
            headers=auth_headers,
            json={"nombre": "Test", "estado": "borrador", "tipo_discador": "sin_discador"}
        )
        campaign_id = create_resp.json()["id"]
        
        client.post(
            f"/api/v1/admin/campaigns/{campaign_id}/start",
            headers=auth_headers
        )
        
        # Try to update
        response = client.put(
            f"/api/v1/admin/campaigns/{campaign_id}",
            headers=auth_headers,
            json={"nombre": "New Name"}
        )
        
        assert response.status_code == 400


class TestCampaignVoIPFields:
    """Test VoIP-specific campaign fields."""
    
    def test_create_campaign_with_trunk(
        self, client: TestClient, test_account, auth_headers, db_session
    ):
        """Test creating campaign with SIP trunk."""
        from app.models.voip import SipProvider, SipTrunk
        
        # Create provider and trunk
        provider = SipProvider(
            cuenta_id=test_account.id,
            nombre="Test Provider",
            activo=True
        )
        db_session.add(provider)
        db_session.flush()
        
        trunk = SipTrunk(
            cuenta_id=test_account.id,
            provider_id=provider.id,
            nombre="Test Trunk",
            host="sip.test.com",
            activo=True
        )
        db_session.add(trunk)
        db_session.commit()
        
        # Create campaign with trunk
        response = client.post(
            f"/api/v1/admin/accounts/{test_account.id}/campaigns",
            headers=auth_headers,
            json={
                "nombre": "VoIP Campaign",
                "estado": "borrador",
                "tipo_discador": "progresivo",
                "trunk_id": str(trunk.id),
                "caller_id": "541111111111",
                "max_concurrent_calls": 10,
                "ring_timeout": 45
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["caller_id"] == "541111111111"
        assert data["max_concurrent_calls"] == 10
