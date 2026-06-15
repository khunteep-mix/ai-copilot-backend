import os
import PyPDF2
import json
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from groq import Groq
from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents
from collections import defaultdict

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

class SessionData:
    def __init__(self):
        self.meeting_transcripts = []
        self.last_context = "เพิ่งเริ่มการสนทนา"
        self.user_context_data = ""
        self.sentence_buffer = ""
        self.current_speaker = None
        self.last_word_end_time = 0.0

sessions: dict[str, SessionData] = defaultdict(SessionData)

@app.post("/api/upload/context")
async def upload_context(file: UploadFile = File(...), session_id: str = Form(...)):
    try:
        content_text = ""
        if file.filename.lower().endswith('.pdf'):
            reader = PyPDF2.PdfReader(file.file)
            for page in reader.pages:
                text = page.extract_text()
                if text: content_text += text + "\n"
        else:
            content = await file.read()
            content_text = content.decode("utf-8")
        
        sessions[session_id].user_context_data = content_text[:5000]
        print(f"✅ [RAG | {session_id}]: อัปโหลด Context สำเร็จ")
        return {"status": "success", "message": "อัปโหลดข้อมูลสำเร็จ AI พร้อมใช้งานแล้ว"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/meeting/reset")
async def reset_meeting(session_id: str = Form(...)): 
    sessions[session_id] = SessionData()
    print(f"🔄 [System | {session_id}]: ล้างหน่วยความจำเรียบร้อย")
    return {"status": "success"}

# ----------------------------------------------------------------------
# 🌐 REAL-TIME WEBSOCKET STREAMING ENDPOINT 
# ----------------------------------------------------------------------
@app.websocket("/api/stream")
async def websocket_stream(websocket: WebSocket, session_id: str, persona: str = "standard", lang: str = "th"):
    await websocket.accept()
    print(f"🔌 [WS Connected] Session: {session_id} | Mode: {persona} | Lang: {lang}")
    
    session = sessions[session_id]
    dg_connection = deepgram.listen.asynclive.v("1") # ใช้ asynclive

    async def flush_sentence():
        final_text = session.sentence_buffer.strip()
        if not final_text:
            return
        
        speaker_id = session.current_speaker if session.current_speaker is not None else 0
        raw_text = f"[ผู้พูดที่ {speaker_id}]: {final_text}"
        print(f"📻 [Live Sentence]: {raw_text}")
        
        session.sentence_buffer = ""

        if persona in PASSIVE_MODES:
            session.meeting_transcripts.append(raw_text)
            await websocket.send_json({"status": "transcript", "text": raw_text})
            return

        rag_injection = f"\n[ข้อมูลอ้างอิงของผู้ใช้]:\n{session.user_context_data}\n" if session.user_context_data else ""
        dynamic_system_prompt = f"""
        คุณคือผู้ช่วย AI อัจฉริยะในโหมด '{persona}'
        ข้อความเรียลไทม์ที่เพิ่งพูด:
        {raw_text}
        
        {rag_injection}
        
        กฎเหล็กที่ต้องปฏิบัติอย่างเคร่งครัด:
        1. ใช้ข้อมูล [ผู้พูดที่ X] จากข้อความเพื่อจัดระเบียบการสนทนา ถ้าบริบทชัดเจนคุณสามารถเปลี่ยนชื่อผู้พูดได้
        2. วิเคราะห์ว่าข้อความนี้มี "คำถาม" หรือ "ข้อร้องขอ" หรือไม่
        3. ถ้ามี: ให้พิมพ์ข้อความดิบพร้อมชื่อผู้พูด แล้วขึ้นบรรทัดใหม่ พิมพ์ "💡 [AI]: " ตามด้วยคำตอบของคุณ
        4. ถ้าไม่มี: ให้พิมพ์ข้อความดิบพร้อมชื่อผู้พูด ห้ามเติมคำอธิบายอื่นเด็ดขาด
        5. ห้ามใช้เครื่องหมาย ✨ (ดาววิบวับ) เด็ดขาด
        """
        
        try:
            def run_groq():
                return client.chat.completions.create(
                    model="llama-3.1-8b-instant", 
                    messages=[
                        {"role": "system", "content": dynamic_system_prompt},
                        {"role": "user", "content": f"[Context ก่อนหน้า: {session.last_context}]\nตอบตามกฎอย่างเคร่งครัด"}
                    ],
                    temperature=0.1, 
                )
            correction = await asyncio.to_thread(run_groq)
            filtered_text = correction.choices[0].message.content.strip()
            
            session.last_context = filtered_text[-300:]
            session.meeting_transcripts.append(filtered_text)
            
            await websocket.send_json({"status": "transcript", "text": filtered_text})
        except Exception as e:
            session.meeting_transcripts.append(raw_text)
            await websocket.send_json({"status": "transcript", "text": raw_text})

    async def on_transcript(self, result, **kwargs):
        try:
            if not result.channel or not result.channel.alternatives:
                return
            
            alt = result.channel.alternatives[0]
            words = alt.words
            
            if not words:
                if getattr(result, 'speech_final', False):
                    await flush_sentence()
                return

            for w in words:
                if w.end <= session.last_word_end_time:
                    continue
                
                if session.current_speaker is not None and w.speaker != session.current_speaker:
                    await flush_sentence()
                
                session.current_speaker = w.speaker
                session.sentence_buffer += " " + w.word
                session.last_word_end_time = w.end

            if getattr(result, 'speech_final', False):
                await flush_sentence()

        except Exception as e:
            print(f"❌ Error ใน on_transcript: {e}")

    async def on_error(self, error, **kwargs):
        print(f"🔴 Deepgram Live Error: {error}")

    dg_connection.on(LiveTranscriptionEvents.Transcript, on_transcript)
    dg_connection.on(LiveTranscriptionEvents.Error, on_error)

    actual_lang = "th" if lang == "detect" else lang

    options = LiveOptions(
        model="nova-2",
        language=actual_lang,
        smart_format=True,
        diarize=True,
        interim_results=False,
        endpointing=500 
    )

    await dg_connection.start(options)

    try:
        while True:
            data = await websocket.receive()
            if "bytes" in data:
                await dg_connection.send(data["bytes"])
    except WebSocketDisconnect:
        print(f"🔌 [WS Disconnected] ปิดท่อสื่อสารของเซสชัน {session_id}")
    except Exception as e:
        print(f"❌ WS Loop Error: {e}")
    finally:
        try:
            await dg_connection.finish()
        except Exception:
            pass
        print("🔒 ปิดการเชื่อมต่อ Deepgram Streaming เรียบร้อย")

# ----------------------------------------------------------------------

@app.post("/api/meeting/summarize")
async def summarize_meeting(persona: str = Form("standard"), session_id: str = Form(...)):
    session = sessions[session_id]
    if not session.meeting_transcripts:
        return {"status": "empty", "message": "ไม่มีข้อความให้สรุปครับ"}
        
    full_text = "\n".join(session.meeting_transcripts)
    system_prompt = PROMPTS.get(persona, PROMPTS["standard"])["summary"]
    
    rag_injection = f"\n[ข้อมูลอ้างอิงของผู้ใช้]:\n{session.user_context_data}\n" if session.user_context_data else ""
    
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
        sessions[session_id] = SessionData()
        return {"status": "success", "summary": final_summary}
    except Exception as e:
        return {"status": "error", "message": str(e)}