from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import EmailPreset, Supplier
from ..schemas import EmailPresetCreate, EmailPresetResponse
from ..gemini_client import generate_content as gemini_generate
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json

router = APIRouter()

# Presets CRUD
@router.get("/presets", response_model=list[EmailPresetResponse])
def get_presets(db: Session = Depends(get_db)):
    return db.query(EmailPreset).all()
@router.post("/presets", response_model=EmailPresetResponse)
def create_preset(preset: EmailPresetCreate, db: Session = Depends(get_db)):
    db_preset = EmailPreset(**preset.dict())
    db.add(db_preset)
    db.commit()
    db.refresh(db_preset)
    return db_preset

@router.put("/presets/{id}")
def update_preset(id: int, preset: EmailPresetCreate, db: Session = Depends(get_db)):
    db_preset = db.query(EmailPreset).filter(EmailPreset.id == id).first()
    if not db_preset: raise HTTPException(404, detail="Preset not found")
    db_preset.name = preset.name
    db_preset.subject = preset.subject
    db_preset.body = preset.body
    db_preset.preset_type = preset.preset_type
    db.commit()
    return db_preset

@router.delete("/presets/{id}")
def delete_preset(id: int, db: Session = Depends(get_db)):
    db_preset = db.query(EmailPreset).filter(EmailPreset.id == id).first()
    if not db_preset: raise HTTPException(404, detail="Preset not found")
    db.delete(db_preset)
    db.commit()
    return {"status": "deleted"}

# Gemini Generation
@router.post("/generate")
def generate_email(prompt: str = Body(..., embed=True), supplier_info: dict = Body(..., embed=True)):
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        if os.getenv("DEV_MODE") == "True":
             return {"generated_text": "Subject: Nabídka spolupráce\n\nDobrý den,\n\nNašel jsem vaši firmu..."}
        raise HTTPException(500, "Gemini API Key missing")
    
    # Construct a rich prompt
    full_prompt = f"""
    Jsi asistent pro nákupčího e-shopu. Tvým úkolem je napsat profesionální email dodavateli.

    Uživatelský pokyn: {prompt}

    Informace o dodavateli:
    Název: {supplier_info.get('name')}
    Klíčové slovo hledání: {supplier_info.get('keyword')}
    Popis: {supplier_info.get('description', 'N/A')}
    Web: {supplier_info.get('website', 'N/A')}

    Email by měl být v češtině. Musí být zdvořilý a přesvědčivý.
    Prosím vygeneruj POUZE text emailu, včetně předmětu na prvním řádku ve formátu "Předmět: ...".
    """

    try:
        generated_text = gemini_generate(gemini_key, full_prompt, primary_model="gemini-1.5-flash")
        return {"generated_text": generated_text}
    except Exception as e:
        raise HTTPException(500, detail=str(e))

# Sending
@router.post("/send")
def send_email_endpoint(
    supplier_id: int = Body(...), 
    subject: str = Body(...), 
    body: str = Body(...),
    db: Session = Depends(get_db)
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(404, "Supplier not found")
        
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASSWORD") # App Password or SMTP password
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 465))
    
    target_email = supplier.email
    if not target_email:
        # In dev mode allow sending even without email to test flow? No, better warn.
        # But maybe user inputted email in UI? 
        # For now assume supplier.email is set.
        pass
        
    # If the user provides an email in the request (override), use that?
    # The UI typically allows editing, but here we just take Supplier ID.
    # Let's assume the frontend might want to pass the email too if it was edited.
    # For now, stick to DB email.
    if not target_email:
         return {"status": "error", "message": "Supplier has no email address saved."}

    if not sender_email or not sender_password:
        return {"status": "error", "message": "Email credentials not configured in .env file"}

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = target_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        supplier.status = "contacted"
        db.commit()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(500, detail=str(e))
