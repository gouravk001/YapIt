from __future__ import annotations

import json
from typing import Any

from app.config.types_config import FieldDefinition, TypeDefinition

_MAX_EXAMPLES = 2

_NOTE_GATE = """Step 1: decide what kind of recording this is (kind).
- note: something the speaker wants to remember or act on later: money owed, a promise, a plan \
or appointment, a fact, a task or to-do, an idea, a reminder, or a personal thought. Short or \
casual notes count.
- greeting_or_test: a greeting or microphone check ("hello", "testing one two three").
- question_or_command: a question asking for information right now, or a command for a media \
player or smart device ("what's the weather today", "play some music", "set a timer", "turn on \
the lights"). Short to-dos the speaker is writing down ("call mom", "buy milk") are notes.
- background_media: speech from a video, TV show, podcast or advert ("thanks for watching, \
like and subscribe").
- lyrics_or_gibberish: song lyrics, nursery rhymes, or words with no recognisable meaning.
If it could reasonably be something the speaker wants to keep, choose note."""

_REFINE_RULES = """Rules:
- Start with "restatement": in your own words (not a copy of the transcript), say who must do \
what for whom and when, from the speaker's point of view. For example "Neha lent me 800 \
rupees, so I will give Neha 800 rupees by Friday" or "I lent Arjun 2,000 rupees, so I will \
receive 2,000 rupees from Arjun". Then fill the fields so they agree with it.
- The speaker is "I" / "me". Read who does what from the speaker's point of view.
- Use only what the transcript says. If a field is not mentioned, return "" for it. Never invent \
values, and never fill an optional field with words the speaker did not say.
- A person field is always someone other than the speaker: never "I", "me" or "myself".
- Spell names as they appear and capitalise them properly.
- Keep text fields short and clean: fix capitalisation and punctuation, drop filler words (um, \
uh, like, you know, basically), keep the speaker's meaning. No full stop after a short phrase.
- For date fields, return the words the speaker used for the date (for example "next Friday"), \
not a calendar date.
- For money fields, return the amount with its currency symbol, for example "₹1,50,000" or "$40".

Summary rules:
- One line, at most 10 words, written like a notebook heading or to-do item.
- Do not narrate: never start with "I", and never write "the speaker" or "this note".
- Write amounts like ₹1,50,000, keep the speaker's date words, and capitalise day and month names.
- Examples of the style only (never copy their names or details): "Arjun owes ₹2,000 for dinner, due Monday", "Pay Neha back ₹800 by \
Friday", "Send Karan the slides tomorrow", "Team lunch with Sara, Thursday 1 PM", "Car insurance \
renews on 3 March", "Pick up the dry cleaning"."""


def _field_line(field: FieldDefinition) -> str:
    kind = field.field_type
    if field.allowed_values:
        kind = f"one of: {' | '.join(repr(choice) for choice in field.llm_choices())}"
    elif field.field_type == "list":
        kind = f"list of {field.item_type or 'text'}"
    requirement = "required" if field.required else "optional"
    return f"- {field.name} ({kind}, {requirement}): {field.description}"


def _fields_block(type_def: TypeDefinition) -> str:
    return "\n".join(_field_line(f) for f in type_def.fields)


def _examples_block(type_def: TypeDefinition) -> str:
    if not type_def.examples:
        return ""
    by_name = {f.name: f for f in type_def.fields}
    parts = []
    for ex in type_def.examples[:_MAX_EXAMPLES]:
        fields = {
            name: by_name[name].to_llm_value(value) if name in by_name else value
            for name, value in ex.expected_fields.items()
        }
        parts.append(
            f'Transcript: "{ex.transcript}"\nFields: {json.dumps(fields, ensure_ascii=False)}'
        )
    return "\n\n## Examples\n" + "\n\n".join(parts)


def classification_prompt(transcript: str, type_definitions: list[TypeDefinition]) -> str:
    """Build the prompt that decides whether the transcript is a note, and of which type."""
    type_descriptions = "\n".join(
        f"- {td.name}: {' '.join(td.description.split())}" for td in type_definitions
    )
    return (
        "You sort voice recordings for a personal notebook app.\n\n"
        f"{_NOTE_GATE}\n\n"
        "Step 2: pick the note type that fits best (type_name):\n"
        f"{type_descriptions}\n"
        'If it is not a note, set type_name to "general".\n\n'
        f'## Transcript\n"""{transcript}"""\n\n'
        "Respond with JSON."
    )


def extraction_prompt(transcript: str, type_def: TypeDefinition) -> str:
    """Build the prompt for the field extraction step."""
    return (
        f"Extract the fields of a **{type_def.name}** note from a voice transcript. "
        'The speaker is "I" / "me".\n\n'
        f"## Fields\n{_fields_block(type_def)}\n\n"
        "For date fields, copy the exact words the speaker used for the date "
        '(for example "next Friday" or "the 25th"). '
        "Leave out fields the transcript does not mention."
        f"{_examples_block(type_def)}\n\n"
        f'## Transcript\n"""{transcript}"""\n\n'
        "Respond with JSON."
    )


def refine_prompt(transcript: str, type_def: TypeDefinition, draft: dict[str, Any]) -> str:
    """Build the prompt that checks a draft against the transcript and tidies it for saving."""
    return (
        f"You are checking a draft **{type_def.name}** note before it is saved. Compare every "
        "field with the transcript and correct anything that is wrong or missing.\n\n"
        f"{_REFINE_RULES}\n\n"
        f"## Fields\n{_fields_block(type_def)}\n\n"
        f'## Transcript\n"""{transcript}"""\n\n'
        f"## Draft\n{json.dumps(draft, ensure_ascii=False)}\n\n"
        "Respond with JSON containing the corrected fields and the summary."
    )


def plausibility_prompt(transcript: str, today: str) -> str:
    """Build the prompt that asks whether a note contains something that cannot be right."""
    return (
        f"You check voice notes for mistakes before they are saved. Today is {today}.\n\n"
        'Answer "unlikely" only if something in the note cannot be right or is very hard to '
        "believe:\n"
        "- an impossible date or clock time (25 PM, 30 February)\n"
        "- something described as upcoming that is already in the past (a flight that leaves "
        "yesterday)\n"
        "- a wildly unrealistic amount, duration or speed (running a marathon in 10 minutes)\n"
        'Ordinary plans, debts, reminders, facts and thoughts are "ordinary", even early-morning '
        "or unusual ones. Mentions of past events (paying for yesterday's dinner), days of the "
        'month ("the 25th"), and large but possible amounts or tight deadlines are "ordinary". '
        'When in doubt, answer "ordinary".\n'
        'If "unlikely", give the reason as one short sentence to the user; otherwise reason is "".'
        f'\n\nNote: """{transcript}"""\n\n'
        "Respond with JSON."
    )
