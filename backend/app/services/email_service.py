# app/services/email_service.py

import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from flask import current_app
from app.utils.input_sanitizer import sanitize_input
import asyncio

logger = logging.getLogger(__name__)

class EmailService:
    _instance = None

    def __init__(self):
        self.sg = None
        self.from_email = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self, app):
        self.sg = SendGridAPIClient(api_key=app.config['SENDGRID_API_KEY'])
        self.from_email = app.config['SENDGRID_FROM_EMAIL']

    async def send_trial_match_email(self, to_email, patient_name, matching_trials):
        """
        Asynchronously send an email to the patient about new matching trials.
        
        Args:
            to_email (str): Recipient's email address
            patient_name (str): Name of the patient
            matching_trials (list): List of matching trial dictionaries
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.sg:
            raise RuntimeError("EmailService not initialized. Call initialize() first.")

        if not matching_trials:
            logger.info(f"No matching trials for {to_email}. Email not sent.")
            return False

        # Sanitize input data
        safe_email = sanitize_input(to_email)
        safe_name = sanitize_input(patient_name)
        safe_trials = sanitize_input(matching_trials)

        subject = "New Clinical Trials Matched to Your Profile"
        
        content = self._construct_email_content(safe_name, safe_trials)

        message = Mail(
            from_email=self.from_email,
            to_emails=safe_email,
            subject=subject,
            plain_text_content=content)

        try:
            # Use asyncio to run the synchronous send method in a separate thread
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self.sg.send, message)
            
            logger.info(f"Email sent to {safe_email}. Status code: {response.status_code}")
            return response.status_code == 202
        except Exception as e:
            logger.error(f"Error sending email to {safe_email}: {str(e)}")
            return False

    def _construct_email_content(self, patient_name, matching_trials):
        """
        Construct the content of the email.
        
        Args:
            patient_name (str): Name of the patient
            matching_trials (list): List of matching trial dictionaries
        
        Returns:
            str: The constructed email content
        """
        content = f"Dear {patient_name},\n\n"
        content += "We've found new clinical trials that match your profile:\n\n"
        
        for trial in matching_trials:
            content += f"- {trial['brief_title']}\n"
            content += f"  NCT ID: {trial['nct_id']}\n"
            content += f"  More info: https://clinicaltrials.gov/ct2/show/{trial['nct_id']}\n\n"
        
        content += "Log in to your account for more details about these trials.\n\n"
        content += "Best regards,\nClinical Trial Eligibility Screener Team"

        return content

# Create a global instance of EmailService
email_service = EmailService.get_instance()