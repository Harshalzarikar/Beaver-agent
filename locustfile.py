from locust import HttpUser, task, between
import uuid

class EmailUser(HttpUser):
    # Wait 1-3 seconds between requests (simulates human behavior)
    wait_time = between(1, 3)

    @task
    def send_email(self):
        # Generate a unique trace ID so logs look real
        trace = str(uuid.uuid4())
        
        payload = {
            "email_text": f"I want to buy enterprise AI software for my company. Trace: {trace}"
        }
        
        # Hit your local API
        self.client.post("/process-email", json=payload)