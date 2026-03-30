"""Invoice Agent — generates professional invoices and manages payment tracking."""

import uuid
from datetime import datetime, timedelta, timezone

from .base import BaseAgent

SYSTEM_PROMPT = """You are a professional invoice and billing specialist. You create
clear, detailed invoice line items and payment reminder messages.

You MUST respond with valid JSON only."""


class InvoiceAgent(BaseAgent):
    name = "invoice"

    async def generate_invoice(
        self,
        client_name: str,
        client_email: str,
        services: list[dict],
        freelancer_name: str = "Freelancer",
        notes: str = "",
    ) -> dict:
        """Generate a professional invoice with HTML rendering.

        Args:
            client_name: Client's name or company
            client_email: Client's email
            services: List of {"description": str, "amount": float}
            freelancer_name: The freelancer's name for the invoice header
            notes: Optional notes to include

        Returns:
            Dict with invoice_number, client, amount, services, due_date, html_content.
        """
        inv_number = f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        total = sum(s.get("amount", 0) for s in services)
        due_date = datetime.now(timezone.utc) + timedelta(days=30)

        rows_html = ""
        for s in services:
            rows_html += (
                f'<tr><td style="padding:12px 16px;border-bottom:1px solid #e5e7eb">'
                f'{s.get("description", "")}</td>'
                f'<td style="padding:12px 16px;border-bottom:1px solid #e5e7eb;text-align:right">'
                f'${s.get("amount", 0):,.2f}</td></tr>'
            )

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Invoice {inv_number}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; color: #1f2937; background: #f9fafb; }}
  .invoice {{ max-width: 720px; margin: 40px auto; background: #fff; border-radius: 12px;
              box-shadow: 0 1px 3px rgba(0,0,0,.1); padding: 48px; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 40px; }}
  .brand {{ font-size: 28px; font-weight: 700; color: #2563eb; }}
  .meta {{ text-align: right; color: #6b7280; font-size: 14px; line-height: 1.6; }}
  .meta strong {{ color: #1f2937; }}
  .parties {{ display: flex; justify-content: space-between; margin-bottom: 32px; }}
  .party {{ font-size: 14px; line-height: 1.7; }}
  .party-label {{ font-size: 12px; text-transform: uppercase; color: #9ca3af; font-weight: 600; letter-spacing: .05em; margin-bottom: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; }}
  th {{ padding: 12px 16px; text-align: left; background: #f3f4f6; font-size: 13px;
       text-transform: uppercase; letter-spacing: .05em; color: #6b7280; font-weight: 600; }}
  th:last-child {{ text-align: right; }}
  .total-row {{ text-align: right; font-size: 20px; font-weight: 700; color: #2563eb; padding: 16px 0; }}
  .notes {{ margin-top: 32px; padding: 16px; background: #f9fafb; border-radius: 8px; font-size: 14px; color: #6b7280; }}
  .footer {{ margin-top: 40px; text-align: center; font-size: 12px; color: #9ca3af; }}
</style></head>
<body><div class="invoice">
  <div class="header">
    <div class="brand">INVOICE</div>
    <div class="meta">
      <div><strong>{inv_number}</strong></div>
      <div>Issued: {datetime.now(timezone.utc).strftime('%B %d, %Y')}</div>
      <div>Due: {due_date.strftime('%B %d, %Y')}</div>
    </div>
  </div>
  <div class="parties">
    <div class="party"><div class="party-label">From</div>{freelancer_name}</div>
    <div class="party"><div class="party-label">Bill To</div>{client_name}<br>{client_email}</div>
  </div>
  <table>
    <thead><tr><th>Service</th><th style="text-align:right">Amount</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
  <div class="total-row">Total Due: ${total:,.2f}</div>
  {f'<div class="notes"><strong>Notes:</strong> {notes}</div>' if notes else ''}
  <div class="footer">Thank you for your business.</div>
</div></body></html>"""

        return {
            "invoice_number": inv_number,
            "client_name": client_name,
            "client_email": client_email,
            "amount": total,
            "services": services,
            "due_date": due_date.isoformat(),
            "html_content": html_content,
            "status": "draft",
        }

    async def generate_payment_reminder(
        self,
        client_name: str,
        invoice_number: str,
        amount: float,
        due_date: str,
        days_overdue: int = 0,
    ) -> dict:
        """Generate a payment reminder message using Claude.

        Args:
            client_name: Client name
            invoice_number: Invoice number for reference
            amount: Amount due
            due_date: Due date string
            days_overdue: How many days past due (0 = upcoming reminder)

        Returns:
            Dict with subject, body, tone.
        """
        if days_overdue <= 0:
            context = "upcoming payment due soon"
            tone_hint = "friendly reminder"
        elif days_overdue <= 7:
            context = f"payment is {days_overdue} days overdue"
            tone_hint = "polite but firm"
        else:
            context = f"payment is {days_overdue} days overdue"
            tone_hint = "firm but professional, mention next steps"

        reminder_prompt = f"""Write a payment reminder email:

- Client: {client_name}
- Invoice: {invoice_number}
- Amount: ${amount:,.2f}
- Due Date: {due_date}
- Status: {context}

Tone: {tone_hint}

Respond with JSON: {{"subject": "...", "body": "...", "tone": "..."}}"""

        return await self.call_claude_json(
            "You are a professional billing specialist. Respond with JSON only.",
            reminder_prompt,
            max_tokens=600,
        )
