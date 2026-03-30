"""Communication Agent — drafts follow-ups, replies, and manages outreach."""

from .base import BaseAgent

SYSTEM_PROMPT = """You are an expert freelance communication specialist. You draft
follow-up messages, replies to client responses, and manage professional outreach.

Your messages are:
- Concise (50-150 words for follow-ups, 100-250 for replies)
- Professional but human — never robotic
- Reference previous interactions specifically
- Include a clear next step or call to action
- NEVER pushy or desperate

You MUST respond with valid JSON only.

JSON schema:
{
  "subject": "email subject line",
  "body": "the message body text",
  "channel": "email|linkedin",
  "tone": "friendly|professional|urgent",
  "notes": "internal notes about this message for the freelancer"
}"""


class CommunicationAgent(BaseAgent):
    name = "communication"

    async def draft_follow_up(
        self,
        lead_name: str,
        company: str,
        original_message: str,
        days_since_sent: int = 2,
        channel: str = "email",
    ) -> dict:
        """Draft a follow-up message for a lead who hasn't responded.

        Args:
            lead_name: Name of the lead
            company: Lead's company name
            original_message: The original proposal/message sent
            days_since_sent: Days since the original message was sent
            channel: Communication channel

        Returns:
            Dict with subject, body, channel, tone, notes.
        """
        user_prompt = f"""Draft a follow-up message:

## Context
- Lead: {lead_name} at {company}
- Channel: {channel}
- Days since original message: {days_since_sent}
- Original message sent:
{original_message[:500]}...

Write a brief, natural follow-up. Don't repeat the entire original pitch.
Add a new piece of value (insight, relevant article topic, or quick tip)."""

        return await self.call_claude_json(SYSTEM_PROMPT, user_prompt, max_tokens=800)

    async def draft_reply(
        self,
        lead_name: str,
        company: str,
        client_message: str,
        conversation_history: str = "",
    ) -> dict:
        """Draft a reply to a client's response.

        Args:
            lead_name: Name of the lead
            company: Lead's company
            client_message: The client's message to reply to
            conversation_history: Previous messages for context

        Returns:
            Dict with subject, body, channel, tone, notes.
        """
        user_prompt = f"""Draft a reply to this client message:

## Client
{lead_name} at {company}

## Their Message
{client_message}

## Previous Conversation
{conversation_history or 'This is the first reply from the client.'}

Respond helpfully. If they're interested, suggest a specific next step
(e.g., a 15-minute call). If they have questions, answer directly."""

        return await self.call_claude_json(SYSTEM_PROMPT, user_prompt, max_tokens=800)

    async def draft_initial_outreach(
        self,
        lead_name: str,
        company: str,
        role: str,
        value_proposition: str,
        channel: str = "email",
    ) -> dict:
        """Draft an initial cold outreach message.

        Args:
            lead_name: Name of the lead
            company: Lead's company
            role: Lead's role/title
            value_proposition: What value the freelancer can provide
            channel: email or linkedin

        Returns:
            Dict with subject, body, channel, tone, notes.
        """
        user_prompt = f"""Draft an initial outreach message:

## Lead
- Name: {lead_name}
- Company: {company}
- Role: {role}
- Channel: {channel}

## Value Proposition
{value_proposition}

Write a compelling first message. Open with something specific to their
company or role (not "I hope this finds you well"). Be direct about
what you can offer. Keep it under 150 words for {channel}."""

        return await self.call_claude_json(SYSTEM_PROMPT, user_prompt, max_tokens=800)
