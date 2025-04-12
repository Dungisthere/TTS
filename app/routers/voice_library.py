from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from fastapi.responses import FileResponse
from pathlib import Path
import shutil

from app.database.connection import get_db
from app.models.voice_library.schemas import (
    VoiceProfileCreate, VoiceProfileUpdate, VoiceProfileResponse,
    VocabularyResponse, VocabularyCreate, VocabularyDelete,
    VoiceProfileWithVocabularies, TextToSpeechRequest
)
from app.models.voice_library.vocabulary import Vocabulary, VoiceProfile
from app.database.voice_service import (
    create_voice_profile, get_voice_profiles_by_user_id, get_voice_profile_by_id,
    update_voice_profile, delete_voice_profile, add_vocabulary,
    get_vocabularies, get_vocabulary, delete_vocabulary, text_to_speech,
    validate_and_fix_audio_file, process_audio_for_vocabulary
)

router = APIRouter(prefix="/voice-library", tags=["voice-library"])

# Voice Profile endpoints
@router.post("/profiles", response_model=VoiceProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    user_id: int,
    profile_data: VoiceProfileCreate,
    db: Session = Depends(get_db)
):
    """Tạo profile giọng nói mới cho người dùng"""
    return create_voice_profile(user_id, profile_data, db)

@router.get("/profiles/user/{user_id}", response_model=List[VoiceProfileResponse])
async def get_profiles(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Lấy danh sách profile giọng nói của người dùng"""
    return get_voice_profiles_by_user_id(user_id, db)

@router.get("/profiles/{profile_id}", response_model=VoiceProfileWithVocabularies)
async def get_profile(
    profile_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Lấy thông tin chi tiết profile giọng nói bao gồm từ vựng"""
    profile = get_voice_profile_by_id(profile_id, user_id, db)
    vocabularies = get_vocabularies(profile_id, user_id, db)
    
    # Tạo response với vocabularies - xử lý an toàn hơn
    try:
        # Chuyển đổi dữ liệu Vocabulary sang định dạng dict trước khi tạo Pydantic model
        vocab_list = []
        for vocab in vocabularies:
            vocab_dict = {
                "id": vocab.id,
                "voice_profile_id": vocab.voice_profile_id,
                "word": vocab.word,
                "audio_path": vocab.audio_path,
                "created_at": vocab.created_at,
                "updated_at": vocab.updated_at,
                "exists": False,
                "message": None
            }
            vocab_list.append(vocab_dict)
        
        response = VoiceProfileWithVocabularies(
            id=profile.id,
            user_id=profile.user_id,
            name=profile.name,
            description=profile.description,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            vocabularies=vocab_list
        )
        return response
    except Exception as e:
        # Log và xử lý nếu có lỗi
        print(f"Lỗi khi chuyển đổi dữ liệu: {str(e)}")
        # Trả về profile mà không có từ vựng trong trường hợp lỗi
        return VoiceProfileWithVocabularies(
            id=profile.id,
            user_id=profile.user_id,
            name=profile.name,
            description=profile.description,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            vocabularies=[]
        )

@router.put("/profiles/{profile_id}", response_model=VoiceProfileResponse)
async def update_profile(
    profile_id: int,
    user_id: int,
    profile_data: VoiceProfileUpdate,
    db: Session = Depends(get_db)
):
    """Cập nhật thông tin profile giọng nói"""
    return update_voice_profile(profile_id, user_id, profile_data, db)

@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Xóa profile giọng nói cùng với tất cả từ vựng đã ghi âm"""
    delete_voice_profile(profile_id, user_id, db)
    return None

# Vocabulary endpoints
@router.post("/profiles/{profile_id}/vocabulary", response_model=VocabularyResponse)
async def add_vocab(
    profile_id: int,
    user_id: int,
    word: str = Form(...),
    audio_file: UploadFile = File(...),
    overwrite: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Thêm một từ vựng mới với file âm thanh được ghi âm"""
    # Kiểm tra định dạng file
    if not audio_file.filename.endswith(('.wav', '.mp3', '.ogg')):
        raise HTTPException(status_code=400, detail="Unsupported file format. Only WAV, MP3, and OGG are supported.")
    
    # Kiểm tra xem từ đã tồn tại chưa
    try:
        existing_vocab = db.query(Vocabulary).filter(
            Vocabulary.voice_profile_id == profile_id,
            Vocabulary.word == word
        ).first()
        
        if existing_vocab and not overwrite:
            # Nếu từ đã tồn tại và không yêu cầu ghi đè, trả về thông báo
            return {
                "id": existing_vocab.id,
                "voice_profile_id": existing_vocab.voice_profile_id,
                "word": existing_vocab.word,
                "audio_path": existing_vocab.audio_path,
                "created_at": existing_vocab.created_at,
                "updated_at": existing_vocab.updated_at,
                "exists": True,
                "message": f"Từ vựng '{word}' đã tồn tại. Đặt overwrite=true để ghi đè."
            }
    except Exception as e:
        print(f"Lỗi khi kiểm tra từ vựng tồn tại: {str(e)}")
    
    # Nếu từ chưa tồn tại hoặc yêu cầu ghi đè, thêm hoặc cập nhật từ vựng
    vocab = add_vocabulary(profile_id, user_id, word, audio_file, db)
    
    # Thêm thông tin về việc ghi đè
    if existing_vocab and overwrite:
        vocab.message = f"Đã ghi đè từ vựng '{word}'"
    
    return vocab

@router.get("/profiles/{profile_id}/vocabulary", response_model=List[VocabularyResponse])
async def get_vocabs(
    profile_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Lấy danh sách từ vựng của profile"""
    try:
        # Lấy danh sách từ vựng
        vocabularies = get_vocabularies(profile_id, user_id, db)
        
        # Chuyển đổi sang định dạng dict để tránh lỗi validation
        result = []
        for vocab in vocabularies:
            vocab_dict = {
                "id": vocab.id,
                "voice_profile_id": vocab.voice_profile_id,
                "word": vocab.word,
                "audio_path": vocab.audio_path,
                "created_at": vocab.created_at,
                "updated_at": vocab.updated_at,
                "exists": False,
                "message": None
            }
            result.append(vocab_dict)
        
        return result
    except Exception as e:
        print(f"Lỗi khi lấy danh sách từ vựng: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy danh sách từ vựng: {str(e)}"
        )

@router.get("/profiles/{profile_id}/vocabulary/{word}", response_model=VocabularyResponse)
async def get_vocab(
    profile_id: int,
    user_id: int,
    word: str,
    db: Session = Depends(get_db)
):
    """Lấy thông tin một từ vựng cụ thể"""
    try:
        vocab = get_vocabulary(profile_id, user_id, word, db)
        
        # Chuyển đổi sang dict để đảm bảo tương thích với VocabularyResponse
        return {
            "id": vocab.id,
            "voice_profile_id": vocab.voice_profile_id,
            "word": vocab.word,
            "audio_path": vocab.audio_path,
            "created_at": vocab.created_at,
            "updated_at": vocab.updated_at,
            "exists": False,
            "message": None
        }
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        print(f"Lỗi khi lấy từ vựng: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi lấy từ vựng: {str(e)}"
        )

@router.delete("/profiles/{profile_id}/vocabulary", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vocab(
    profile_id: int,
    user_id: int,
    vocab_data: VocabularyDelete,
    db: Session = Depends(get_db)
):
    """Xóa một từ vựng"""
    delete_vocabulary(profile_id, user_id, vocab_data.word, db)
    return None

@router.get("/profiles/{profile_id}/vocabulary/{word}/audio")
async def get_vocab_audio(
    profile_id: int,
    user_id: int,
    word: str,
    db: Session = Depends(get_db)
):
    """Lấy file âm thanh của một từ vựng"""
    vocab = get_vocabulary(profile_id, user_id, word, db)
    audio_path = vocab.audio_path
    
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(audio_path)

# Text to Speech endpoints
@router.post("/text-to-speech")
async def convert_text_to_speech(
    request: TextToSpeechRequest,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Chuyển đổi văn bản thành giọng nói sử dụng từ điển âm thanh"""
    result = text_to_speech(request.voice_profile_id, user_id, request.text, db)
    
    # Lấy đường dẫn audio từ kết quả trả về dạng dict
    output_path = result.get("audio_path")
    
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=500, detail="Không thể tạo file âm thanh")
    
    return FileResponse(output_path)

@router.post("/repair-audio")
def repair_audio(
    profile_id: int,
    user_id: int,
    word: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Kiểm tra và sửa các file audio đã lưu
    - Nếu không có word: sửa tất cả file audio trong profile
    - Nếu có word: chỉ sửa file audio cho từ đó
    """
    try:
        # Lấy danh sách từ vựng cần kiểm tra
        if word:
            vocab = get_vocabulary(profile_id, user_id, word, db)
            vocabs = [vocab] if vocab else []
        else:
            vocabs = get_vocabularies(profile_id, user_id, db)
        
        # Kết quả
        results = []
        
        # Kiểm tra và sửa từng file
        for vocab in vocabs:
            audio_path = vocab.audio_path
            try:
                valid, error_msg = validate_and_fix_audio_file(audio_path, force_convert=True)
                results.append({
                    "word": vocab.word,
                    "path": audio_path,
                    "success": valid,
                    "message": error_msg if not valid else "Đã sửa thành công"
                })
            except Exception as e:
                results.append({
                    "word": vocab.word,
                    "path": audio_path,
                    "success": False,
                    "message": f"Lỗi: {str(e)}"
                })
        
        # Thống kê
        success_count = sum(1 for r in results if r["success"])
        return {
            "message": f"Đã xử lý {len(results)} file audio, thành công: {success_count}",
            "results": results
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi sửa file audio: {str(e)}"
        )

# Thêm endpoint để xử lý lại các file âm thanh
@router.post("/reprocess-audio")
def reprocess_audio(
    profile_id: int,
    user_id: int,
    word: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Xử lý lại các file âm thanh đã lưu với thuật toán cải tiến
    - Cải thiện chất lượng giọng nói
    - Giảm nhiễu
    - Chuẩn hóa âm lượng
    - Tăng cường dải tần giọng nói
    """
    try:
        # Lấy danh sách từ vựng cần xử lý
        if word:
            vocab = get_vocabulary(profile_id, user_id, word, db)
            vocabs = [vocab] if vocab else []
        else:
            vocabs = get_vocabularies(profile_id, user_id, db)
        
        # Kết quả
        results = []
        
        # Xử lý từng file
        for vocab in vocabs:
            audio_path = vocab.audio_path
            try:
                # Kiểm tra file tồn tại
                if not os.path.exists(audio_path):
                    results.append({
                        "word": vocab.word,
                        "path": audio_path,
                        "success": False,
                        "message": "File không tồn tại"
                    })
                    continue
                
                # Tạo bản sao để xử lý
                backup_path = f"{audio_path}.backup"
                shutil.copy2(audio_path, backup_path)
                
                # Xử lý nâng cao
                success = process_audio_for_vocabulary(audio_path)
                
                if success:
                    results.append({
                        "word": vocab.word,
                        "path": audio_path,
                        "success": True,
                        "message": "Đã xử lý thành công"
                    })
                    # Xóa file backup nếu thành công
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                else:
                    # Khôi phục từ backup nếu thất bại
                    if os.path.exists(backup_path):
                        shutil.copy2(backup_path, audio_path)
                        os.remove(backup_path)
                    
                    results.append({
                        "word": vocab.word,
                        "path": audio_path,
                        "success": False,
                        "message": "Xử lý thất bại, đã khôi phục bản gốc"
                    })
                    
            except Exception as e:
                # Khôi phục từ backup nếu có lỗi
                if 'backup_path' in locals() and os.path.exists(backup_path):
                    shutil.copy2(backup_path, audio_path)
                    os.remove(backup_path)
                
                results.append({
                    "word": vocab.word,
                    "path": audio_path,
                    "success": False,
                    "message": f"Lỗi: {str(e)}"
                })
        
        # Thống kê
        success_count = sum(1 for r in results if r["success"])
        return {
            "message": f"Đã xử lý {len(results)} file audio, thành công: {success_count}",
            "results": results
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi xử lý lại file audio: {str(e)}"
        ) 