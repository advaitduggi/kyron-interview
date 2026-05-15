import asyncio
import logging
import os

from tools.lookup_office_info import PRACTICE_INFO

logger = logging.getLogger(__name__)

_OFFICE_ADDRESS = PRACTICE_INFO["address"]
_OFFICE_PHONE = PRACTICE_INFO["phone"]


def _confirmation_number(appointment_id: str) -> str:
    return "KM-" + appointment_id.replace("-", "")[:8].upper()


async def send_confirmation_email(
    patient_email: str,
    patient_name: str,
    provider_name: str,
    slot_time: str,
    appointment_id: str,
) -> None:
    """Send appointment confirmation via SendGrid. Errors are logged, not raised."""
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail

        api_key = os.environ.get("SENDGRID_API_KEY", "")
        from_email = os.environ.get("FROM_EMAIL", "noreply@kyronmedical.com")
        confirmation = _confirmation_number(appointment_id)

        body = (
            f"Dear {patient_name},\n\n"
            f"Your appointment has been confirmed.\n\n"
            f"  Doctor:           {provider_name}\n"
            f"  Date & Time:      {slot_time}\n"
            f"  Confirmation #:   {confirmation}\n\n"
            f"Office Location:\n"
            f"  {_OFFICE_ADDRESS}\n"
            f"  {_OFFICE_PHONE}\n\n"
            "To cancel or reschedule, please call our office during business hours "
            "(Monday–Friday, 9 AM–5 PM).\n\n"
            "Thank you,\nKyron Medical"
        )

        message = Mail(
            from_email=from_email,
            to_emails=patient_email,
            subject=f"Appointment Confirmed — {provider_name}",
            plain_text_content=body,
        )

        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        await asyncio.to_thread(sg.send, message)
        logger.info("Confirmation email sent to %s (appt %s)", patient_email, appointment_id)

    except Exception:
        logger.exception("Failed to send confirmation email to %s", patient_email)


async def send_confirmation_sms(
    patient_phone: str,
    provider_name: str,
    slot_time: str,
) -> None:
    """Send appointment confirmation via Twilio. Errors are logged, not raised."""
    try:
        from twilio.rest import Client

        account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        from_number = os.environ.get("TWILIO_PHONE_NUMBER", "")

        body = (
            f"Your appt with {provider_name} is confirmed for {slot_time}. "
            "Reply STOP to opt out."
        )

        client = Client(account_sid, auth_token)
        await asyncio.to_thread(
            client.messages.create,
            body=body,
            from_=from_number,
            to=patient_phone,
        )
        logger.info("Confirmation SMS sent to %s", patient_phone)

    except Exception:
        logger.exception("Failed to send confirmation SMS to %s", patient_phone)
