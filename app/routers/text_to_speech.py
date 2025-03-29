from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from app.models.text_to_speech import TTSRequest
from app.database.auth import get_current_user
import tempfile
import os
import requests
import soundfile as sf
import torch
from transformers import AutoTokenizer, AutoModelForTextToWaveform
from starlette.background import BackgroundTask

router = APIRouter(prefix="/tts", tags=["text-to-speech"])

# URL của VietTTS API
VIETTTS_URL = "http://localhost:8298"

# Khởi tạo model Facebook MMS-TTS
try:
    tokenizer_mien_nam = AutoTokenizer.from_pretrained("facebook/mms-tts-vie")
    model_mien_nam = AutoModelForTextToWaveform.from_pretrained("facebook/mms-tts-vie")
    mien_nam_available = True
except Exception as e:
    print(f"Lỗi khi tải model miền Nam: {str(e)}")
    mien_nam_available = False

# Kiểm tra kết nối đến VietTTS API
try:
    response = requests.get(f"{VIETTTS_URL}/v1/voices")
    if response.status_code == 200:
        viettts_available = True
        viettts_voices = response.json()
    else:
        viettts_available = False
        viettts_voices = []
except Exception as e:
    print(f"Lỗi khi kết nối VietTTS API: {str(e)}")
    viettts_available = False
    viettts_voices = []

@router.get("/models")
async def get_models():
    """Lấy danh sách các model TTS"""
    models = []
    
    if mien_nam_available:
        models.append({"id": "mien-nam", "name": "Facebook MMS-TTS", "region": "Miền Nam"})
    
    if viettts_available:
        models.append({"id": "mien-bac", "name": "VietTTS", "region": "Miền Bắc"})
    
    return models

@router.get("/voices")
async def get_voices():
    """Lấy danh sách giọng đọc cho VietTTS"""
    if viettts_available:
        return viettts_voices
    return []

@router.post("/generate")
async def generate_speech(
    request: TTSRequest, 
    background_tasks: BackgroundTasks
):
    """Tạo giọng nói từ văn bản với model được chọn mà không cần xác thực"""
    try:
        # Tạo file tạm để lưu âm thanh
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            audio_file = temp_file.name
            
            # Xử lý theo model được chọn
            if request.model_type == "mien-nam" and mien_nam_available:
                # Sử dụng model Facebook MMS-TTS (miền Nam)
                inputs = tokenizer_mien_nam(request.text, return_tensors="pt")
                with torch.no_grad():
                    output = model_mien_nam(**inputs).waveform
                audio = output.squeeze().cpu().numpy()
                sampling_rate = model_mien_nam.config.sampling_rate
                sf.write(audio_file, audio, sampling_rate)
                
            elif request.model_type == "mien-bac" and viettts_available:
                # Sử dụng VietTTS API với giọng được chọn
                voice = request.voice or "cdteam"  # Mặc định là giọng "cdteam"
                
                # Gọi API VietTTS
                data = {
                    "model": "tts-1",
                    "input": request.text,
                    "voice": voice,
                    "speed": request.speed
                }
                
                try:
                    # Debug - ghi log request
                    print(f"Gửi request tới {VIETTTS_URL}/v1/audio/speech với data: {data}")
                    
                    response = requests.post(
                        f"{VIETTTS_URL}/v1/audio/speech",
                        headers={
                            "Authorization": "Bearer viet-tts",
                            "Content-Type": "application/json"
                        },
                        json=data
                    )
                    
                    # Debug - ghi log response status
                    print(f"Status code: {response.status_code}")
                    print(f"Headers: {response.headers}")
                    
                    if response.status_code != 200:
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"VietTTS API lỗi: {response.text}"
                        )
                    
                    # Lưu audio trực tiếp từ content
                    with open(audio_file, 'wb') as f:
                        f.write(response.content)
                    
                except Exception as e:
                    print(f"Lỗi khi gọi VietTTS API: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"Lỗi khi gọi VietTTS API: {str(e)}")
            else:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Model {request.model_type} không được hỗ trợ hoặc không khả dụng"
                )

        # Hàm dọn dẹp để xóa file tạm
        def cleanup():
            if os.path.exists(audio_file):
                os.remove(audio_file)

        # Trả về file âm thanh
        return FileResponse(
            audio_file,
            media_type="audio/wav",
            filename="speech.wav",
            background=BackgroundTask(cleanup)
        )
    
    except Exception as e:
        # Nếu có lỗi, xóa file tạm nếu tồn tại
        if 'audio_file' in locals() and os.path.exists(audio_file):
            os.remove(audio_file)
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo âm thanh: {str(e)}")

@router.get("/test-viettts")
async def test_viettts():
    """API test - Kiểm tra kết nối đến VietTTS API"""
    try:
        response = requests.get(f"{VIETTTS_URL}/v1/voices")
        if response.status_code == 200:
            return {
                "status": "success",
                "message": "Kết nối thành công với VietTTS API",
                "voices": response.json()
            }
        else:
            return {
                "status": "error",
                "message": f"Lỗi khi kết nối với VietTTS API: {response.status_code}",
                "detail": response.text
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Lỗi khi kết nối với VietTTS API: {str(e)}"
        }