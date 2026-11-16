"""Email-drafting helper built on the Claude API.

The model is instructed to use only facts it's actually given — club
background plus whatever the member types in — and to mark anything it
doesn't know with a placeholder rather than invent it.
"""

import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

import db

load_dotenv()

CLUB_INFO_PATH = Path(__file__).parent / "club_info.md"
MODEL = "claude-sonnet-5-5"

SYSTEM_PROMPT_RESEARCH = """You help MFBC (Madison Fashion Business Collective), a UW-Madison \
student organization, prepare outreach to brands, companies, or individuals for sponsorship, \
speaking, or partnership opportunities at their events.

You have a web search tool. Use it to look up real, current public information about the \
company or person MFBC wants to reach out to — their brand, size, audience, recent news, and \
social presence — specifically to judge whether a student fashion-business event at UW-Madison \
would plausibly appeal to them.

You are given:
1. MFBC's own background (club history, past events, audience).
2. MFBC's actual outreach history — brands reached out to before, the type of ask, and the \
outcome where known (replied, no reply, declined, attending, etc.).
3. Details on the NEW brand/contact MFBC wants to reach out to now.

Using real information only — your web search results and what MFBC gave you below, never \
invented facts — produce exactly three sections in this format:

---CHANCE---
<One word: Low, Medium, or High> — <2-4 sentences of reasoning, grounded in (a) how similar this \
company is, in industry/scale/audience, to companies in MFBC's history that did or didn't reply, \
and (b) what your research found about why this company might or might not want to engage with a \
student organization like MFBC. Do not state a numeric percent — there isn't enough historical \
data (only a handful of logged outcomes) to justify one; a plain Low/Medium/High judgment call is \
more honest than a fake-precise number.>

---DRAFT---
<The outreach email body. Explain briefly and specifically why THIS company might want to \
participate in MFBC, using real facts from your research and from MFBC's own background — not \
generic flattery. Professional but warm tone, a student club reaching out, not a sales email. \
Under ~200 words. No subject line unless asked. Use a clearly marked placeholder like \
[SPECIFIC DETAIL] for anything that would improve the email but wasn't available from research or \
the facts given.>

---RELIED ON---
<Bullet list of the specific facts you used — both what you found via web search (with a brief \
source, e.g. "company website," "a 2025 press article") and what was given to you directly — so \
a club member can verify everything in the draft and chance assessment before sending.>

Rules:
- Never invent facts about the company, numbers, dates, or past interactions. If your search \
doesn't turn up something relevant, say so rather than guessing.
- Keep the tone professional but warm and genuine.
- Always produce all three sections, in full. Never end your turn on research notes, a partial \
thought, or anything other than the complete ---CHANCE---, ---DRAFT---, and ---RELIED ON--- \
sections — the draft section in particular must always be an actual, ready-to-edit email, never \
a status update about what you were doing.
"""


SYSTEM_PROMPT_FOLLOWUP = """You help MFBC (Madison Fashion Business Collective), a UW-Madison \
student organization, continue an email conversation with a brand, company, or individual \
they've already reached out to about a sponsorship, speaking, or partnership opportunity.

You are given MFBC's background, the brand/contact's details, the email MFBC already sent them, \
what MFBC had previously researched or knew about them, and their actual reply.

Write a single follow-up email that directly responds to what they said — answer any question \
they asked, address any concern they raised, and move the conversation forward (e.g. propose a \
next step, answer logistics, or thank them and confirm next steps if they said yes). Do not \
repeat the full original pitch or re-introduce MFBC from scratch — they already know who MFBC is.

Rules:
- Never invent facts, numbers, or dates not given to you.
- Professional but warm tone, a student club member writing to someone they're already talking to.
- Under ~150 words. No subject line unless asked.
- Output ONLY the email body — no preamble, no section markers, no commentary.
"""


SYSTEM_PROMPT_REMINDER = """You help MFBC (Madison Fashion Business Collective), a UW-Madison \
student organization, write a polite follow-up/reminder email to a brand, company, or individual \
they already emailed but haven't heard back from yet.

You are given MFBC's background, the brand/contact's details, what MFBC had previously \
researched or knew about them, and the email MFBC already sent.

Write a short, polite reminder — reference the original note briefly (don't repeat the whole \
pitch), acknowledge they're probably busy, and restate interest without being pushy.

Rules:
- Never invent facts, numbers, or dates not given to you.
- Professional but warm tone, a student club member following up.
- Under ~100 words. No subject line unless asked.
- Output ONLY the email body — no preamble, no section markers, no commentary.
"""


def draft_reminder(record: dict) -> dict:
    """One-shot reminder draft for a brand that hasn't replied yet — a polite nudge based on
    the original email and what MFBC knew, with no reply to respond to."""
    club_info = read_club_info()
    brand_block = _brand_block(record)
    original_email = record.get("email_text") or "(no original email on file)"
    relied_on = record.get("ai_relied_on") or "(none recorded)"

    user_message = f"""MFBC CLUB BACKGROUND:
{club_info}

BRAND/CONTACT DETAILS:
{brand_block}

WHAT MFBC PREVIOUSLY KNEW/RESEARCHED ABOUT THEM:
{relied_on}

THE EMAIL MFBC ALREADY SENT THEM (no reply yet):
{original_email}

Write the reminder/follow-up email."""

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT_REMINDER,
        messages=[{"role": "user", "content": user_message}],
    )
    text = "".join(block.text for block in message.content if block.type == "text")
    return {"draft": text.strip()}


def draft_followup(record: dict, response_text: str) -> dict:
    """One-shot follow-up draft: given the email MFBC already sent, what MFBC knew about this
    brand, and their actual reply, draft the next email in the conversation. No web search —
    this is a quick continuation of an existing thread, not fresh research."""
    club_info = read_club_info()
    brand_block = _brand_block(record)
    original_email = record.get("email_text") or "(no original email on file)"
    relied_on = record.get("ai_relied_on") or "(none recorded)"

    user_message = f"""MFBC CLUB BACKGROUND:
{club_info}

BRAND/CONTACT DETAILS:
{brand_block}

WHAT MFBC PREVIOUSLY KNEW/RESEARCHED ABOUT THEM:
{relied_on}

THE EMAIL MFBC ALREADY SENT THEM:
{original_email}

THEIR REPLY:
{response_text.strip() or "(no reply text given)"}

Write the follow-up email."""

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT_FOLLOWUP,
        messages=[{"role": "user", "content": user_message}],
    )
    text = "".join(block.text for block in message.content if block.type == "text")
    return {"draft": text.strip()}


def read_club_info() -> str:
    """The club's narrative background, plus the live, member-editable fact
    bullets from the Home page — editing a bullet there changes this, and so
    changes what the AI uses on the next draft."""
    base = CLUB_INFO_PATH.read_text() if CLUB_INFO_PATH.exists() else ""
    notes = db.club_notes_text()
    return f"{base}\n\n## Known facts (maintained by the club, editable on the Home page)\n{notes}"


def api_key_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _brand_block(brand_info: dict) -> str:
    brand_lines = []
    for label, key in [
        ("Company", "company"),
        ("Contact name", "contact_name"),
        ("Contact role", "contact_role"),
        ("Type of ask", "ask_type"),
        ("This is a follow-up", "is_follow_up"),
        ("UW/MFBC connection", "has_uw_mfbc_connection"),
        ("Prior relationship", "has_prior_relationship"),
        ("Notes from the club", "notes"),
    ]:
        val = brand_info.get(key)
        if val not in (None, "", False):
            brand_lines.append(f"- {label}: {val}")
    return "\n".join(brand_lines) if brand_lines else "(no brand details provided)"


def _history_summary(history_df) -> str:
    if history_df is None or history_df.empty:
        return "(no outreach history logged yet)"
    lines = []
    for row in history_df.itertuples():
        bits = [str(row.company)]
        if getattr(row, "ask_type", None):
            bits.append(f"ask: {row.ask_type}")
        if getattr(row, "outcome", None):
            bits.append(f"outcome: {row.outcome}")
        if getattr(row, "stage", None):
            bits.append(f"stage: {row.stage}")
        lines.append("- " + ", ".join(bits))
    return "\n".join(lines) if lines else "(no outreach history logged yet)"


def research_and_draft(brand_info: dict, history_df, extra_public_info: str = "") -> dict:
    """AI mode: Claude researches the company via web search, then returns a chance assessment and a draft grounded in that research plus MFBC's own history.

    No artificial time limit — this runs until the model is done researching
    and writing, however long that takes.
    """
    club_info = read_club_info()
    brand_block = _brand_block(brand_info)
    history_block = _history_summary(history_df)
    extra_block = extra_public_info.strip() or "(none provided)"

    user_message = f"""MFBC CLUB BACKGROUND:
{club_info}

MFBC'S OUTREACH HISTORY (company, ask type, outcome where known):
{history_block}

NEW BRAND/CONTACT MFBC WANTS TO REACH OUT TO:
{brand_block}

ADDITIONAL INFO THE MEMBER ALREADY KNOWS (optional, may be empty):
{extra_block}

Research this company with web search, then produce the three sections exactly as instructed."""

    client = anthropic.Anthropic()
    with client.messages.stream(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT_RESEARCH,
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 10}],
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        final_message = stream.get_final_message()
    text = "".join(block.text for block in final_message.content if block.type == "text")

    chance_label = None
    chance_reasoning = ""
    # Best-effort fallback: if the model didn't return the expected section
    # markers, the draft is simply whatever text it did write — never a
    # status message about what the research was doing.
    draft = text
    relied_on = "(model did not return a relied-on list)"

    if "---CHANCE---" in text and "---DRAFT---" in text:
        chance_part, rest = text.split("---DRAFT---", 1)
        chance_reasoning = chance_part.split("---CHANCE---", 1)[1].strip()
        for candidate in ("High", "Medium", "Low"):
            if chance_reasoning.lower().startswith(candidate.lower()):
                chance_label = candidate
                break
        if chance_label is None:
            for candidate in ("High", "Medium", "Low"):
                if candidate.lower() in chance_reasoning.lower():
                    chance_label = candidate
                    break
        if "---RELIED ON---" in rest:
            draft, relied_on = rest.split("---RELIED ON---", 1)
        else:
            draft = rest
    elif "---RELIED ON---" in text:
        draft, relied_on = text.split("---RELIED ON---", 1)

    return {
        "chance_label": chance_label,
        "chance_reasoning": chance_reasoning,
        "draft": draft.strip(),
        "relied_on": relied_on.strip(),
    }
