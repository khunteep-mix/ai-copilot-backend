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
        # 1. ให้ Whisper ถอดเสียงแบบดิบๆ ออกมาก่อน
        transcription = client.audio.transcriptions.create(
            file=("chunk.webm", audio_bytes),
            model="whisper-large-v3",
            prompt="Multilingual environment. Transcribe the exact spoken words whether it is Thai, English, Japanese, Chinese, Korean, Spanish, French, etc.",
            response_format="text" 
        )
        raw_text = transcription.strip()
        
        if not raw_text:
            return {"status": "success", "text": ""}
        
        print(f"📻 [Whisper Raw]: {raw_text}")
        
        rag_injection = ""
        if user_context_data:
            rag_injection = f"\n[ข้อมูลอ้างอิงของผู้ใช้]:\n{user_context_data}\n"

        # ----------------------------------------------------
        # 🌟 อัปเกรด: AI คิดตามบริบท (Context-Aware Filtering)
        # ----------------------------------------------------
        if persona in PASSIVE_MODES:
            system_task = """
            หน้าที่ของคุณ:
            1. ตรวจสอบและเกลาคำผิดที่เกิดจากการฟังเพี้ยนของระบบ (เช่น 'Exterword' แก้เป็น 'Extrovert') ให้ถูกต้องตามบริบทก่อนหน้า
            2. คืนค่าเฉพาะ 'ข้อความที่ถูกเกลาแล้ว' เท่านั้น ห้ามเพิ่มเนื้อหา ห้ามสรุปความ และห้ามตอบกลับเด็ดขาด
            """
        else:
            system_task = """
            หน้าที่ของคุณ:
            1. ตรวจสอบและเกลาคำผิดที่เกิดจากการฟังเพี้ยน (เช่น 'Exterword' แก้เป็น 'Extrovert') ให้ถูกต้องตามบริบทก่อนหน้า
            2. วิเคราะห์ว่าข้อความนี้มี "คำถาม" หรือ "ข้อร้องขอ" ถึงคุณหรือไม่
            3. ถ้ามี: ให้พิมพ์ข้อความที่เกลาแล้ว ขึ้นบรรทัดใหม่ พิมพ์ "💡 [AI]: " ตามด้วยคำตอบสั้นๆ (1-2 ประโยค)
            4. ถ้าไม่มี: ให้คืนค่าเฉพาะ 'ข้อความที่เกลาแล้ว' เท่านั้น ห้ามเพิ่มเนื้อหา ห้ามสรุปความเด็ดขาด
            """

        dynamic_system_prompt = f"""
        คุณคือ AI ผู้เชี่ยวชาญด้านการตรวจทานและแก้ไขข้อความ (Context-Aware Proofreader) ในโหมด '{persona}'
        
        [บริบทที่กำลังคุยกันอยู่ (Context)]: {last_context}
        {rag_injection}
        
        [ข้อความดิบที่เพิ่งพูด (อาจมีคำที่ฟังเพี้ยน)]: "{raw_text}"
        
        {system_task}
        
        กฎเหล็ก:
        - หากมีคำที่ดูแปลกๆ ให้พิจารณาจาก "บริบทที่กำลังคุยกันอยู่" ว่าควรจะเป็นคำศัพท์ไหน
        - หากมีการเริ่มประเด็นใหม่ หรือเปลี่ยนหัวข้อคุย ให้ปรับตัวคิดตามหัวข้อใหม่ได้เลยทันที
        - ตอบกลับมาแค่ผลลัพธ์สุดท้าย ห้ามมีคำเกริ่นนำใดๆ ทั้งสิ้น
        """
        
        try:
            # ส่งให้ Llama-3.1-8b-instant ช่วยคลีนข้อความด้วยความเร็วแสง
            correction = client.chat.completions.create(
                model="llama-3.1-8b-instant", 
                messages=[
                    {"role": "system", "content": dynamic_system_prompt},
                    {"role": "user", "content": "กรุณาแก้คำผิดตามบริบทและประมวลผลตามกฎ"}
                ],
                temperature=0.1, 
            )
            filtered_text = correction.choices[0].message.content.strip()
            
            # หาก AI ตอบกลับมาแปลกๆ (หลุด) ให้ใช้ข้อความดิบแทน
            if not filtered_text or len(filtered_text) < 2:
                filtered_text = raw_text
            
            # อัปเดตความจำ (Memory) ให้ AI จำเรื่องที่เพิ่งคุยไปได้ยาวขึ้น (จำ 800 ตัวอักษรล่าสุด)
            last_context = (last_context + " | " + filtered_text)[-800:]
            
            # 💡 สำคัญ: เก็บข้อความที่ "ฉลาดและถูกเกลาแล้ว" เข้าสู่ระบบสรุปผล
            meeting_transcripts.append(filtered_text)
            print(f"🧠 [Context-Aware AI]: {filtered_text}\n" + "-"*50)
            
            return {"status": "success", "text": filtered_text}
            
        except Exception as e:
            # Fallback: ถ้า AI มีปัญหา ให้บันทึกและแสดงข้อความดิบจาก Whisper ไปก่อน
            meeting_transcripts.append(raw_text)
            return {"status": "success", "text": raw_text}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}