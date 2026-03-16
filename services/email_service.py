import aiosmtplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import settings

class EmailService:
    @staticmethod
    async def send_email(to_email: str, subject: str, html_content: str, text_content: str = None):
        """Send email using Gmail SMTP"""
        try:
            print(f"Attempting to send email to: {to_email}")
            print(f"Using SMTP: {settings.email_host}:{settings.email_port}")
            print(f"From: {settings.email_from}")
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{settings.email_from_name} <{settings.email_from}>"
            message["To"] = to_email
            
            # Add text and HTML parts
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)
            
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Send email with more detailed error handling
            try:
                await aiosmtplib.send(
                    message,
                    hostname=settings.email_host,
                    port=settings.email_port,
                    start_tls=True,
                    username=settings.email_username,
                    password=settings.email_password,
                    timeout=30,
                )
                print(f"Email sent successfully to: {to_email}")
                return True
            except aiosmtplib.SMTPAuthenticationError as auth_error:
                print(f"❌ Gmail Authentication failed: {str(auth_error)}")
                print("🔧 SOLUTION REQUIRED:")
                print("1. Enable 2-Factor Authentication on your Gmail account")
                print("2. Generate an App Password: https://myaccount.google.com/apppasswords")
                print("3. Use the App Password (16 characters) in EMAIL_PASSWORD")
                print("4. Make sure EMAIL_USERNAME matches your Gmail address")
                return False
            except aiosmtplib.SMTPException as smtp_error:
                print(f"SMTP error: {str(smtp_error)}")
                return False
            except Exception as general_error:
                print(f"General error: {str(general_error)}")
                return False
                
        except Exception as e:
            print(f"Email sending failed: {str(e)}")
            return False

    @staticmethod
    def send_email_sync(to_email: str, subject: str, html_content: str):
        """Alternative email sending using standard smtplib"""
        try:
            print(f"Trying alternative email method to: {to_email}")
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{settings.email_from_name} <{settings.email_from}>"
            msg['To'] = to_email
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Connect to Gmail SMTP server
            server = smtplib.SMTP(settings.email_host, settings.email_port)
            server.starttls()
            server.login(settings.email_username, settings.email_password)
            
            # Send email
            text = msg.as_string()
            server.sendmail(settings.email_from, to_email, text)
            server.quit()
            
            print(f"Alternative email sent successfully to: {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ Gmail Authentication failed (sync): {str(e)}")
            print("🔧 SOLUTION REQUIRED:")
            print("1. Enable 2-Factor Authentication on your Gmail account")
            print("2. Generate an App Password: https://myaccount.google.com/apppasswords")
            print("3. Use the App Password (16 characters) in EMAIL_PASSWORD")
            return False
        except Exception as e:
            print(f"Alternative email failed: {str(e)}")
            return False

    @staticmethod
    async def form_submitted_email(user_email: str, user_name: str, student_id: str = None):
        """Send form submitted confirmation email"""
        subject = "✅ Registration Successful - KNCCI Internship Program"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #2c5aa0 0%, #1e3d72 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h1 style="color: white; margin: 0; font-size: 28px;">🎉 Welcome to KNCCI!</h1>
                    <p style="color: #e8f4fd; margin: 10px 0 0 0; font-size: 16px;">Internship Program Registration</p>
                </div>
                
                <div style="padding: 30px; background-color: #ffffff; border-radius: 0 0 10px 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h2 style="color: #2c5aa0; margin-top: 0;">Dear {user_name},</h2>
                    
                    <div style="background-color: #e8f5e8; padding: 20px; border-radius: 8px; border-left: 4px solid #28a745; margin: 20px 0;">
                        <h3 style="color: #155724; margin-top: 0;">✅ Registration Successful!</h3>
                        <p style="margin-bottom: 0; color: #155724;">Your application for the KNCCI Internship Program has been successfully submitted and received.</p>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #2c5aa0;">📋 Registration Details</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #555;">Name:</td>
                                <td style="padding: 8px 0; color: #333;">{user_name}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #555;">Email:</td>
                                <td style="padding: 8px 0; color: #333;">{user_email}</td>
                            </tr>
                            {f'<tr><td style="padding: 8px 0; font-weight: bold; color: #555;">Student ID:</td><td style="padding: 8px 0; color: #333;">{student_id}</td></tr>' if student_id else ''}
                            <tr>
                                <td style="padding: 8px 0; font-weight: bold; color: #555;">Status:</td>
                                <td style="padding: 8px 0; color: #28a745; font-weight: bold;">Form Submitted ✓</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div style="background-color: #fff3cd; padding: 20px; border-radius: 8px; border-left: 4px solid #ffc107; margin: 20px 0;">
                        <h3 style="color: #856404; margin-top: 0;">📞 What's Next?</h3>
                        <ul style="color: #856404; margin: 0; padding-left: 20px;">
                            <li>Our counselors will review your application within 2-3 business days</li>
                            <li>You will receive an email notification about the next steps</li>
                            <li>Keep checking your email (including spam folder) for updates</li>
                            <li>If you have any questions, feel free to contact us</li>
                        </ul>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <p style="color: #666; margin: 0;">Thank you for choosing KNCCI Internship Program!</p>
                    </div>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    
                    <div style="text-align: center; color: #666; font-size: 14px;">
                        <p style="margin: 5px 0;"><strong>KNCCI Internship Program Team</strong></p>
                        <p style="margin: 5px 0;">Email: {settings.email_from}</p>
                        <p style="margin: 5px 0;">This is an automated message, please do not reply to this email.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        return await EmailService.send_email(user_email, subject, html_content)

    @staticmethod
    async def send_document_request_email(user_email: str, user_name: str, notes: str):
        """Send document request email"""
        subject = "Documents Required - KNCCI Internship Program"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c5aa0;">Documents Required - KNCCI Internship Program</h2>
                    
                    <p>Dear {user_name},</p>
                    
                    <p>We have reviewed your application for the KNCCI Internship Program. To proceed further, we need you to upload the following documents:</p>
                    
                    <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
                        <h3 style="margin-top: 0; color: #856404;">Counselor Notes:</h3>
                        <p>{notes}</p>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #2c5aa0;">Required Documents:</h3>
                        <ul>
                            <li>Government ID (Aadhar Card/Passport/Driving License)</li>
                            <li>Address Proof</li>
                            <li>Educational Certificate</li>
                        </ul>
                    </div>
                    
                    <p><strong>Please upload these documents through our portal at your earliest convenience.</strong></p>
                    
                    <p>If you have any questions, please contact us.</p>
                    
                    <p>Best regards,<br>
                    <strong>KNCCI Internship Program Team</strong><br>
                    Email: {settings.email_from}</p>
                </div>
            </body>
        </html>
        """
        
        # Try async method first
        print(f"Trying to send document request email to: {user_email}")
        success = await EmailService.send_email(user_email, subject, html_content)
        
        # If async fails, try sync method
        if not success:
            print("Async email failed, trying synchronous method...")
            success = EmailService.send_email_sync(user_email, subject, html_content)
        
        return success

    @staticmethod
    async def send_payment_request_email(user_email: str, user_name: str, amount: float):
        """Send payment request email"""
        subject = "Payment Required - KNCCI Internship Program"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c5aa0;">Payment Required</h2>
                    
                    <p>Dear {user_name},</p>
                    
                    <p>Congratulations! Your documents have been approved. To complete your registration for the KNCCI Internship Program, please make the payment.</p>
                    
                    <div style="background-color: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745;">
                        <h3 style="margin-top: 0; color: #155724;">Payment Details:</h3>
                        <p><strong>Amount:</strong> ₹{amount}</p>
                        <p><strong>Program:</strong> KNCCI Internship Program</p>
                    </div>
                    
                    <p>Please contact our office for payment instructions or visit our portal to complete the payment online.</p>
                    
                    <p>Best regards,<br>
                    <strong>KNCCI Internship Program Team</strong></p>
                </div>
            </body>
        </html>
        """
        
        return await EmailService.send_email(user_email, subject, html_content)

    @staticmethod
    async def send_rejection_email(user_email: str, user_name: str, reason: str):
        """Send application rejection email"""
        subject = "Application Update - KNCCI Internship Program"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c5aa0;">Application Update</h2>
                    
                    <p>Dear {user_name},</p>
                    
                    <p>Thank you for your interest in the KNCCI Internship Program. After careful review, we regret to inform you that we cannot proceed with your application at this time.</p>
                    
                    <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #dc3545;">
                        <h3 style="margin-top: 0; color: #721c24;">Reason:</h3>
                        <p>{reason}</p>
                    </div>
                    
                    <p>We encourage you to apply again in the future when you meet all the requirements.</p>
                    
                    <p>Best regards,<br>
                    <strong>KNCCI Internship Program Team</strong></p>
                </div>
            </body>
        </html>
        """
        
        return await EmailService.send_email(user_email, subject, html_content)

    @staticmethod
    async def send_approval_email(user_email: str, user_name: str, student_id: str = None):
        """Send application approval email"""
        subject = "Congratulations! Application Approved - KNCCI Internship Program"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #28a745;">Congratulations!</h2>
                    
                    <p>Dear {user_name},</p>
                    
                    <p>We are pleased to inform you that your application for the KNCCI Internship Program has been approved!</p>
                    
                    <div style="background-color: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745;">
                        <h3 style="margin-top: 0; color: #155724;">Application Approved</h3>
                        <p><strong>Name:</strong> {user_name}</p>
                        {f'<p><strong>Student ID:</strong> {student_id}</p>' if student_id else ''}
                        <p><strong>Status:</strong> Payment Completed - Approved</p>
                    </div>
                    
                    <p>You will receive further instructions about the program start date and other details soon.</p>
                    
                    <p>Welcome to the KNCCI Internship Program!</p>
                    
                    <p>Best regards,<br>
                    <strong>KNCCI Internship Program Team</strong></p>
                </div>
            </body>
        </html>
        """
        
        return await EmailService.send_email(user_email, subject, html_content)