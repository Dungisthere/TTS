from pydantic import BaseModel

# Định nghĩa dữ liệu đầu vào
class TTSRequest(BaseModel):
    text: str