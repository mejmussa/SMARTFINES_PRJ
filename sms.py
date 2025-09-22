# import package
import africastalking

# Initialize SDK
username = "CIRELINK"    # use 'sandbox' for development in the test environment
api_key = "atsk_af5952bbed2423bd9ff5636e22d20069adb57e6604aaf6f2eb7f67b774a281577ca78c98"      # use your sandbox app API key for development in the test environment
africastalking.initialize(username, api_key)

# Initialize a service e.g. SMS
sms = africastalking.SMS

def send_phone_login_otp(phone, otp):
    message = f"""Test
"""
    try:
        response = sms.send(
            message=message,
            recipients=[phone],
            sender_id="Smartfines"  # Alphanumeric sender ID
        )
        print(f"SMS sent successfully: {response}")
        return response
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return None

# Example usage for testing
if __name__ == "__main__":
    test_phone = "+255717455602"  # Replace with a test phone number
    test_otp = "123456"           # Example OTP
    result = send_phone_login_otp(test_phone, test_otp)