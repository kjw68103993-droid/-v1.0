import os
from pathlib import Path
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
import shutil

class PhotoManager:
    """사진 관리 클래스"""
    
    def __init__(self, base_path=None):
        """초기화
        Args:
            base_path: 저장소 기본 경로 (기본값: 사용자 홈/영광조경)
        """
        if base_path is None:
            home = Path.home()
            base_path = home / "영광조경"
        
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def get_project_folder(self, company, year, month):
        """프로젝트 폴더 경로 생성
        예: C:\Users\User\영광조경\수자원공사\2024\1월
        """
        folder = self.base_path / company / str(year) / f"{month}월"
        folder.mkdir(parents=True, exist_ok=True)
        return folder
    
    def get_photo_folder(self, company, year, month, category):
        """사진 폴더 경로
        예: C:\...\1월\사진\작업전
        """
        photo_path = self.get_project_folder(company, year, month) / "사진" / category
        photo_path.mkdir(parents=True, exist_ok=True)
        return photo_path
    
    def get_exif_datetime(self, file_path):
        """EXIF 데이터에서 촬영 시간 추출"""
        try:
            image = Image.open(file_path)
            exif_data = image._getexif()
            
            if not exif_data:
                return None
            
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, tag_id)
                if tag_name == "DateTime":
                    return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
        except Exception as e:
            print(f"EXIF 추출 오류: {e}")
        
        return None
    
    def get_file_datetime(self, file_path):
        """파일 수정 시간 추출"""
        try:
            timestamp = os.path.getmtime(file_path)
            return datetime.fromtimestamp(timestamp)
        except:
            return datetime.utcnow()
    
    def sort_photos_by_timestamp(self, files):
        """사진을 타임스탐프 기준으로 정렬"""
        photo_list = []
        
        for file in files:
            # 임시 저장
            temp_path = f"/tmp/{file.filename}"
            file.save(temp_path)
            
            # EXIF 타임스탐프 추출 (또는 파일 수정 시간)
            dt = self.get_exif_datetime(temp_path) or self.get_file_datetime(temp_path)
            
            photo_list.append({
                'file': file,
                'temp_path': temp_path,
                'timestamp': dt
            })
        
        # 타임스탐프 기준 정렬
        photo_list.sort(key=lambda x: x['timestamp'])
        return photo_list
    
    def auto_organize_photos(self, company, year, month, uploaded_files):
        """사진 300장을 3개 카테고리로 자동 분류
        
        작업전 (Before) | 작업중 (During) | 작업후 (After)
        각각 약 100장씩
        """
        sorted_files = self.sort_photos_by_timestamp(uploaded_files)
        total = len(sorted_files)
        third = total // 3
        
        categories = {
            '작업전': sorted_files[:third],
            '작업중': sorted_files[third:2*third],
            '작업후': sorted_files[2*third:]
        }
        
        saved_photos = {}
        
        for category, files in categories.items():
            saved_photos[category] = []
            folder = self.get_photo_folder(company, year, month, category)
            
            for i, photo_info in enumerate(files, 1):
                # 파일명 생성
                ext = Path(photo_info['file'].filename).suffix
                filename = f"{category}_{i:03d}{ext}"
                filepath = folder / filename
                
                # 저장
                photo_info['file'].save(str(filepath))
                
                saved_photos[category].append({
                    'filename': filename,
                    'filepath': str(filepath),
                    'timestamp': photo_info['timestamp']
                })
                
                # 임시 파일 삭제
                try:
                    os.remove(photo_info['temp_path'])
                except:
                    pass
        
        return saved_photos
    
    def delete_photos(self, company, year, month, category=None):
        """사진 폴더 삭제"""
        if category:
            folder = self.get_photo_folder(company, year, month, category)
        else:
            folder = self.get_project_folder(company, year, month) / "사진"
        
        if folder.exists():
            shutil.rmtree(folder)
            return True
        return False
    
    def get_photo_count(self, company, year, month, category=None):
        """사진 개수 조회"""
        if category:
            folder = self.get_photo_folder(company, year, month, category)
            return len(list(folder.glob('*')))
        else:
            folder = self.get_project_folder(company, year, month) / "사진"
            if folder.exists():
                return len(list(folder.rglob('*')))
        return 0
