"""Mock enterprise tools used by the sample agent."""
from __future__ import annotations

# These are mock implementations. In a real deployment they would call actual enterprise APIs.

MOCK_CUSTOMERS = {
    "C-12345": {"id": "C-12345", "name": "Alice Smith", "email": "alice@example.com", "tier": "premium"},
    "C-99999": {"id": "C-99999", "name": "Bob Jones", "email": "bob@example.com", "tier": "standard"},
}


def query_customer_db(customer_id: str) -> dict:
    customer = MOCK_CUSTOMERS.get(customer_id)
    if not customer:
        return {"error": f"Customer {customer_id} not found"}
    return customer


def send_email(to: str, subject: str, body: str) -> dict:
    print(f"[MOCK EMAIL] To: {to} | Subject: {subject} | Body: {body[:80]}...")
    return {"status": "sent", "to": to, "subject": subject}


def create_ticket(customer_id: str, subject: str, priority: str = "normal") -> dict:
    import uuid
    ticket_id = f"TKT-{str(uuid.uuid4())[:8].upper()}"
    print(f"[MOCK TICKET] Created {ticket_id} for customer {customer_id}: {subject}")
    return {"ticket_id": ticket_id, "customer_id": customer_id, "subject": subject, "priority": priority}


def delete_customer(customer_id: str) -> dict:
    # This should NEVER be reached — the ACR gateway blocks it
    raise RuntimeError("SECURITY VIOLATION: delete_customer should be blocked by ACR policy")


def issue_refund(customer_id: str, amount: float, reason: str) -> dict:
    print(f"[MOCK REFUND] Issuing ${amount} refund for customer {customer_id}: {reason}")
    return {"status": "refund_issued", "customer_id": customer_id, "amount": amount}
