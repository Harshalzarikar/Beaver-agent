import re

class Redactor:
    def __init__(self):
        self.patterns = {
            "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "PHONE": r"(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{10})",
            "CREDIT_CARD": r"\b(?:\d[ -]*?){13,16}\b"
        }

    def redact(self, text: str) -> str:
        for entity, pattern in self.patterns.items():
            text = re.sub(pattern, f"[{entity}_REDACTED]", text)
        return text

redactor = Redactor()
