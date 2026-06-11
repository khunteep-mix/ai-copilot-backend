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
        
        print(f"📻 [Whisper ดิบ]: {raw_text}")

        rag_injection = ""
        if user_context_data:
            rag_injection = f"\n[ข้อมูลอ้างอิงของผู้ใช้]:\n{user_context_data}\n"

        # โหมดที่ไม่ต้องการให้ AI ตอบแทรก
        PASSIVE_MODES = ["podcast", "student"]

        # ----------------------------------------------------
        # 🧠 ล็อคกรง AI: ให้กรองคำอย่างเดียว ห้ามแต่งเรื่อง!
        # ----------------------------------------------------
        dynamic_system_prompt = f"""
คุณคือตัวกรองคำผิดจากการถอดเสียง (Speech-to-text proofreader)
ห้ามแต่งประโยคเพิ่ม ห้ามสนทนาโต้ตอบ ห้ามอธิบาย หน้าที่เดียวของคุณคือ "แก้คำที่สะกดผิดหรือฟังเพี้ยน" ให้ถูกต้องตามบริบท

[บริบทการคุยก่อนหน้า]: {last_context[-500:]}
{rag_injection}

กฎเหล็กขั้นเด็ดขาด (ทำผิดคือพัง):
1. ห้ามใส่คำนำหน้าเด็ดขาด (เช่น ห้ามพิมพ์ 'ข้อความที่แก้ไข:' หรือ 'คำตอบ:')
2. ห้ามใส่เครื่องหมายอัญประกาศ (" ") ครอบข้อความ
3. หากมีคำที่ฟังเพี้ยน ให้อนุมานจากบริบท (เช่นได้ยิน 'เอ็กเตอเวิด' ให้แก้เป็น 'Extrovert')
4. ต้องคงความหมายและโครงสร้างประโยคเดิมของ "ข้อความดิบ" ไว้ทั้งหมด ห้ามแต่งเรื่อง หรือมโนเนื้อหาขึ้นมาใหม่เด็ดขาด
"""
        
        if persona not in PASSIVE_MODES:
            dynamic_system_prompt += """
5. พิเศษเฉพาะคุณ: ถ้า "ข้อความดิบ" มีลักษณะเป็น "คำถาม" หรือ "คำสั่ง" ที่เจาะจงถาม AI ให้คุณแก้คำผิดให้เสร็จก่อน แล้วขึ้นบรรทัดใหม่ พิมพ์ "💡 [AI]: " ตามด้วยคำตอบสั้นๆ (ไม่เกิน 2 ประโยค) 
ถ้าไม่ใช่คำถาม ห้ามพิมพ์ "💡 [AI]: " เด็ดขาด
"""

        try:
            correction = client.chat.completions.create(
                model="llama-3.1-8b-instant", 
                messages=[
                    {"role": "system", "content": dynamic_system_prompt},
                    # บังคับให้ AI โฟกัสแค่ข้อความที่เพิ่งพูด
                    {"role": "user", "content": f"ข้อความดิบ: {raw_text}"} 
                ],
                temperature=0.0, # 🌟 ปรับเป็น 0 เพื่อบังคับไม่ให้ AI มีจินตนาการแต่งเรื่องเอง
            )
            filtered_text = correction.choices[0].message.content.strip()
            
            # 🛡️ ระบบตบเกรียน AI (ดักลบคำนำหน้าที่ AI อาจจะดื้อพิมพ์มา)
            prefixes_to_remove = ["ข้อความที่แก้ไข", "ข้อความดิบ", "แก้ไข:", "ข้อความ:"]
            for prefix in prefixes_to_remove:
                if prefix in filtered_text[:20]: # เช็คแค่ช่วงต้นข้อความ
                    filtered_text = filtered_text.split(":", 1)[-1].strip()
            
            # ถ้า AI ดื้อใส่เครื่องหมายคำพูด (" ") มาครอบ ให้ลบออก
            if filtered_text.startswith('"') and filtered_text.endswith('"'):
                filtered_text = filtered_text[1:-1].strip()

            # แยกส่วนที่จะเอาไปเก็บเป็นประวัติ (ตัดคำตอบ AI ออก)
            text_to_save = filtered_text.split("💡 [AI]:")[0].strip()
            if not text_to_save:
                text_to_save = raw_text
                
            meeting_transcripts.append(text_to_save)
            last_context = (last_context + " | " + text_to_save)[-800:]
            
            print(f"🤖 [AI กรองแล้ว]: {filtered_text}\n" + "-"*50)
            return {"status": "success", "text": filtered_text}
            
        except Exception as e:
            meeting_transcripts.append(raw_text)
            return {"status": "success", "text": raw_text}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}