from presidio_analyzer import AnalyzerEngine
import uuid

class PIIManager:
    def __init__(self):
        # Initialize Microsoft Presidio Analyzer (Loads the NLP model)
        self.analyzer = AnalyzerEngine()
        self.vault = {}  # Stores { "[TOKEN]": "Real Data" }

    def anonymize(self, text: str):
        """
        Uses Presidio to FIND entities, then swaps them for tokens
        and saves them to the vault.
        """
        # 1. Analyze the text (Finds PERSON, PHONE_NUMBER, EMAIL_ADDRESS, etc.)
        results = self.analyzer.analyze(text=text, language='en', 
                                        entities=["PHONE_NUMBER", "EMAIL_ADDRESS", "PERSON", "CREDIT_CARD"])
        
        # 2. Iterate backwards to replace text without messing up indices
        # (We go backwards because changing text at the start shifts the end positions)
        for result in sorted(results, key=lambda x: x.start, reverse=True):
            
            # Extract the sensitive text (e.g., "9822012345")
            sensitive_data = text[result.start:result.end]
            
            # Create a Token (e.g., "[PHONE_NUMBER_1a2b]")
            token = f"[{result.entity_type}_{str(uuid.uuid4())[:4]}]"
            
            # Save to Vault
            self.vault[token] = sensitive_data
            
            # Replace in the text string
            text = text[:result.start] + token + text[result.end:]
            
        return text

    def deanonymize(self, text: str):
        """
        Restores the real data from the vault.
        """
        for token, real_value in self.vault.items():
            if token in text:
                text = text.replace(token, real_value)
        return text