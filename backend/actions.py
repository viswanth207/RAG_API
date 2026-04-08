
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging

from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dummy Contact Table REMOVED.
# We will now look up contacts dynamically via RAG.

def detect_intent(message):
    """
    Detects if the message is a 'call' or 'email' action.
    Returns:
        tuple: (intent_type, target_name) or (None, None)
        intent_type: 'call' | 'email' | None
    """
    msg = message.strip().lower()
    
    # 1. QUESTION FILTER
    question_starters = ["what", "who", "where", "give", "show", "get", "tell"]
    if any(msg.startswith(s) for s in question_starters):
        return None, None

    # 2. CALL INTENT
    call_match = re.search(r"(?:^|\s)(?:call|dial|phone)\s+(.+)$", msg)
    if call_match:
        target = call_match.group(1).strip()
        if " of " in target: 
             return None, None
        return "call", target
    
    # 3. EMAIL INTENT
    clean_msg = re.sub(r"^(?:yes|please|kindly|ok|can you|could you)\s*[,]?\s*", "", msg).strip()

    # Heuristic-based regex matching (No local verification)
    
    # Pattern A: "send email to <answer> ..." - Keyword 'to' is strong
    # "send email to manikanta that..."
    p1 = re.search(r"^send\s+(?:an\s+)?(?:email|mail)\s+to\s+(.+?)\s+(?:saying|with|about|that)?\s*:?\s*(.+)$", clean_msg)
    if p1:
        return "email", (p1.group(1).strip(), p1.group(2).strip())

    # Pattern B: "email <message> to <name>" - Keyword 'to' is strong
    p2 = re.search(r"^(?:email|mail)\s+(.+)\s+to\s+(.+)$", clean_msg)
    if p2:
        return "email", (p2.group(2).strip(), p2.group(1).strip())

    # Pattern C: "send <message> to <name> via email" - Keyword 'via email' matches intent, 'to' matches name
    p3 = re.search(r"^send\s+(.+)\s+to\s+(.+?)\s+via\s+(?:email|mail)$", clean_msg)
    if p3:
        return "email", (p3.group(2).strip(), p3.group(1).strip())

    # Pattern D: Direct Command: "mail <name> <message>" (Weakest, usage depends on word count)
    # "mail manikanta something"
    p4 = re.search(r"^(?:email|mail)\s+([a-zA-Z0-9_@.]+?)\s+(.+)$", clean_msg)
    if p4:
        first_word = p4.group(1).strip()
        rest = p4.group(2).strip()
        # Heuristic: Name is usually short.
        if len(first_word.split()) <= 3:
            return "email", (first_word, rest)

    return None, None

async def execute_action(intent, target, assistant_config=None):
    """
    Executes the detected action using RAG for contact lookup if needed.
    
    Args:
        intent: 'call' or 'email'
        target: name (str) for call, or (name, body) tuple for email
        assistant_config: Loaded configuration (dict) containing vector_store, etc.
        
    Returns:
        dict: Response dictionary matching the specified JSON structure.
    """
    try:
        contact_email = None
        contact_phone = None
        contact_name = None
        
        # Helper RAG function
        async def find_contact_info_rag(name, info_type):
            if not assistant_config: 
                return None
            try:
                # We need to use the engine.chat method which expects config
                from backend.assistant_engine import AssistantEngine
                groq_api_key = os.getenv("GROQ_API_KEY")
                model_name = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
                
                if not groq_api_key: return None
                
                engine = AssistantEngine(groq_api_key, model_name)
                
                # We construct a query to find the contact info
                query = f"What is the {info_type} of {name}? Return ONLY the {info_type} value. If not found, imply it is not found."
                
                # Use engine.chat which uses the vector store in assistant_config
                # This is a synchronous call, but that's fine.
                result = engine.chat(assistant_config, query)
                
                answer = result.get("response", "")
                
                # Cleanup answer
                clean_ans = answer.strip()
                
                # If the answer is too long or vague, try to extract specific format
                if info_type == "email":
                     em_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", clean_ans)
                     if em_match: return em_match.group(0)
                elif info_type == "phone":
                     ph_match = re.search(r"\+?\d[\d\s-]{8,15}\d", clean_ans)
                     if ph_match: return ph_match.group(0)
                
                # Heuristic: If answer is short enough (likely just the value), return it.
                if len(clean_ans) < 100 and "not found" not in clean_ans.lower():
                    return clean_ans
                    
                return None
            except Exception as e:
                logger.error(f"RAG search error: {e}")
                return None

        if intent == "call":
            name = target
            contact_name = name
            
            # Direct phone check
            if re.match(r"^\+?\d{10,15}$", name):
                contact_phone = name
            else:
                contact_phone = await find_contact_info_rag(name, "phone number")
            
            if not contact_phone:
                return {
                    "type": "error",
                    "message": f"Sorry, I couldn't find a phone number for {name}.",
                    "data": "Contact not found via RAG."
                }
            
            return {
                "type": "action",
                "action": "open_whatsapp",
                "phone": contact_phone
            }
            
        elif intent == "email":
            name, body = target
            contact_name = name
            
            # Direct email check
            if "@" in name and "." in name:
                contact_email = name
            else:
                contact_email = await find_contact_info_rag(name, "email")
            
            if not contact_email:
                return {
                    "type": "error",
                    "message": f"Sorry, I couldn't find an email address for {name}.",
                    "data": "Contact not found via RAG."
                }
            
            # ------------------------------------------------------------------
            # AI Refinement of Email Content & Subject
            # ------------------------------------------------------------------
            try:
                from backend.assistant_engine import AssistantEngine
                
                # Fetch API Key/Model just like main.py
                groq_api_key = os.getenv("GROQ_API_KEY")
                model_name = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
                
                if groq_api_key:
                    logger.info("Refining email content with AI...")
                    engine = AssistantEngine(groq_api_key, model_name)
                    
                    prompt = f"""
                    You are a professional email assistant.
                    
                    User Instruction: "{body}"
                    
                    Your Task:
                    1. rewrite the instruction into a professional email body addressed directly to the recipient.
                    2. CRITICAL: Change third-person references to the recipient (he/she/him/her) to second-person (You/Your).
                       Example: "He should meet" -> "You should meet".
                    3. Do not repeat the original wording verbatim if it's awkward or informal.
                    4. Keep it short and professional.
                    5. Output ONLY the body paragraphs. 
                    6. Include a polite closing sentence regarding the next steps (e.g. "Let me know if you have any questions", "Looking forward to your reply", or "Thank you") ONLY if appropriate for the context.
                    7. Do NOT include a Subject line.
                    8. Do NOT include a salutation (like "Hi Name").
                    9. Do NOT include a formal sign-off (like "Best regards") or signature.
                    
                    Output:
                    <Body Paragraphs and Closing Sentence>
                    """
                    
                    # We use a simple direct invocation since we don't need RAG context here
                    response = engine.llm.invoke(prompt).content
                    refined_body = response.strip()
                    
                    # Safety cleanup: remove common email artifacts if AI ignores instructions
                    refined_body = re.sub(r"^Subject:.*\n?", "", refined_body, flags=re.IGNORECASE).strip()
                    refined_body = re.sub(r"^(Hi|Hello|Dear) .*\n?", "", refined_body, flags=re.IGNORECASE).strip()
                    refined_body = re.sub(r"(Best regards|Sincerely|Thanks|Cheers).*", "", refined_body, flags=re.IGNORECASE | re.DOTALL).strip()
                    
                    if refined_body:
                        body = refined_body
                        
                    logger.info("AI Refinement Complete.")
            except Exception as e:
                logger.error(f"AI Refinement Failed: {str(e)}")
                # Fallback to original actions (manual cleanup) if AI fails
                display_body = body.strip()
                if display_body.lower().startswith("that "):
                    display_body = display_body[5:].strip()
                lower_body = display_body.lower()
                if lower_body.startswith("he ") or lower_body.startswith("she ") or lower_body.startswith("they "):
                    first_space = display_body.find(' ')
                    if first_space != -1:
                        display_body = "You" + display_body[first_space:]
                if display_body:
                    body = display_body[0].upper() + display_body[1:]
            
            # Send Email
            email_result = send_email_smtp(contact_email, body)
            
            if email_result is True:
                return {
                    "type": "success",
                    "message": f"Email sent successfully to {contact_name} ({contact_email})."
                }
            else:
                return {
                    "type": "error",
                    "message": f"Failed to send email: {email_result}",
                    "data": f"SMTP failure: {email_result}"
                }
                
    except Exception as e:
        logger.error(f"Action execution error: {str(e)}")
        return {
            "type": "error",
            "message": "Sorry, an error occurred while processing your request.",
            "data": str(e)
        }

    return None

def send_email_smtp(to_email, body):
    """Sends an email using SMTP and environment variables."""
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")
    
    if not email_user or not email_pass:
        logger.error("EMAIL_USER or EMAIL_PASS environment variables are not set.")
        # For simulation purposes if env vars are missing, we might want to return True or False.
        # But per requirements: "Do NOT auto-send email without checking contact existence." (Done above)
        # "Use environment variables for credentials."
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = email_user
        msg['To'] = to_email
        msg['Subject'] = "Task Update from Dynamic AI Assistant"
        
        # Professional Conversational HTML Template
        # Professional Conversational HTML Template
        sender_name = "Dynamic AI Assistant"
        
        final_body = body
        if final_body.lower().startswith("that "):
             final_body = final_body[5:].strip()
             if final_body:
                 final_body = final_body[0].upper() + final_body[1:]
                 
        html_content = f"""
        <html>
          <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
              <p>Hi,</p>
              
              <p>I hope you are doing well.</p>
              
              <p>{final_body}</p>
              
              <div style="margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px;">
                <p style="color: #555; font-weight: bold;">Best regards,</p>
                <p style="color: #555;">{sender_name}</p>
              </div>
            </div>
          </body>
        </html>
        """
        
        # Plain text fallback
        plain_text = f"Hi,\n\nI hope you are doing well.\n\n{final_body}\n\nBest regards,\n{sender_name}"
        
        msg.attach(MIMEText(plain_text, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        # Connect to Gmail SMTP (Standard port 587 for TLS)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.set_debuglevel(1)  # Enable debug output
        server.starttls()
        server.login(email_user, email_pass)
        text = msg.as_string()
        server.sendmail(email_user, to_email, text)
        server.quit()
        logger.info(f"Email sent successfully to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication Error: {str(e)}")
        return f"Authentication Failed: Check EMAIL_USER and App Password. Details: {str(e)}"
    except Exception as e:
        logger.error(f"SMTP Error: {str(e)}")
        return f"SMTP Error: {str(e)}"
