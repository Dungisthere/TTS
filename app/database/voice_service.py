import os
import re
import math
import json
import base64
import hashlib
import subprocess
import tempfile
import shutil
from pathlib import Path
import numpy as np
from scipy import signal
import scipy.ndimage as ndimage
import time

# Thư viện xử lý audio
import soundfile as sf
import librosa
import sounddevice as sd

# Thư viện web
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional

# Import từ models
from app.models.voice_library.vocabulary import VoiceProfile, Vocabulary
from app.models.voice_library.schemas import VoiceProfileCreate, VoiceProfileUpdate
from app.database.user_service import get_user_by_id_or_404

# Đường dẫn lưu trữ file audio
AUDIO_UPLOAD_DIR = Path("audio_uploads")
VOICE_PROFILES_DIR = AUDIO_UPLOAD_DIR / "voice_profiles"
TEMP_DIR = Path("audio_uploads/temp")  # Thư mục lưu trữ file tạm thời

# Đảm bảo thư mục tồn tại
VOICE_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)  # Đảm bảo thư mục temp tồn tại

# Voice Profile Services
def create_voice_profile(user_id: int, profile_data: VoiceProfileCreate, db: Session):
    # Kiểm tra user tồn tại
    user = get_user_by_id_or_404(user_id, db)
    
    # Tạo profile mới
    new_profile = VoiceProfile(
        user_id=user_id,
        name=profile_data.name,
        description=profile_data.description
    )
    
    # Tạo thư mục lưu trữ
    profile_dir = VOICE_PROFILES_DIR / f"user_{user_id}"
    profile_dir.mkdir(exist_ok=True)
    
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    
    return new_profile

def get_voice_profiles_by_user_id(user_id: int, db: Session):
    # Kiểm tra user tồn tại
    get_user_by_id_or_404(user_id, db)
    
    # Lấy danh sách profile
    profiles = db.query(VoiceProfile).filter(VoiceProfile.user_id == user_id).all()
    return profiles

def get_voice_profile_by_id(profile_id: int, user_id: int, db: Session):
    profile = db.query(VoiceProfile).filter(
        VoiceProfile.id == profile_id,
        VoiceProfile.user_id == user_id
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="Voice profile not found")
    
    return profile

def update_voice_profile(profile_id: int, user_id: int, profile_data: VoiceProfileUpdate, db: Session):
    profile = get_voice_profile_by_id(profile_id, user_id, db)
    
    # Cập nhật thông tin
    if profile_data.name is not None:
        profile.name = profile_data.name
    if profile_data.description is not None:
        profile.description = profile_data.description
    
    db.commit()
    db.refresh(profile)
    
    return profile

def delete_voice_profile(profile_id: int, user_id: int, db: Session):
    profile = get_voice_profile_by_id(profile_id, user_id, db)
    
    # Xóa thư mục chứa file âm thanh nếu có
    profile_dir = VOICE_PROFILES_DIR / f"user_{user_id}" / f"profile_{profile_id}"
    if profile_dir.exists():
        shutil.rmtree(profile_dir)
    
    # Xóa profile từ database
    db.delete(profile)
    db.commit()
    
    return True

# Vocabulary Services
def add_vocabulary(profile_id: int, user_id: int, word: str, audio_file: UploadFile, db: Session):
    """
    Thêm từ vựng và file audio vào profile với xử lý âm thanh nâng cao
    """
    temp_path = None
    filepath = None
    
    try:
        profile = get_voice_profile_by_id(profile_id, user_id, db)
        if not profile:
            raise HTTPException(status_code=404, detail="Voice profile not found")

        # Lưu file audio
        file_dir = VOICE_PROFILES_DIR / f"user_{user_id}" / f"profile_{profile_id}"
        file_dir.mkdir(exist_ok=True, parents=True)
        
        # Đảm bảo word được chuẩn hóa (lowercase và loại bỏ khoảng trắng)
        word = word.lower().strip()
        
        # Đảm bảo file luôn có đuôi .wav
        filepath = file_dir / f"{word}.wav"
        temp_path = filepath.with_suffix('.temp')
        
        # Lưu file tạm trước để kiểm tra
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
        
        # Sử dụng hàm validate_and_fix_audio_file để xử lý file audio
        valid, error_msg = validate_and_fix_audio_file(str(temp_path), force_convert=True)
        if not valid:
            raise HTTPException(
                status_code=400,
                detail=f"Không thể xử lý file audio: {error_msg}"
            )
            
        # Nếu valid, di chuyển từ temp_path sang filepath
        os.replace(str(temp_path), str(filepath))
        
        # Xử lý nâng cao cho file âm thanh
        print(f"Đang xử lý nâng cao cho file: {str(filepath)}")
        process_audio_for_vocabulary(str(filepath))
        
        # Tạo hoặc cập nhật record trong database
        vocab = get_vocabulary_by_word(profile_id, user_id, word, db)
        if vocab:
            vocab.audio_path = str(filepath)
            db.commit()
            return vocab
        else:
            db_vocab = Vocabulary(
                voice_profile_id=profile_id,
                word=word,
                audio_path=str(filepath)
            )
            db.add(db_vocab)
            db.commit()
            db.refresh(db_vocab)
            return db_vocab
            
    except HTTPException:
        # Dọn dẹp nếu có lỗi
        if temp_path and os.path.exists(str(temp_path)):
            os.remove(str(temp_path))
        raise
        
    except Exception as e:
        # Dọn dẹp nếu có lỗi
        if temp_path and os.path.exists(str(temp_path)):
            os.remove(str(temp_path))
        if filepath and os.path.exists(str(filepath)):
            os.remove(str(filepath))
            
        print(f"Lỗi khi thêm từ vựng: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi thêm từ vựng: {str(e)}")

def get_vocabularies(profile_id: int, user_id: int, db: Session):
    # Kiểm tra profile tồn tại
    profile = get_voice_profile_by_id(profile_id, user_id, db)
    
    # Lấy danh sách từ vựng
    vocabs = db.query(Vocabulary).filter(Vocabulary.voice_profile_id == profile_id).all()
    return vocabs

def get_vocabulary(profile_id: int, user_id: int, word: str, db: Session):
    # Kiểm tra profile tồn tại
    profile = get_voice_profile_by_id(profile_id, user_id, db)
    
    # Tìm từ vựng
    vocab = db.query(Vocabulary).filter(
        Vocabulary.voice_profile_id == profile_id,
        Vocabulary.word == word
    ).first()
    
    if not vocab:
        raise HTTPException(status_code=404, detail=f"Vocabulary '{word}' not found")
    
    return vocab

def delete_vocabulary(profile_id: int, user_id: int, word: str, db: Session):
    # Tìm từ vựng
    vocab = get_vocabulary(profile_id, user_id, word, db)
    
    # Xóa file audio
    audio_path = Path(vocab.audio_path)
    if audio_path.exists():
        os.remove(audio_path)
    
    # Xóa record
    db.delete(vocab)
    db.commit()
    
    return True

# Text to Speech Service
def text_to_speech(profile_id: int, user_id: int, text: str, db: Session):
    try:
        # Lấy voice profile
        profile = get_voice_profile_by_id(profile_id, user_id, db)
        if not profile:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy voice profile"
            )
            
        # Kiểm tra quyền sở hữu
        if profile.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Bạn không có quyền sử dụng voice profile này"
            )
            
        # Lấy vocabulary của profile
        vocab_query = db.query(Vocabulary).filter(Vocabulary.voice_profile_id == profile_id)
        vocabulary = {item.word: item.audio_path for item in vocab_query.all()}
        
        if not vocabulary:
            raise HTTPException(
                status_code=404,
                detail="Voice profile chưa có vocabulary nào"
            )
            
        # Xử lý text, tách thành từng từ
        # Cải thiện tách từ, hỗ trợ dấu câu và khoảng trắng đặc biệt
        text = text.lower().strip()
        # Xử lý dấu câu - thêm khoảng trắng trước dấu câu để tách riêng
        for punct in [',', '.', '?', '!', ':', ';']:
            text = text.replace(punct, f' {punct}')
        words = [word for word in text.split() if word.strip()]
        
        # Kiểm tra và lọc ra các từ có sẵn trong vocabulary
        available_vocabs = {}
        missing_words = []
        
        for word in words:
            word = word.strip()
            if not word:
                continue
            
            if word in vocabulary:
                available_vocabs[word] = vocabulary[word]
            else:
                missing_words.append(word)
        
        if missing_words:
            raise HTTPException(
                status_code=400,
                detail=f"Các từ sau chưa có trong vocabulary: {', '.join(missing_words)}"
            )
        
        # Biến để lưu các từ đã xử lý
        processed_words = []
        sampling_rate = None
        
        # Đọc tất cả các file audio trước, xử lý từng file để xóa khoảng trống
        for i, word in enumerate(words):
            try:
                audio_path = available_vocabs[word]
                print(f"Đang đọc file: {audio_path}")
                
                # Kiểm tra file tồn tại
                if not os.path.exists(audio_path):
                    raise HTTPException(
                        status_code=404,
                        detail=f"File audio cho từ '{word}' không tồn tại: {audio_path}"
                    )
                
                # Validate file
                valid, error_msg = validate_and_fix_audio_file(audio_path)
                if not valid:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Lỗi với file audio cho từ '{word}': {error_msg}. Vui lòng ghi âm lại từ này."
                    )
                
                # Sử dụng hàm process_audio_for_vocabulary để xử lý audio với phương pháp cắt tối ưu
                temp_output_path = os.path.join(tempfile.gettempdir(), f"proc_{os.path.basename(audio_path)}")
                data, rate = process_audio_for_vocabulary(audio_path, output_path=temp_output_path)
                
                if data is None or rate is None:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Không thể xử lý audio cho từ '{word}'. Vui lòng ghi âm lại."
                    )
                
                if sampling_rate is None:
                    sampling_rate = rate
                elif rate != sampling_rate:
                    # Resampling để khớp tỷ lệ mẫu
                    data = librosa.resample(data, orig_sr=rate, target_sr=sampling_rate)
                
                # Phân tích từ để quyết định xử lý đặc biệt
                is_punctuation = word in [',', '.', '?', '!', ':', ';']
                is_short_word = len(word) <= 2 or len(data) < int(0.2 * sampling_rate)
                is_conjunction = word in ['và', 'hay', 'hoặc', 'nhưng', 'của', 'thì', 'là', 'mà']
                
                # Lưu thông tin để xử lý nối từ
                processed_words.append({
                    'word': word,
                    'data': data,
                    'is_punctuation': is_punctuation,
                    'is_short_word': is_short_word,
                    'is_conjunction': is_conjunction,
                    'position': i,  # Vị trí từ trong câu
                    'is_last': i == len(words) - 1  # Đánh dấu từ cuối
                })
                
                # Xóa file tạm sau khi sử dụng
                if os.path.exists(temp_output_path):
                    os.remove(temp_output_path)
                
            except Exception as e:
                print(f"Lỗi khi xử lý từ '{word}': {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Lỗi khi xử lý từ '{word}': {str(e)}"
                )
        
        # Kết hợp các từ lại với chiến lược nối liền mạch
        print("Đang kết hợp các từ...")
        combined_audio = np.array([])
        
        for i, word_dict in enumerate(processed_words):
            word_data = word_dict['data']
            is_punctuation = word_dict['is_punctuation']
            is_short_word = word_dict['is_short_word']
            is_conjunction = word_dict['is_conjunction'] 
            is_last = word_dict['is_last']
            
            # Xử lý điều kiện ghép từ đầu tiên
            if len(combined_audio) == 0:
                combined_audio = word_data
                continue
            
            # Quyết định crossfade dựa trên loại từ
            if is_punctuation:
                # Thêm khoảng dừng nhỏ trước dấu câu (10ms)
                pause = np.zeros(int(0.01 * sampling_rate))
                combined_audio = np.concatenate([combined_audio, pause, word_data])
            else:
                # Điều chỉnh độ dài crossfade dựa trên loại từ
                if is_short_word or is_conjunction:
                    # Dùng crossfade ngắn hơn cho từ ngắn để tránh mất âm thanh
                    crossfade_duration = 0.03  # 30ms
                else:
                    crossfade_duration = 0.05  # 50ms 
                
                # Sử dụng smooth_audio_transitions để tạo chuyển tiếp mượt mà
                combined_audio = smooth_audio_transitions(
                    combined_audio, 
                    word_data, 
                    sampling_rate, 
                    crossfade_duration=crossfade_duration
                )
                
        # Thêm fade in/out cho toàn bộ câu
        # Dùng cửa sổ Hanning để tạo fade mượt mà ở đầu và cuối
        if len(combined_audio) > 0:
            fade_samples = min(int(0.02 * sampling_rate), len(combined_audio) // 10)
            if fade_samples > 1:
                # Tạo fade in/out
                fade_in = np.hanning(fade_samples * 2)[:fade_samples]
                fade_out = np.hanning(fade_samples * 2)[-fade_samples:]
                combined_audio[:fade_samples] *= fade_in
                combined_audio[-fade_samples:] *= fade_out
        
        # Định dạng file output
        output_path = os.path.join(TEMP_DIR, f"tts_{user_id}_{profile_id}_{int(time.time())}.wav")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Ghi file
        sf.write(output_path, combined_audio, sampling_rate)
        
        return {
            "success": True,
            "audio_path": output_path
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Text-to-speech error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi thực hiện text-to-speech: {str(e)}"
        )

# Hàm xử lý âm thanh
def trim_silence(audio_path, threshold=0.025, min_silence_duration=0.1, pad_ms=50):
    """
    Cắt bỏ khoảng lặng ở đầu và cuối file audio với các tham số nâng cao
    - threshold: ngưỡng cường độ âm thanh (càng nhỏ càng nhạy với âm thanh nhỏ)
    - min_silence_duration: thời lượng tối thiểu của khoảng lặng (giây)
    - pad_ms: khoảng đệm giữ lại ở đầu và cuối (millisecond)
    """
    try:
        print(f"Đang cắt bỏ khoảng lặng cho file: {audio_path}")
        
        # Lưu một bản sao của file gốc để phòng trường hợp có lỗi
        backup_path = f"{audio_path}.backup"
        shutil.copy2(audio_path, backup_path)
        
        # Đọc file audio
        data, rate = librosa.load(audio_path, sr=None)
        
        # Chuyển đổi sang mono nếu là stereo
        if len(data.shape) > 1:
            mono_data = data.mean(axis=1)
        else:
            mono_data = data
        
        # Sử dụng librosa để phát hiện khoảng không lặng
        # Sử dụng threshold thấp hơn để phát hiện tiếng nói nhỏ
        non_silent_intervals = librosa.effects.split(
            mono_data, 
            top_db=30,  # Giá trị thấp hơn để phát hiện tiếng nói nhỏ
            frame_length=512,
            hop_length=128
        )
        
        if len(non_silent_intervals) > 0:
            # Thêm khoảng đệm (ms) để tránh cắt mất âm thanh
            pad_samples = int(pad_ms * rate / 1000)
            start = max(0, non_silent_intervals[0][0] - pad_samples)
            end = min(len(data), non_silent_intervals[-1][1] + pad_samples)
            
            # Cắt data (giữ nguyên kênh nếu là stereo)
            if len(data.shape) > 1:
                trimmed_data = data[start:end, :]
            else:
                trimmed_data = data[start:end]
            
            # Thêm fade-in và fade-out nhẹ để tránh pop/click
            fade_duration = min(30, pad_ms)  # tối đa 30ms
            fade_samples = int(fade_duration * rate / 1000)
            
            if len(trimmed_data) > 2 * fade_samples:
                # Tạo fade windows với hàm Hanning (mượt mà hơn linear)
                fade_in = np.hanning(fade_samples * 2)[:fade_samples]
                fade_out = np.hanning(fade_samples * 2)[-fade_samples:]
                
                if len(trimmed_data.shape) > 1:
                    # Xử lý stereo
                    for channel in range(trimmed_data.shape[1]):
                        trimmed_data[:fade_samples, channel] *= fade_in
                        trimmed_data[-fade_samples:, channel] *= fade_out
                else:
                    # Xử lý mono
                    trimmed_data[:fade_samples] *= fade_in
                    trimmed_data[-fade_samples:] *= fade_out
            
            # Phân tích và chuẩn hóa âm lượng nếu cần
            rms = np.sqrt(np.mean(trimmed_data**2))
            current_db = 20 * np.log10(rms + 1e-9)
            
            # Nếu biên độ quá thấp, tăng cường
            if current_db < -30:
                gain = 10 ** ((-20 - current_db) / 20)
                trimmed_data = trimmed_data * gain
                # Clipping để tránh vượt quá giới hạn
                trimmed_data = np.clip(trimmed_data, -0.95, 0.95)
            
            # Lưu file đã xử lý
            sf.write(audio_path, trimmed_data, rate)
            print(f"Đã cắt giảm khoảng lặng thành công: {audio_path}")
            
            # Xóa bản sao nếu thành công
            os.remove(backup_path)
            return True
        else:
            print(f"Không tìm thấy khoảng không lặng trong file: {audio_path}")
            # Khôi phục file gốc
            os.remove(audio_path)
            os.rename(backup_path, audio_path)
            return False
            
    except Exception as e:
        # Nếu có lỗi, khôi phục file gốc
        print(f"Lỗi khi cắt giảm khoảng lặng: {e}")
        if os.path.exists(backup_path):
            if os.path.exists(audio_path):
                os.remove(audio_path)
            os.rename(backup_path, audio_path)
        return False

def get_vocabulary_by_word(profile_id: int, user_id: int, word: str, db: Session):
    """
    Lấy vocabulary theo từ
    """
    profile = get_voice_profile_by_id(profile_id, user_id, db)
    if not profile:
        return None
        
    return db.query(Vocabulary).filter(
        Vocabulary.voice_profile_id == profile_id,
        Vocabulary.word == word
    ).first()

# Hàm kiểm tra và sửa file audio
def validate_and_fix_audio_file(file_path, force_convert=False):
    """
    Kiểm tra và sửa file audio nếu cần
    - Đọc file bằng librosa (hỗ trợ nhiều định dạng)
    - Lưu lại dưới dạng WAV chuẩn
    """
    file_path = str(file_path)
    if not os.path.exists(file_path):
        print(f"File không tồn tại: {file_path}")
        return False, "File không tồn tại"
    
    # Kiểm tra kích thước file
    if os.path.getsize(file_path) == 0:
        print(f"File rỗng: {file_path}")
        return False, "File rỗng"
    
    # Nếu không cần convert bắt buộc, thử đọc bằng soundfile trước
    if not force_convert:
        try:
            data, rate = sf.read(file_path)
            print(f"File đã ở định dạng phù hợp: {file_path}")
            return True, None
        except Exception as e:
            print(f"Không thể đọc file bằng soundfile: {str(e)}")
            # Tiếp tục với convert
    
    try:
        print(f"Đang convert file: {file_path}")
        # Tạo một file tạm để lưu kết quả
        temp_path = file_path + ".temp.wav"
        
        # Thử đọc bằng librosa (hỗ trợ nhiều định dạng)
        try:
            # Đọc audio với librosa
            y, sr = librosa.load(file_path, sr=None)
            # Librosa đọc thành mảng numpy float -> cần chuyển về int16 cho WAV
            y = (y * 32767).astype(np.int16)
            # Lưu với định dạng WAV
            sf.write(temp_path, y, sr, format='WAV')
        except Exception as e1:
            print(f"Không thể đọc file bằng librosa: {str(e1)}")
            # Thử phương pháp khác - ví dụ sử dụng subprocess gọi ffmpeg
            try:
                import subprocess
                cmd = ['ffmpeg', '-y', '-i', file_path, '-acodec', 'pcm_s16le', temp_path]
                subprocess.run(cmd, check=True, capture_output=True)
                
                # Kiểm tra file đã tạo
                if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                    raise ValueError("Không thể convert file với ffmpeg")
            except Exception as e2:
                print(f"Không thể convert file bằng ffmpeg: {str(e2)}")
                return False, f"Không thể convert file: {str(e1)} | {str(e2)}"
        
        # Kiểm tra file đã convert
        try:
            sf.read(temp_path)
            # Convert thành công, thay thế file cũ
            os.replace(temp_path, file_path)
            print(f"Đã convert thành công file: {file_path}")
            return True, None
        except Exception as e3:
            print(f"File đã convert vẫn không đọc được: {str(e3)}")
            # Xóa file tạm
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False, f"Không thể tạo file audio hợp lệ: {str(e3)}"
            
    except Exception as e:
        print(f"Lỗi khi xử lý file: {str(e)}")
        return False, f"Lỗi khi xử lý file: {str(e)}" 

# Các hàm xử lý âm thanh nâng cao
def denoise_audio(audio_data, sr, reduction_factor=0.15):
    """
    Giảm nhiễu cực kỳ nhẹ để giữ đặc tính giọng nói tự nhiên
    Chỉ giảm nhiễu ở những vùng có biên độ thấp, không ảnh hưởng đến âm thanh chính
    """
    try:
        # Nếu reduction_factor quá nhỏ, không cần xử lý
        if reduction_factor < 0.05:
            return audio_data
        
        # Giới hạn mức độ giảm nhiễu để đảm bảo âm thanh không bị méo
        reduction_factor = min(reduction_factor, 0.2)
            
        # Chuyển sang miền tần số để xử lý
        n_fft = min(2048, len(audio_data))
        if n_fft < 64:  # Nếu audio quá ngắn, trả về nguyên bản
            return audio_data
            
        # Sử dụng cửa sổ hann để giảm thiểu hiệu ứng rò rỉ phổ
        D = librosa.stft(audio_data, n_fft=n_fft, hop_length=n_fft//4, window='hann')
        mag, phase = librosa.magphase(D)
        
        # Ước tính nhiễu từ 5% mẫu có biên độ thấp nhất
        # Phương pháp này chỉ tập trung vào khu vực thực sự là nhiễu
        mag_db = librosa.amplitude_to_db(mag)
        percentile_5 = np.percentile(mag_db, 5)  # Lấy ngưỡng 5% thấp nhất
        
        # Tạo mask chỉ nhắm vào vùng nhiễu, giữ nguyên âm thanh chính
        # Vùng nhiễu được xác định là vùng biên độ thấp dưới ngưỡng
        noise_mask = mag_db < (percentile_5 + 3)  # Chỉ nhắm vào vùng thực sự thấp
        
        # Áp dụng giảm nhiễu rất nhẹ chỉ ở vùng đã xác định
        # Giảm nhẹ hơn nữa so với trước đây
        reduction = np.ones_like(mag)
        reduction[noise_mask] = 1.0 - reduction_factor * 0.8  # Giảm mức độ tác động thêm 20%
        
        # Áp dụng reduction mask, vẫn giữ nguyên phase
        mag_denoised = mag * reduction
        
        # Tái tạo tín hiệu, giữ nguyên phase để không bị méo
        D_denoised = mag_denoised * phase
        audio_denoised = librosa.istft(D_denoised, hop_length=n_fft//4, window='hann')
        
        # Cắt/pad để giữ nguyên độ dài
        if len(audio_denoised) > len(audio_data):
            audio_denoised = audio_denoised[:len(audio_data)]
        elif len(audio_denoised) < len(audio_data):
            # Sử dụng padding đối xứng để tránh hiệu ứng biên
            pad_size = len(audio_data) - len(audio_denoised)
            audio_denoised = np.pad(audio_denoised, (pad_size//2, pad_size - pad_size//2), mode='constant')
        
        # Áp dụng crossfade nhẹ giữa tín hiệu gốc và tín hiệu đã xử lý
        # để đảm bảo không có hiệu ứng không mong muốn
        alpha = 0.3  # Giữ 70% âm thanh gốc, 30% âm thanh đã xử lý
        final_audio = audio_data * (1 - alpha) + audio_denoised * alpha
        
        return final_audio
    except Exception as e:
        print(f"Lỗi khi xử lý giảm nhiễu: {e}")
        return audio_data  # Trả về dữ liệu gốc nếu có lỗi

def normalize_audio(audio_data, target_db=-20):
    """
    Chuẩn hóa âm lượng của file âm thanh
    """
    print("Đang chuẩn hóa âm lượng...")
    try:
        # Tránh chia cho 0
        if np.all(audio_data == 0):
            return audio_data
        
        # Tính toán RMS
        rms = np.sqrt(np.mean(audio_data**2))
        # Chuyển sang dB
        current_db = 20 * np.log10(rms + 1e-9)
        # Tính toán hệ số nhân cần thiết
        gain = 10 ** ((target_db - current_db) / 20)
        # Áp dụng normalization
        normalized_audio = audio_data * gain
        
        # Clipping để đảm bảo không vượt quá -1 đến 1
        normalized_audio = np.clip(normalized_audio, -1.0, 1.0)
        
        return normalized_audio
    except Exception as e:
        print(f"Lỗi khi chuẩn hóa âm lượng: {e}")
        return audio_data  # Trả về dữ liệu gốc nếu có lỗi

def apply_compression(audio_data, threshold=-20, ratio=4, attack=0.005, release=0.15):
    """
    Áp dụng dynamic range compression để làm tín hiệu âm thanh đồng đều hơn
    """
    print("Đang áp dụng compression...")
    try:
        # Chuyển đổi threshold từ dB sang tuyến tính
        threshold_linear = 10 ** (threshold / 20)
        
        # Tính toán biên độ của tín hiệu
        abs_audio = np.abs(audio_data)
        
        # Tạo mask cho các điểm vượt quá threshold
        mask = abs_audio > threshold_linear
        
        # Áp dụng compression
        compressed_audio = np.copy(audio_data)
        compressed_audio[mask] = (
            threshold_linear + 
            (abs_audio[mask] - threshold_linear) / ratio * 
            np.sign(audio_data[mask])
        )
        
        return compressed_audio
    except Exception as e:
        print(f"Lỗi khi áp dụng compression: {e}")
        return audio_data  # Trả về dữ liệu gốc nếu có lỗi

def match_target_amplitude(audio_data, target_dBFS=-20):
    """
    Điều chỉnh biên độ của audio để đạt được mục tiêu dBFS
    """
    try:
        # Tính RMS của audio (căn bậc hai trung bình bình phương)
        rms = np.sqrt(np.mean(audio_data**2))
        
        # Chuyển sang dB
        current_dBFS = 20 * np.log10(rms) if rms > 0 else -120
        
        # Tính toán hệ số khuếch đại cần thiết
        gain = 10 ** ((target_dBFS - current_dBFS) / 20)
        
        # Áp dụng gain
        return audio_data * gain
    except Exception as e:
        print(f"Lỗi khi điều chỉnh biên độ: {e}")
        return audio_data

def smooth_audio_transitions(audio1, audio2, sr, crossfade_duration=0.05):
    """
    Tạo chuyển tiếp mượt mà giữa hai đoạn audio với nhiều cải tiến.
    Tối ưu hóa cho các từ ngắn và dài với nhiều thuật toán khác nhau.
    
    Args:
        audio1: Đoạn audio đầu tiên
        audio2: Đoạn audio thứ hai
        sr: Sample rate
        crossfade_duration: Độ dài crossfade tính bằng giây (mặc định: 0.05s)
    
    Returns:
        Đoạn audio đã được kết hợp với chuyển tiếp mượt mà
    """
    # Xử lý đặc biệt cho các từ ngắn
    is_short_word = len(audio2) < int(0.2 * sr)  # Từ ngắn hơn 200ms
    
    # Điều chỉnh độ dài crossfade tùy thuộc vào độ dài từ
    if is_short_word:
        # Dùng crossfade ngắn hơn cho từ ngắn để bảo toàn âm thanh
        crossfade_duration = min(crossfade_duration, 0.02)  # tối đa 20ms cho từ ngắn
        # Tăng âm lượng cho từ ngắn để nghe rõ hơn 
        audio2 = audio2 * 1.15  # tăng 15% âm lượng
    
    # Tính số mẫu cho crossfade
    crossfade_samples = int(crossfade_duration * sr)
    
    # Kiểm tra độ dài của audio để đảm bảo đủ dài cho crossfade
    if len(audio1) < crossfade_samples or len(audio2) < crossfade_samples:
        # Không đủ độ dài để crossfade, nối trực tiếp với fade in/out nhẹ
        fade_samples = min(len(audio1) // 2, len(audio2) // 2, int(0.01 * sr))
        if fade_samples > 1:
            # Apply fade out cho audio1
            fade_out = np.linspace(1.0, 0.8, fade_samples)
            audio1[-fade_samples:] *= fade_out
            
            # Apply fade in cho audio2
            fade_in = np.linspace(0.8, 1.0, fade_samples)
            audio2[:fade_samples] *= fade_in
        
        # Nối trực tiếp
        return np.concatenate([audio1, audio2])
    
    # Chuẩn bị phần cuối của audio1 và phần đầu của audio2 cho crossfade
    end_audio1 = audio1[-crossfade_samples:]
    start_audio2 = audio2[:crossfade_samples]
    
    # Tối ưu hóa năng lượng giữa 2 phần (cân bằng âm lượng)
    energy_ratio = np.sqrt(np.mean(np.square(end_audio1)) / max(1e-10, np.mean(np.square(start_audio2))))
    if energy_ratio > 1.5 or energy_ratio < 0.67:
        # Nếu có sự chênh lệch lớn về năng lượng, điều chỉnh
        if energy_ratio > 1.5:
            # audio1 to hơn audio2
            normalized_audio2 = audio2 * min(1.5, energy_ratio * 0.8)  # Tăng nhưng có giới hạn
        else:
            # audio2 to hơn audio1
            normalized_audio1 = audio1.copy()
            normalized_audio1[-crossfade_samples:] *= min(1.5, 1/energy_ratio * 0.8)
            audio1 = normalized_audio1
    
    # Tìm điểm chuyển tiếp tối ưu bằng tương quan chéo
    max_shift = min(crossfade_samples // 4, 500)  # Giới hạn dịch chuyển tối đa
    best_corr = -1
    best_shift = 0
    
    # Chỉ tính tương quan nếu từ đủ dài
    if not is_short_word and crossfade_samples > 100:
        for shift in range(-max_shift, max_shift + 1, 5):  # Bước nhảy 5 để tăng tốc độ
            if shift < 0:
                # Dịch audio2 sang trái
                a = end_audio1[:crossfade_samples+shift]
                b = start_audio2[-shift:][:len(a)]
            else:
                # Dịch audio2 sang phải
                a = end_audio1[shift:][:crossfade_samples-shift]
                b = start_audio2[:len(a)]
                
            if len(a) < 50 or len(b) < 50:  # Đảm bảo đủ mẫu để tính tương quan
                continue
                
            # Tính toán và chuẩn hóa tương quan
            corr = np.correlate(a, b, mode='valid')[0] / (np.sqrt(np.sum(a**2) * np.sum(b**2)) + 1e-10)
            
            if corr > best_corr:
                best_corr = corr
                best_shift = shift
    
    # Áp dụng dịch chuyển tối ưu nếu tìm thấy
    if best_shift != 0 and best_corr > 0.1:  # Chỉ áp dụng nếu có tương quan tốt
        if best_shift < 0:
            # Cắt bớt audio1, thêm khoảng trống vào audio2
            audio1 = audio1[:len(audio1)+best_shift]
            audio2 = np.concatenate([np.zeros(-best_shift), audio2])
        else:
            # Cắt bớt audio2, thêm khoảng trống vào audio1
            audio1 = np.concatenate([audio1, np.zeros(best_shift)])
            audio2 = audio2[best_shift:]
        
        # Tính lại crossfade_samples
        crossfade_samples = min(crossfade_samples, len(audio1), len(audio2))
    
    # Tạo cửa sổ crossfade mượt mà với cửa sổ Hanning
    fade_window = np.hanning(crossfade_samples * 2)[crossfade_samples:]
    # Cửa sổ cho audio1 (fade out)
    fade_out = fade_window[::-1]  # đảo ngược cửa sổ để tạo fade out
    # Cửa sổ cho audio2 (fade in)
    fade_in = fade_window
    
    # Phần không crossfade của audio1
    result = audio1[:-crossfade_samples].copy()
    
    # Tính phần crossfade
    crossfade = audio1[-crossfade_samples:] * fade_out + audio2[:crossfade_samples] * fade_in
    
    # Ghép phần crossfade và phần còn lại của audio2
    result = np.concatenate([result, crossfade, audio2[crossfade_samples:]])
    
    # Kiểm tra và xử lý "pop" sound ở điểm chuyển tiếp
    transition_point = len(audio1) - crossfade_samples + len(result) - len(audio1) - len(audio2) + crossfade_samples
    check_window = 100
    if transition_point > check_window and transition_point < len(result) - check_window:
        # Kiểm tra sự thay đổi đột ngột
        pre_trans = result[transition_point-check_window:transition_point]
        post_trans = result[transition_point:transition_point+check_window]
        
        if np.abs(np.mean(pre_trans) - np.mean(post_trans)) > 0.1 * np.max(np.abs(result)):
            # Nếu có thay đổi lớn, áp dụng làm mịn bổ sung
            smoothing_window = np.hanning(check_window*2)
            smoothing_region = result[transition_point-check_window:transition_point+check_window].copy()
            smoothed = smoothing_region * smoothing_window
            result[transition_point-check_window:transition_point+check_window] = smoothed
    
    return result

def enhance_voice(audio_data, sr):
    """
    Cải thiện chất lượng giọng nói
    - Tăng cường dải tần của giọng nói (thường 250Hz-3.5kHz)
    - Giảm các tần số cao gây chói tai
    """
    print("Đang cải thiện chất lượng giọng nói...")
    try:
        # Áp dụng bộ lọc EQ để tăng cường giọng nói
        # Tạo bộ lọc band-pass cho vùng giọng nói
        sos = signal.butter(4, [200, 3500], 'bandpass', fs=sr, output='sos')
        voice_band = signal.sosfilt(sos, audio_data)
        
        # Tạo bộ lọc low-pass để giảm tần số cao
        sos_lowpass = signal.butter(4, 7000, 'lowpass', fs=sr, output='sos')
        high_freqs = signal.sosfilt(sos_lowpass, audio_data)
        
        # Kết hợp
        enhanced = voice_band * 1.5 + high_freqs * 0.7
        
        # Chuẩn hóa lại
        enhanced = normalize_audio(enhanced)
        
        return enhanced
    except Exception as e:
        print(f"Lỗi khi cải thiện giọng nói: {e}")
        return audio_data  # Trả về dữ liệu gốc nếu có lỗi

def process_audio_for_vocabulary(audio_path, output_path=None):
    """
    Xử lý file âm thanh từ vựng, cắt khoảng lặng cực kỳ chặt chẽ đầu/cuối 
    và tạo smooth transitions cho phần ghép nối từ
    """
    try:
        # Đọc file âm thanh
        y, sr = librosa.load(audio_path, sr=None)
        
        # Cắt khoảng lặng đầu và cuối file với tham số hỗ trợ phát hiện tốt hơn
        # Tăng top_db để nhạy hơn với âm thanh yếu và giảm hop_length để phân tích chi tiết hơn
        intervals = librosa.effects.split(y, top_db=33, hop_length=64)
        
        if len(intervals) > 0:
            # Lấy phần không lặng đầu tiên và cuối cùng 
            first_start, first_end = intervals[0]
            last_start, last_end = intervals[-1]
            
            # Thêm padding ngắn hơn để đảm bảo âm thanh không bị cắt mất
            pad = int(0.012 * sr)  # Chỉ 12ms padding, ngắn hơn 30ms trước đây
            
            # Phân tích chi tiết hơn để xác định điểm bắt đầu/kết thúc thực sự của từ
            # bằng cách phân tích 10% đầu/cuối để tìm điểm bắt đầu/kết thúc thực sự
            
            # Phân tích chi tiết điểm bắt đầu
            start_region = y[first_start:first_start + int((first_end-first_start)*0.1)]
            if len(start_region) > 0:
                # Tính RMS của từng khung thời gian nhỏ (2ms)
                frame_length = int(0.002 * sr)
                if frame_length > 0:
                    start_rms = librosa.feature.rms(y=start_region, frame_length=frame_length, hop_length=frame_length)[0]
                    # Tìm điểm bắt đầu âm thanh thực sự (khi RMS vượt qua 10% giá trị lớn nhất)
                    threshold = 0.1 * np.max(start_rms)
                    actual_start_frames = np.where(start_rms > threshold)[0]
                    if len(actual_start_frames) > 0:
                        actual_start = first_start + actual_start_frames[0] * frame_length
                        # Chỉ dùng actual_start nếu nó sớm hơn first_start + 5ms
                        if actual_start < first_start + int(0.005 * sr):
                            first_start = max(0, actual_start - pad//2)  # giảm pad thêm một nửa
            
            # Phân tích chi tiết điểm kết thúc
            end_region = y[last_end - int((last_end-last_start)*0.1):last_end]
            if len(end_region) > 0:
                frame_length = int(0.002 * sr)
                if frame_length > 0:
                    end_rms = librosa.feature.rms(y=end_region, frame_length=frame_length, hop_length=frame_length)[0]
                    # Tìm điểm kết thúc âm thanh thực sự (khi RMS giảm xuống dưới 10% giá trị lớn nhất)
                    threshold = 0.1 * np.max(end_rms)
                    actual_end_frames = np.where(end_rms > threshold)[0]
                    if len(actual_end_frames) > 0:
                        relative_end = actual_end_frames[-1] * frame_length
                        actual_end = (last_end - len(end_region)) + relative_end
                        # Chỉ dùng actual_end nếu nó muộn hơn last_end - 5ms
                        if actual_end > last_end - int(0.005 * sr):
                            last_end = min(len(y), actual_end + pad//2)  # giảm pad thêm một nửa
            
            # Áp dụng fade in/out nhẹ để tránh click
            y_trimmed = y[max(0, first_start - pad):min(len(y), last_end + pad)]
            
            # Áp dụng fade in và fade out nhẹ (8ms)
            fade_samples = min(int(0.008 * sr), len(y_trimmed) // 4)
            if fade_samples > 0:
                fade_in = np.linspace(0, 1, fade_samples)
                fade_out = np.linspace(1, 0, fade_samples)
                
                # Áp dụng fade
                y_trimmed[:fade_samples] *= fade_in
                y_trimmed[-fade_samples:] *= fade_out
            
            # Chỉ áp dụng khử nhiễu rất nhẹ để đảm bảo giữ được chất lượng âm thanh gốc
            y_trimmed = denoise_audio(y_trimmed, sr, reduction_factor=0.15)
            
            if output_path:
                sf.write(output_path, y_trimmed, sr)
            
            return y_trimmed, sr
        else:
            # Nếu không tìm thấy khoảng không lặng, giữ nguyên file gốc
            if output_path:
                sf.write(output_path, y, sr)
            return y, sr
    except Exception as e:
        print(f"Lỗi khi xử lý file âm thanh {audio_path}: {e}")
        # Trả về None để xử lý lỗi bên ngoài
        return None, None 