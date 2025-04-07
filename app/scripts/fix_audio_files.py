#!/usr/bin/env python3
"""
Script để kiểm tra và xử lý nâng cao các file audio đã lưu trong hệ thống
Sử dụng: python -m app.scripts.fix_audio_files
"""

import os
import sys
from pathlib import Path
import importlib.util
import shutil
import argparse

# Thêm thư mục gốc vào PATH để import các module
script_dir = Path(__file__).resolve().parent
root_dir = script_dir.parent.parent
sys.path.insert(0, str(root_dir))

# Import các module cần thiết
from app.database.voice_service import (
    validate_and_fix_audio_file, VOICE_PROFILES_DIR,
    process_audio_for_vocabulary
)
from app.database.database import SessionLocal
from app.models.voice_library.vocabulary import Vocabulary

def scan_directory(directory):
    """Quét thư mục và trả về danh sách các file audio"""
    audio_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.wav', '.mp3', '.flac', '.ogg')):
                audio_files.append(os.path.join(root, file))
    return audio_files

def main():
    """Hàm chính để thực hiện kiểm tra và xử lý nâng cao cho file audio"""
    parser = argparse.ArgumentParser(description='Xử lý nâng cao cho file audio từ vựng')
    parser.add_argument('--validate-only', action='store_true', help='Chỉ kiểm tra định dạng file, không xử lý nâng cao')
    parser.add_argument('--user-id', type=int, help='Chỉ xử lý file của user này')
    parser.add_argument('--profile-id', type=int, help='Chỉ xử lý file của profile này')
    parser.add_argument('--word', type=str, help='Chỉ xử lý file của từ này')
    args = parser.parse_args()
    
    print("Đang quét thư mục để tìm file audio...")
    
    # Tìm đường dẫn file cụ thể nếu có chỉ định user, profile, word
    if args.user_id and args.profile_id and args.word:
        profile_dir = VOICE_PROFILES_DIR / f"user_{args.user_id}" / f"profile_{args.profile_id}"
        word_file = profile_dir / f"{args.word.lower()}.wav"
        if word_file.exists():
            audio_files = [str(word_file)]
        else:
            print(f"Không tìm thấy file cho từ '{args.word}' trong profile {args.profile_id} của user {args.user_id}")
            return
    elif args.user_id and args.profile_id:
        profile_dir = VOICE_PROFILES_DIR / f"user_{args.user_id}" / f"profile_{args.profile_id}"
        if profile_dir.exists():
            audio_files = scan_directory(profile_dir)
        else:
            print(f"Không tìm thấy thư mục profile {args.profile_id} của user {args.user_id}")
            return
    elif args.user_id:
        user_dir = VOICE_PROFILES_DIR / f"user_{args.user_id}"
        if user_dir.exists():
            audio_files = scan_directory(user_dir)
        else:
            print(f"Không tìm thấy thư mục cho user {args.user_id}")
            return
    else:
        audio_files = scan_directory(VOICE_PROFILES_DIR)
    
    print(f"Tìm thấy {len(audio_files)} file audio")
    
    # Xác nhận từ người dùng
    confirm = input(f"Bạn có muốn xử lý {len(audio_files)} file này? (y/n): ")
    if confirm.lower() != 'y':
        print("Hủy xử lý")
        return
    
    success_count = 0
    failed_count = 0
    
    for audio_file in audio_files:
        print(f"\nĐang xử lý: {audio_file}")
        try:
            # Tạo bản sao dự phòng
            backup_path = f"{audio_file}.backup"
            shutil.copy2(audio_file, backup_path)
            
            # Đảm bảo định dạng file hợp lệ
            valid, message = validate_and_fix_audio_file(audio_file)
            if not valid:
                print(f"✗ Không thể validate file: {audio_file}, Lỗi: {message}")
                # Khôi phục từ backup
                shutil.copy2(backup_path, audio_file)
                failed_count += 1
                continue
                
            # Nếu chỉ validate thì bỏ qua xử lý nâng cao
            if not args.validate_only:
                # Xử lý nâng cao cho file âm thanh
                success = process_audio_for_vocabulary(audio_file)
                if success:
                    print(f"✓ Đã xử lý nâng cao thành công: {audio_file}")
                    success_count += 1
                else:
                    print(f"✗ Không thể xử lý nâng cao: {audio_file}")
                    # Khôi phục từ backup
                    shutil.copy2(backup_path, audio_file)
                    failed_count += 1
            else:
                print(f"✓ Đã validate thành công: {audio_file}")
                success_count += 1
                
            # Xóa bản sao nếu thành công
            if os.path.exists(backup_path):
                os.remove(backup_path)
                
        except Exception as e:
            print(f"✗ Lỗi: {e}")
            # Khôi phục từ backup nếu có
            if 'backup_path' in locals() and os.path.exists(backup_path):
                shutil.copy2(backup_path, audio_file)
                os.remove(backup_path)
            failed_count += 1
    
    print("\n=== KẾT QUẢ ===")
    print(f"Tổng số file: {len(audio_files)}")
    print(f"Thành công: {success_count}")
    print(f"Thất bại: {failed_count}")
    
    # Cập nhật database nếu cần
    update_db = input("\nBạn có muốn cập nhật đường dẫn trong database không? (y/n): ")
    if update_db.lower() == 'y':
        print("Đang cập nhật database...")
        db = SessionLocal()
        try:
            # Lấy tất cả vocabulary
            vocabs = db.query(Vocabulary).all()
            print(f"Tìm thấy {len(vocabs)} vocabulary trong database")
            
            updated_count = 0
            for vocab in vocabs:
                path = Path(vocab.audio_path)
                if not path.exists():
                    print(f"❌ File không tồn tại: {vocab.audio_path}, Từ: {vocab.word}")
                    continue
                
                # Kiểm tra path có đúng không
                correct_path = str(path)
                if vocab.audio_path != correct_path:
                    print(f"Cập nhật đường dẫn: {vocab.audio_path} -> {correct_path}")
                    vocab.audio_path = correct_path
                    updated_count += 1
            
            if updated_count > 0:
                db.commit()
                print(f"Đã cập nhật {updated_count} bản ghi trong database")
            else:
                print("Không cần cập nhật database")
                
        finally:
            db.close()
    
    print("\nHoàn tất!")

if __name__ == "__main__":
    main() 