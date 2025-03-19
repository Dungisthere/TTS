from fastapi import APIRouter
from fastapi import FastAPI, File, UploadFile, Header, HTTPException, Request, Form  # noqa: E402, F401
from fastapi.responses import FileResponse  # noqa: E402

from uuid import uuid4

from app.models.file_upload import FileUpload
from app.security.security import get_api_key
# from app.service.gmail import Gmail
from app.config import settings
# from app.models.mail import Mail


import os
import shutil

# Tạo router cho người dùng
router = APIRouter(prefix="/upload-file", tags=["file-upload"])


@router.post("/upload/", response_model=FileUpload)
async def upload_file(
    request: Request,  # Đối tượng Request để lấy thông tin từ header
    file: UploadFile = File(...),  # Tệp được upload
    api_key: str = get_api_key,  # Khóa API để xác thực
    mail_to: str = Form(""),  # Địa chỉ email người nhận (nếu có)
    mail_title: str = Form(""),  # Tiêu đề email (nếu có)
    mail_content: str = Form(""),  # Nội dung email (nếu có)
):
    """
    API để upload tệp và gửi email với liên kết tải xuống (nếu có).

    Tham số:
    - `file`: Tệp được upload cần lưu trữ.
    - `api_key`: Khóa API dùng để xác thực yêu cầu.
    - `mail_to`: Địa chỉ email người nhận (nếu có).
    - `mail_title`: Tiêu đề email (nếu có).
    - `mail_content`: Nội dung email (nếu có).

    Trả về:
    - `filename`: Tên tệp đã upload.
    - `download_url`: URL để tải xuống tệp.
    - `mail`: Địa chỉ email người nhận (nếu đã gửi email).

    Nếu `mail_to` được cung cấp, email sẽ được gửi đến địa chỉ đó với liên kết tải xuống tệp.
    """
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid4()}{file_extension}"
    folder_path = os.path.join(os.path.join(settings.DIR_ROOT, "utils","download"))
    os.makedirs(folder_path) if not os.path.exists(folder_path) else folder_path
    file_path = os.path.join(folder_path, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    download_url = f"{router.prefix}/download/{unique_filename}"

    # if mail_to != "":
    #     domain = request.headers.get("Host")
    #     mail_content = mail_content + "\n" + f"url: {domain}{download_url}"

    #     # Gmail.send_email(
    #     #     Mail(mail_to=mail_to, mail_title=mail_title, mail_noi_dung=mail_content)
    #     # )

    return FileUpload(filename=file.filename, download_url=download_url, mail=mail_to)


@router.get("/download/{filename}")
async def download_file(filename: str):
    """
    API để tải xuống tệp.

    Tham số:
    - `filename`: Tên tệp cần tải xuống.

    Trả về:
    - Nếu tệp tồn tại, trả về tệp dưới dạng phản hồi tải xuống.
    - Nếu tệp không tồn tại, trả về lỗi 404 với thông báo "File not found".
    """
    file_path = os.path.join(os.path.join(settings.DIR_ROOT, "utils","download"), filename)
    if os.path.exists(file_path):
        return FileResponse(
            path=file_path, filename=filename, media_type="application/octet-stream"
        )
    raise HTTPException(status_code=404, detail="File not found")