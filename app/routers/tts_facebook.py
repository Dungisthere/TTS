from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import tempfile
import os
import soundfile as sf
import torch
from transformers import AutoTokenizer, AutoModelForTextToWaveform
from starlette.background import BackgroundTask
from app.models.text_to_speech import TTSRequest

router = APIRouter(prefix="/tts-facebook", tags=["tts-facebook"])

# Khởi tạo model Facebook MMS-TTS
try:
    tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-vie")
    model = AutoModelForTextToWaveform.from_pretrained("facebook/mms-tts-vie")
    model_available = True
except Exception as e:
    print(f"Lỗi khi tải model Facebook MMS-TTS: {str(e)}")
    model_available = False

@router.get("/info")
async def get_model_info():
    """Lấy thông tin về model Facebook MMS-TTS"""
    return {
        "model": "facebook/mms-tts-vie",
        "name": "Facebook MMS-TTS",
        "region": "Miền Nam",
        "available": model_available
    }

@router.post("/generate")
async def generate_speech(request: TTSRequest, background_tasks: BackgroundTasks):
    """Tạo giọng nói từ văn bản với model Facebook MMS-TTS"""
    if not model_available:
        raise HTTPException(
            status_code=503,
            detail="Model Facebook MMS-TTS không khả dụng"
        )
        
    try:
        # Tạo file tạm để lưu âm thanh
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            audio_file = temp_file.name
            
            # Sử dụng model Facebook MMS-TTS
            inputs = tokenizer(request.text, return_tensors="pt")
            with torch.no_grad():
                output = model(**inputs).waveform
            
            audio = output.squeeze().cpu().numpy()
            sampling_rate = model.config.sampling_rate
            sf.write(audio_file, audio, sampling_rate)

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
        # Xóa file tạm nếu có lỗi
        if 'audio_file' in locals() and os.path.exists(audio_file):
            os.remove(audio_file)
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo âm thanh: {str(e)}")
