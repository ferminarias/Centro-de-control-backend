"""
Tests for performance (N+1 queries, etc.).
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session


class TestNPlusOneQueries:
    """Test for N+1 query problems."""
    
    def test_list_leads_no_n_plus_one(
        self, client: TestClient, test_account, auth_headers, db_session
    ):
        """Test that listing leads doesn't cause N+1 queries."""
        from app.models.lead import Lead
        
        # Create multiple leads
        for i in range(10):
            lead = Lead(
                cuenta_id=test_account.id,
                datos={"nombre": f"Lead {i}", "email": f"lead{i}@test.com"}
            )
            db_session.add(lead)
        db_session.commit()
        
        # Count queries
        queries = []
        
        @event.listens_for(db_session.bind, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            queries.append(statement)
        
        # Make request
        response = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/leads",
            headers=auth_headers
        )
        
        # Remove listener
        event.remove(db_session.bind, "before_cursor_execute", before_cursor_execute)
        
        assert response.status_code == 200
        
        # Should have ~2-3 queries (count + select + maybe one join)
        # Not 1 + 10 = 11 queries (which would indicate N+1)
        assert len(queries) < 5, f"Too many queries ({len(queries)}), possible N+1 problem"
    
    def test_campaign_list_with_leads_no_n_plus_one(
        self, client: TestClient, test_account, auth_headers, db_session
    ):
        """Test that campaign with leads doesn't cause N+1."""
        from app.models.campaign import Campania, ColaLead
        from app.models.lead import Lead
        
        # Create campaign
        campaign = Campania(
            cuenta_id=test_account.id,
            nombre="Test Campaign",
            estado="activa",
            tipo_discador="sin_discador"
        )
        db_session.add(campaign)
        db_session.flush()
        
        # Create leads and add to campaign queue
        for i in range(5):
            lead = Lead(
                cuenta_id=test_account.id,
                datos={"nombre": f"Lead {i}"}
            )
            db_session.add(lead)
            db_session.flush()
            
            cola = ColaLead(
                campania_id=campaign.id,
                lead_id=lead.id,
                estado="pendiente"
            )
            db_session.add(cola)
        
        db_session.commit()
        
        # Count queries
        queries = []
        
        @event.listens_for(db_session.bind, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            queries.append(statement)
        
        # Get campaign with leads
        response = client.get(
            f"/api/v1/admin/campaigns/{campaign.id}/leads",
            headers=auth_headers
        )
        
        # Remove listener
        event.remove(db_session.bind, "before_cursor_execute", before_cursor_execute)
        
        assert response.status_code == 200
        
        # Should not have 1 query per lead
        assert len(queries) < 10, f"Too many queries ({len(queries)}), possible N+1"


class TestResponseTimes:
    """Test API response times."""
    
    def test_leads_list_response_time(
        self, client: TestClient, test_account, auth_headers
    ):
        """Test that leads list responds within acceptable time."""
        import time
        
        start = time.time()
        response = client.get(
            f"/api/v1/admin/accounts/{test_account.id}/leads",
            headers=auth_headers
        )
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 1.0, f"Response too slow: {duration}s"
    
    def test_ingest_response_time(
        self, client: TestClient, test_account
    ):
        """Test that ingestion responds within acceptable time."""
        import time
        
        payload = {"nombre": "Test", "email": "test@test.com"}
        
        start = time.time()
        response = client.post(
            f"/api/v1/ingest/{test_account.api_key}",
            json=payload
        )
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 2.0, f"Ingest too slow: {duration}s"
