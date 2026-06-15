import os
import PyPDF2
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from groq import Groq
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
from collections import defaultdict # 🆕 Import เพิ่มสำหรับสร้าง Dictionary ที่ตั้งค่าเริ่มต้นให้อัตโนมัติ

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AI Clients
client = Groq()
deepgram = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))

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

PASSIVE_MODES = ["podcast"]

# ---------------------------------------------------------
# 🆕 1. โครงสร้างข้อมูลสำหรับ 1 Session
# ---------------------------------------------------------
class SessionData:
    def __init__(self):
        self.meeting_transcripts = []
        self.last_context = "เพิ่งเริ่มการสนทนา"
        self.user_context_data = ""

# สร้าง "สมุด" เก็บข้อมูลแต่ละ Session
sessions: dict[str, SessionData] = defaultdict(SessionData)
# ---------------------------------------------------------

@app.post("/api/upload/context")
async def upload_context(
    file: UploadFile = File(...),
    session_id: str = Form(...) # 🆕 รับ session_id 
):
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
        
        # เก็บข้อมูลลงเฉพาะกล่องของ Session นั้น
        sessions[session_id].user_context_data = content_text[:5000]
        print(f"✅ [RAG | {session_id}]: อัปโหลดข้อมูล Context สำเร็จ!")
        return {"status": "success", "message": "อัปโหลดข้อมูลสำเร็จ AI พร้อมใช้งานข้อมูลนี้แล้ว"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/meeting/reset")
async def reset_meeting(session_id: str = Form(...)): # 🆕 รับ session_id
    # ล้างข้อมูลด้วยการสร้างกล่องใหม่ทับกล่องเก่าของ Session นั้น
    sessions[session_id] = SessionData()
    print(f"🔄 [System | {session_id}]: ล้างหน่วยความจำเริ่มการประชุมใหม่เรียบร้อย")
    return {"status": "success"}

@app.post("/api/audio/chunk")
async def receive_audio_chunk(
    file: UploadFile = File(...), 
    persona: str = Form("standard"),
    session_id: str = Form(...),
    lang: str = Form("th") # 💡 รับค่าภาษามาจากหน้าเว็บ
):
    audio_bytes = await file.read()
    
    if len(audio_bytes) < 1000:
        return {"status": "skipped"}

    session = sessions[session_id]

    try:
        payload: FileSource = {"buffer": audio_bytes}
        
        # 💡 เช็คว่าผู้ใช้เลือก Auto-Detect หรือไม่
        if lang == "detect":
            options = PrerecordedOptions(
                model="nova-2",
                detect_language=True, # เปิดโหมดจับภาษาอัตโนมัติ
                smart_format=True,
                diarize=True,
                punctuate=True
            )
        else:
            options = PrerecordedOptions(
                model="nova-2",
                language=lang, # ใช้ภาษา th หรือ en ตามที่ผู้ใช้เลือก
                smart_format=True,
                diarize=True,
                punctuate=True
            )
        
        response = await deepgram.listen.asyncrest.v("1").transcribe_file(payload, options)
        
        words = response.results.channels[0].alternatives[0].words
        if not words:
            return {"status": "success", "text": ""}
            
        current_speaker = words[0].speaker
        speaker_text = ""
        formatted_transcripts = []
        
        for word in words:
            text_word = getattr(word, 'punctuated_word', word.word)
            
            if word.speaker == current_speaker:
                speaker_text += text_word + " "
            else:
                formatted_transcripts.append(f"[ผู้พูดที่ {current_speaker}]: {speaker_text.strip()}")
                current_speaker = word.speaker
                speaker_text = text_word + " "
                
        if speaker_text:
            formatted_transcripts.append(f"[ผู้พูดที่ {current_speaker}]: {speaker_text.strip()}")
        
        raw_text = "\n".join(formatted_transcripts)
        print(f"📻 [Deepgram | {session_id}]:\n{raw_text}")
        
        if persona in PASSIVE_MODES:
            session.meeting_transcripts.append(raw_text)
            return {"status": "success", "text": raw_text}

        rag_injection = f"\n[ข้อมูลอ้างอิงของผู้ใช้]:\n{session.user_context_data}\n" if session.user_context_data else ""

        dynamic_system_prompt = f"""
        คุณคือผู้ช่วย AI อัจฉริยะในโหมด '{persona}'
        ข้อความเรียลไทม์ที่เพิ่งพูด:
        {raw_text}
        
        {rag_injection}
        
        กฎเหล็กที่ต้องปฏิบัติอย่างเคร่งครัด:
        1. ใช้ข้อมูล [ผู้พูดที่ X] จากข้อความเพื่อจัดระเบียบการสนทนา ถ้าบริบทชัดเจนคุณสามารถเปลี่ยนชื่อผู้พูดได้ (เช่น เปลี่ยนเป็น [ผู้สัมภาษณ์] หรือ [ลูกค้า])
        2. วิเคราะห์ว่าข้อความนี้มี "คำถาม" หรือ "ข้อร้องขอ" หรือไม่
        3. ถ้ามี: ให้พิมพ์ข้อความดิบพร้อมชื่อผู้พูด แล้วขึ้นบรรทัดใหม่ พิมพ์ "💡 [AI]: " ตามด้วยคำตอบของคุณ
        4. ถ้าไม่มี (เป็นการพูดคุยทั่วไป): ให้พิมพ์ข้อความดิบพร้อมชื่อผู้พูด ห้ามเติมคำอธิบายอื่นเด็ดขาด
        5. ห้ามใช้เครื่องหมาย ✨ (ดาววิบวับ) เด็ดขาด
        """
        
        try:
            correction = client.chat.completions.create(
                model="llama-3.1-8b-instant", 
                messages=[
                    {"role": "system", "content": dynamic_system_prompt},
                    {"role": "user", "content": f"[Context ก่อนหน้า: {session.last_context}]\nตอบตามกฎอย่างเคร่งครัด"}
                ],
                temperature=0.1, 
            )
            filtered_text = correction.choices[0].message.content.strip()
            
            # อัปเดตข้อมูลของ Session นั้นๆ
            session.last_context = filtered_text[-300:]
            session.meeting_transcripts.append(filtered_text)
            
            print(f"🤖 [AI | {session_id}]: {filtered_text}\n" + "-"*50)
            return {"status": "success", "text": filtered_text}
            
        except Exception as e:
            session.meeting_transcripts.append(raw_text)
            return {"status": "success", "text": raw_text}
            
    except Exception as e:
        print(f"❌ Error in processing audio chunk: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post("/api/meeting/summarize")
async def summarize_meeting(
    persona: str = Form("standard"),
    session_id: str = Form(...) # 🆕 รับ session_id
):
    session = sessions[session_id]
    
    if not session.meeting_transcripts:
        return {"status": "empty", "message": "ไม่มีข้อความให้สรุปครับ"}
        
    full_text = "\n".join(session.meeting_transcripts)
    system_prompt = PROMPTS.get(persona, PROMPTS["standard"])["summary"]
    
    rag_injection = ""
    if session.user_context_data:
        rag_injection = f"\n[ข้อมูลอ้างอิงของผู้ใช้]:\n{session.user_context_data}\n"
    
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
        
        # สรุปเสร็จ ล้างข้อมูลห้องนี้ทิ้งได้เลย
        sessions[session_id] = SessionData()
        
        return {"status": "success", "summary": final_summary}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}