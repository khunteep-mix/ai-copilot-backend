import os
import PyPDF2
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
app = FastAPI()

# 1. แก้ไข CORS ให้รองรับเว็บจาก Vercel (ทุกโดเมน)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq()

meeting_transcripts = []
last_context = "เพิ่งเริ่มการสนทนา"
user_context_data = "" 

# คลังสมองระดับโลก สำหรับการสรุปผลตอนจบ (Summary Only)
PROMPTS = {
    "standard": {"summary": "สรุปรายงานการประชุมสากลเป็นภาษาไทย จงสรุปโดยละเอียดที่สุด ห้ามละเลยหัวข้อย่อยหรือประเด็นใดๆ ที่มีการพูดถึงแม้จะเพียงเล็กน้อย ให้แตกหัวข้อย่อยออกมาให้ครบถ้วนที่สุด โครงสร้าง: 1. ประเด็นสำคัญ 2. เป้าหมาย 3. Action Items 4. คำถามที่ค้างคา"},
    "interview": {"summary": "สรุปผลสัมภาษณ์ จงสรุปโดยละเอียดที่สุด ห้ามละเลยหัวข้อย่อยหรือประเด็นใดๆ ที่มีการพูดถึงแม้จะเพียงเล็กน้อย ให้แตกหัวข้อย่อยออกมาให้ครบถ้วนที่สุด โครงสร้าง: 1. ภาพรวม 2. คลังคำถามเด็ด 3. จุดเด่นที่ทำได้ดี 4. จุดที่ต้องเตรียมตัวเพิ่ม"},
    "student": {"summary": "สรุปเลกเชอร์ จงสรุปโดยละเอียดที่สุด ห้ามละเลยหัวข้อย่อยหรือประเด็นใดๆ ที่มีการพูดถึงแม้จะเพียงเล็กน้อย ให้แตกหัวข้อย่อยออกมาให้ครบถ้วนที่สุด โครงสร้าง: 🎯 แก่นสำคัญ, 📚 คำศัพท์/ทฤษฎี, 💡 ตัวอย่าง, 📝 สิ่งที่ต้องทบทวน"},
    "secretary": {"summary": "สรุปรายงาน จงสรุปโดยละเอียดที่สุด ห้ามละเลยหัวข้อย่อยหรือประเด็นใดๆ ที่มีการพูดถึงแม้จะเพียงเล็กน้อย ให้แตกหัวข้อย่อยออกมาให้ครบถ้วนที่สุด โครงสร้าง: 📊 ภาพรวม, 🎯 มติที่ประชุม, 👤 Action Items, 📅 Next Steps"},
    "podcast": {"summary": "สรุป Podcast จงสรุปโดยละเอียดที่สุด ห้ามละเลยหัวข้อย่อยหรือประเด็นใดๆ ที่มีการพูดถึงแม้จะเพียงเล็กน้อย ให้แตกหัวข้อย่อยออกมาให้ครบถ้วนที่สุด โครงสร้าง: 🎙️ ธีมหลัก, 💡 Key Takeaways, 💬 วาทะเด็ด, 🔗 แหล่งอ้างอิง"},
    "business": {"summary": "วิเคราะห์ธุรกิจ จงสรุปโดยละเอียดที่สุด ห้ามละเลยหัวข้อย่อยหรือประเด็นใดๆ ที่มีการพูดถึงแม้จะเพียงเล็กน้อย ให้แตกหัวข้อย่อยออกมาให้ครบถ้วนที่สุด โครงสร้าง: 📈 โอกาส, ⚠️ ความเสี่ยง, 💰 ผลกระทบทางการเงิน, 🚀 กลยุทธ์"},
    "sales": {"summary": "สรุปดีล จงสรุปโดยละเอียดที่สุด ห้ามละเลยหัวข้อย่อยหรือประเด็นใดๆ ที่มีการพูดถึงแม้จะเพียงเล็กน้อย ให้แตกหัวข้อย่อยออกมาให้ครบถ้วนที่สุด โครงสร้าง: 🎯 สัญญาณการซื้อ, 💔 Pain Points, 🛡️ ข้อโต้แย้ง, 📞 Follow-up"},
    "tech": {"summary": "สรุป Tech จงสรุปโดยละเอียดที่สุด ห้ามละเลยหัวข้อย่อยหรือประเด็นใดๆ ที่มีการพูดถึงแม้จะเพียงเล็กน้อย ให้แตกหัวข้อย่อยออกมาให้ครบถ้วนที่สุด โครงสร้าง: 💻 สถาปัตยกรรมระบบ, 🐛 ปัญหาที่พบ, 🔧 วิธีแก้ไข, 🚀 แผนพัฒนา"},
    "diplomat": {"summary": "สรุปข้อพิพาท จงสรุปโดยละเอียดที่สุด ห้ามละเลยหัวข้อย่อยหรือประเด็นใดๆ ที่มีการพูดถึงแม้จะเพียงเล็กน้อย ให้แตกหัวข้อย่อยออกมาให้ครบถ้วนที่สุด โครงสร้าง: 🌪️ ความขัดแย้ง, 🤝 ความต้องการลึกๆ, ⚖️ ข้อเสนอประนีประนอม"}
}

# 3. เพิ่มโหมดผู้ฟัง (Podcast) ให้ทำงานลื่นไหล ไม่มี AI แทรก
PASSIVE_MODES = ["podcast"]

@app.post("/api/upload/context")
async def upload_context(file: UploadFile = File(...)):
    global user_context_data
    try:
        content_text = ""
        if file.filename.lower().endswith('.pdf'):
            reader = PyPDF2.PdfReader(file.file)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    content_text += text + "\n"
        else:
            content = await file.read()
            content_text = content.decode("utf-8")
        
        user_context_data = content_text[:5000]
        print("✅ [RAG]: อัปโหลดข้อมูล Context สำเร็จ!")
        return {"status": "success", "message": "อัปโหลดข้อมูลสำเร็จ AI พร้อมใช้งานข้อมูลนี้แล้ว"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 2. เพิ่ม API Reset ป้องกัน Error 404 ตอนเริ่มอัดเสียงใหม่
@app.post("/api/meeting/reset")
async def reset_meeting():
    global meeting_transcripts, last_context
    meeting_transcripts.clear()
    last_context = "เพิ่งเริ่มการสนทนา"
    print("🔄 [System]: ล้างหน่วยความจำเริ่มการประชุมใหม่เรียบร้อย")
    return {"status": "success"}

@app.post("/api/audio/chunk")
async def receive_audio_chunk(file: UploadFile = File(...), persona: str = Form("standard")):
    global meeting_transcripts, last_context, user_context_data
    audio_bytes = await file.read()
    
    if len(audio_bytes) < 1000:
        return {"status": "skipped"}

    try:
        transcription = client.audio.transcriptions.create(
            file=("chunk.webm", audio_bytes),
            model="whisper-large-v3",
            prompt="Multilingual environment. Transcribe the exact spoken words whether it is Thai, English, Japanese, Chinese, Korean, Spanish, French, etc.",
            response_format="text" 
        )
        raw_text = transcription.strip()
        
        if not raw_text:
            return {"status": "success", "text": ""}
        
        print(f"📻 [Whisper]: {raw_text}")
        meeting_transcripts.append(raw_text)
        
        # กฎข้อ 2: ถ้าเป็นโหมด Podcast ให้คืนค่าซับไตเติ้ลเลย
        if persona in PASSIVE_MODES:
            return {"status": "success", "text": raw_text}

        # กฎข้อ 1: โหมดผู้ช่วย ให้ AI วิเคราะห์ว่าควรตอบไหม (ไม่มี ✨)
        rag_injection = ""
        if user_context_data:
            rag_injection = f"\n[ข้อมูลอ้างอิงของผู้ใช้]:\n{user_context_data}\n"

        dynamic_system_prompt = f"""
        คุณคือผู้ช่วย AI อัจฉริยะในโหมด '{persona}'
        ข้อความเรียลไทม์ที่เพิ่งพูด: "{raw_text}"
        {rag_injection}
        
        กฎเหล็กที่ต้องปฏิบัติอย่างเคร่งครัด:
        1. วิเคราะห์ว่าข้อความนี้มี "คำถามที่ต้องการคำตอบ" "ข้อร้องขอ" หรือ "การสั่งงาน" หรือไม่
        2. ถ้ามี: ให้พิมพ์ข้อความดิบ "{raw_text}" แล้วขึ้นบรรทัดใหม่ พิมพ์ "💡 [AI]: " ตามด้วยคำตอบหรือคำแนะนำของคุณ (ไม่เกิน 2 ประโยค)
        3. ถ้าไม่มี (เป็นการพูดคุยทั่วไป): ให้ส่งข้อความดิบ "{raw_text}" กลับไปเลย ห้ามเติมคำอื่นเด็ดขาด
        4. ห้ามใช้เครื่องหมาย ✨ (ดาววิบวับ) หรือโควตเด็ดเด็ดขาด 
        """
        
        try:
            correction = client.chat.completions.create(
                model="llama-3.1-8b-instant", 
                messages=[
                    {"role": "system", "content": dynamic_system_prompt},
                    {"role": "user", "content": f"[Context ก่อนหน้า: {last_context}]\nวิเคราะห์และตอบตามกฎอย่างเคร่งครัด"}
                ],
                temperature=0.1, 
            )
            filtered_text = correction.choices[0].message.content.strip()
            last_context = filtered_text[-300:]
            print(f"🤖 [AI]: {filtered_text}\n" + "-"*50)
            
            return {"status": "success", "text": filtered_text}
            
        except Exception as e:
            return {"status": "success", "text": raw_text}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/meeting/summarize")
async def summarize_meeting(persona: str = "standard"):
    global meeting_transcripts, last_context, user_context_data
    
    if not meeting_transcripts:
        return {"status": "empty", "message": "ไม่มีข้อความให้สรุปครับ"}
        
    full_text = "\n".join(meeting_transcripts)
    system_prompt = PROMPTS.get(persona, PROMPTS["standard"])["summary"]
    
    rag_injection = ""
    if user_context_data:
        rag_injection = f"\n[ข้อมูลอ้างอิงของผู้ใช้]:\n{user_context_data}\n"
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[
                {"role": "system", "content": system_prompt + "\n\nตอบเป็นภาษาไทยที่เป็นทางการ อ่านง่าย มี Emoji ประกอบหัวข้อตามความเหมาะสม" + rag_injection},
                {"role": "user", "content": f"ข้อมูลดิบทั้งหมดที่คุยกัน:\n{full_text}"}
            ],
            temperature=0.3, 
        )
        final_summary = completion.choices[0].message.content
        
        # เคลียร์ข้อมูลทิ้งหลังสรุปผลเสร็จ
        meeting_transcripts = []
        last_context = "เพิ่งเริ่มการสนทนา"
        user_context_data = "" 
        
        return {"status": "success", "summary": final_summary}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}