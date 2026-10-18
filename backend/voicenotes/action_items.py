"""Rule-based meeting action-item identification.

Each sentence is scored on linguistic evidence of a commitment or request:

  +2  strong obligation cue   ("need to", "must", "make sure", "let's", "please", "follow up" ...)
  +1  weak cue                ("will", "going to", "should", "can you" ...)
  +1  a concrete action verb  (send, prepare, schedule, review, finish ...)
  +1  a responsible person    (named person, or I / we / you)
  +1  a deadline phrase       ("by Friday", "tomorrow", "end of the week" ...)

A sentence with score >= 3 is reported as an action item. Rules are used
instead of a trained classifier because no labelled meeting dataset is needed
and every decision can be explained.
"""
import re

STRONG = re.compile(
    r"\b(?:action item|to-?do|need(?:s|ed)? to|(?:has|have) to|must|make sure|"
    r"follow(?:ing)? up|remember to|let'?s|please|responsible for|assigned to|"
    r"due (?:on|by|date)|deadline)\b", re.I)
WEAK = re.compile(
    r"\b(?:will|going to|should|shall|can you|could you|would you|"
    r"(?:i|we)'ll|plan(?:s|ning)? to)\b", re.I)
VERBS = {
    "send", "prepare", "schedule", "review", "update", "finish", "complete", "submit",
    "share", "create", "call", "email", "mail", "fix", "check", "book", "arrange",
    "finalize", "finalise", "draft", "write", "test", "deploy", "design", "organize",
    "organise", "contact", "confirm", "plan", "research", "publish", "present", "set",
    "follow", "discuss", "prepare", "collect", "upload", "download", "install", "build",
    "implement", "analyze", "analyse", "approve", "assign", "buy", "order", "print",
    "ask", "remind", "meet", "setup", "complete", "document", "report", "decide",
    "investigate", "resolve", "prioritize", "coordinate", "clean", "revise", "verify",
}

_DAYS = r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
_MONTHS = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
           r"sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)")
_PERIOD = r"(?:week|month|quarter|year|" + _DAYS + r")"
DEADLINE = re.compile(
    r"\b(?:by|before|until|till|on|due)\s+(?:the\s+)?(?:"
    r"(?:next|this|coming)\s+" + _PERIOD + r"|end of (?:the )?(?:day|week|month|quarter|year)|"
    r"eod|eow|today|tonight|tomorrow|" + _DAYS + r"|"
    r"\d{1,2}(?:st|nd|rd|th)(?:\s+(?:of\s+)?" + _MONTHS + r")?|"
    r"\d{1,2}\s+(?:of\s+)?" + _MONTHS + r"|" + _MONTHS + r"\s+\d{1,2}(?:st|nd|rd|th)?|"
    r"\d{1,2}(?::\d{2})?\s*(?:am|pm))\b"
    r"|\b(?:next|this|coming)\s+" + _PERIOD + r"\b"
    r"|\b(?:tomorrow|tonight|asap)\b"
    r"|\bend of (?:the )?(?:day|week|month)\b"
    r"|\bwithin\s+(?:\d+|an?|one|two|three|four|five|six|seven)\s+(?:hours?|days?|weeks?|months?)\b",
    re.I)

NAME_STOP = {
    "The", "This", "That", "These", "Those", "It", "He", "She", "They", "We", "You", "I",
    "There", "Here", "What", "Who", "When", "Where", "Why", "How", "And", "But", "So",
    "Then", "Also", "Okay", "Ok", "Well", "Now", "Today", "Tomorrow", "Meeting", "Project",
    "Report", "Work", "Rain", "Which", "Everything", "Nothing", "Please", "Maybe", "Next",
}
_NAME = r"([A-Z][a-z]{1,15})"
NAME_PATTERNS = [
    re.compile(r"\b" + _NAME + r"(?:\s+and\s+" + _NAME + r")?\s+(?:will|should|must|shall|needs? to|"
               r"has to|have to|is going to|are going to|can|could)\b"),
    re.compile(r"^" + _NAME + r",\s*(?:please|can you|could you|would you)\b"),
    re.compile(r"\b(?:assigned to|assign(?:ed)? it to|responsible:?|owner:?)\s+" + _NAME),
    re.compile(r"\b" + _NAME + r"\s+is responsible\b"),
]
URGENT = re.compile(r"\b(?:urgent(?:ly)?|asap|immediately|critical|high priority|top priority)\b", re.I)
LEADING = re.compile(r"^(?:okay|ok|so|alright|right|and|also|then|well|now)[,]?\s+", re.I)


def _assignee(sentence: str) -> str:
    for pat in NAME_PATTERNS:
        m = pat.search(sentence)
        if m:
            names = [g for g in m.groups() if g and g not in NAME_STOP]
            if names:
                return " & ".join(names)
    low = sentence.lower()
    if re.search(r"\b(?:can|could|would) you\b|\byou (?:should|need|must|will)\b", low):
        return "Person addressed"
    if re.search(r"\b(?:i|i'll|i'm)\b", low):
        return "Speaker (self)"
    if re.search(r"\b(?:we|we'll|let'?s|us|everyone)\b", low):
        return "Team"
    return "Unassigned"


def _score(sentence: str, assignee: str, deadline) -> int:
    score = 0
    if STRONG.search(sentence):
        score += 2
    if WEAK.search(sentence):
        score += 1
    words = set(re.findall(r"[a-z]+", sentence.lower()))
    if words & VERBS:
        score += 1
    if assignee != "Unassigned":
        score += 1
    if deadline:
        score += 1
    return score


def extract_action_items(sentences: list, threshold: int = 3) -> list:
    """Return [{task, assignee, deadline, priority, confidence}] sorted by confidence."""
    items, seen = [], set()
    for sent in sentences:
        sent = sent.strip()
        if len(sent.split()) < 3 or sent.endswith("?") and not re.search(r"can you|could you|would you", sent, re.I):
            continue
        m = DEADLINE.search(sent)
        deadline = m.group(0).strip() if m else None
        who = _assignee(sent)
        score = _score(sent, who, deadline)
        if score < threshold:
            continue
        task = LEADING.sub("", sent).strip()
        task = task[0].upper() + task[1:]
        key = task.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append({
            "task": task,
            "assignee": who,
            "deadline": deadline,
            "priority": "High" if URGENT.search(sent) else "Normal",
            "confidence": round(min(score / 5, 1.0), 2),
        })
    return sorted(items, key=lambda i: -i["confidence"])
