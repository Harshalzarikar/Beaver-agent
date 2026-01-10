from src.security import PIIManager

def test_pii_logic():
    print("🛡️ TESTING PII SECURITY VAULT...")
    
    # 1. Setup
    manager = PIIManager()
    
    # 2. Input Data (Sensitive!)
    original_text = "My name is Harshal. Call me at 9822012345 or email harshal@test.com."
    print(f"\n1️⃣ ORIGINAL:\n   {original_text}")

    # 3. Test Anonymization (What the AI sees)
    safe_text = manager.anonymize(original_text)
    print(f"\n2️⃣ ANONYMIZED (Sent to AI):\n   {safe_text}")
    
    # VERIFICATION CHECK
    if "9822012345" in safe_text:
        print("❌ FAILED: Phone number leaked!")
    elif "harshal@test.com" in safe_text:
        print("❌ FAILED: Email leaked!")
    else:
        print("✅ SUCCESS: Secrets are hidden.")

    # 4. Test De-anonymization (What the Customer sees)
    restored_text = manager.deanonymize(safe_text)
    print(f"\n3️⃣ RESTORED (Final Output):\n   {restored_text}")
    
    # VERIFICATION CHECK
    if restored_text == original_text:
        print("✅ SUCCESS: Data perfectly restored.")
    else:
        print("❌ FAILED: Data corruption during restore.")

if __name__ == "__main__":
    test_pii_logic()