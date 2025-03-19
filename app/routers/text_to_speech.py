from fastapi import APIRouter, HTTPException
from transformers import AutoTokenizer, AutoModelForTextToWaveform
import torch
import soundfile as sf
from app.models.text_to_speech import TTSRequest
from fastapi.responses import FileResponse, Response
import tempfile
import base64
import os

# Tạo router
router = APIRouter(prefix="/tts", tags=["text-to-speech"])

# Khởi tạo mô hình và tokenizer
tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-vie")
model = AutoModelForTextToWaveform.from_pretrained("facebook/mms-tts-vie")

@router.post("/generate")
async def generate_tts(request: TTSRequest):
    try:
        # Văn bản từ request
        text = request.text

        # Tokenize văn bản
        inputs = tokenizer(text, return_tensors="pt")

        # Tạo âm thanh
        with torch.no_grad():
            output = model(**inputs).waveform

        # Chuyển đổi waveform thành file âm thanh
        audio = output.squeeze().cpu().numpy()
        sampling_rate = model.config.sampling_rate

        # Tạo file tạm bằng tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            audio_file = temp_file.name
            sf.write(audio_file, audio, sampling_rate)

        # Trả về file trực tiếp
        return FileResponse(
            audio_file,
            filename="output.wav",
            media_type="audio/wav",
            background=task_cleanup(audio_file)  # Xóa file sau khi gửi xong
        )

    except Exception as e:
        # Nếu có lỗi, xóa file tạm nếu tồn tại
        if 'audio_file' in locals() and os.path.exists(audio_file):
            os.remove(audio_file)
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo âm thanh: {str(e)}")

# Hàm xóa file tạm sau khi response được gửi
from starlette.background import BackgroundTask

def task_cleanup(file_path: str):
    def cleanup():
        if os.path.exists(file_path):
            os.remove(file_path)
    return BackgroundTask(cleanup)