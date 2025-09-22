# import package
import africastalking

# Initialize SDK
username = "TECMOCSY"    # use 'sandbox' for development in the test environment
api_key = "atsk_f4abc439a793684e70936ae3fabee834d337385ca90f4caf274d938a1739809c33d39ed4"      # use your sandbox app API key for development in the test environment
africastalking.initialize(username, api_key)

# Initialize a service e.g. SMS
sms = africastalking.SMS

def send_phone_login_otp(phone, otp):
    message = f"""TECMOCSY Login
OTP code: {otp}
Expires in 10 minutes.
"""
    try:
        response = sms.send(
            message=message,
            recipients=[phone],
            sender_id="MOCSYPAY"  # Alphanumeric sender ID
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