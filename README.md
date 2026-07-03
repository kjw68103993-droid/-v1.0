# 영광조경 업무관리시스템 (YG-Manager)

영광조경의 현장 관리, 사진 관리, 보고서 생성을 통합한 업무관리 시스템입니다.

## 🎯 주요 기능

### 1. 현장관리 (📁 Site Management)
- 회사, 현장명, 년도, 월별로 프로젝트 관리
- 프로젝트 정보 조회 및 수정

### 2. 사진관리 (📷 Photo Management)
- **대량 사진 업로드**: 300장 이상 일괄 선택 가능
- **자동정리**: 타임스탐프 기반으로 3개 카테고리로 자동 분류
  - 작업전 (Before): 초기 사진
  - 작업중 (During): 중간 작업 사진
  - 작업후 (After): 완료 사진
- **로컬 저장**: `C:\영광조경\현장명\년도\월\사진\` 폴더 구조

### 3. 보고서 (📄 Report Generation)
- **PPT 생성**: 프로젝트 정보와 사진을 포함한 파워포인트 작성
- **PDF 변환**: PPT → PDF 자동 변환
- **엑셀 생성**: 프로젝트 데이터와 통계를 엑셀로 출력

## 📂 폴더 구조

```
내컴퓨터 (Local Storage)
└── 영광조경/
    ├── 수자원공사/
    │   ├── 2024/
    │   │   ├── 1월/
    │   │   │   ├── 사진/
    │   │   │   │   ├── 작업전/ (작업전_001.jpg ~ 작업전_100.jpg)
    │   │   │   │   ├── 작업중/ (작업중_001.jpg ~ 작업중_100.jpg)
    │   │   │   │   └── 작업후/ (작업후_001.jpg ~ 작업후_100.jpg)
    │   │   │   ├── 수자원공사_2024_1월.ppt
    │   │   │   ├── 수자원공사_2024_1월.pdf
    │   │   │   └── 수자원공사_2024_1월.xlsx
    │   │   └── 2월/
    │   └── 2025/
    └── 다른현장/
```

## 🚀 빠른 시작

### 1. 설치

```bash
# 저장소 클론
git clone https://github.com/kjw68103993-droid/-v1.0.git
cd -v1.0

# 필수 패키지 설치
pip install -r requirements.txt
```

### 2. 실행

```bash
python app.py
```

그 후 브라우저에서 `http://localhost:5000` 접속

### 3. 선택사항: PDF 변환 설정

PPT → PDF 변환을 위해 LibreOffice 설치 필요:

**Windows:**
```bash
choco install libreoffice
```

**macOS:**
```bash
brew install libreoffice
```

**Linux:**
```bash
sudo apt-get install libreoffice
```

## 📋 사용 흐름

### 보고서 생성 프로세스

```
1. 현장 선택/생성
   ├─ 회사명: 수자원공사
   ├─ 현장명: 도로 포장 공사
   ├─ 년도: 2024
   └─ 월: 1

2. 사진 업로드
   └─ 300장 사진 일괄 선택

3. 자동정리
   ├─ 작업전 (~100장)
   ├─ 작업중 (~100장)
   └─ 작업후 (~100장)

4. 보고서 생성
   ├─ PPT 생성
   ├─ PDF 변환
   └─ 엑셀 생성

5. 파일 저장 및 다운로드
   └─ C:\영광조경\수자원공사\2024\1월\
      ├─ 수자원공사_2024_1월.ppt
      ├─ 수자원공사_2024_1월.pdf
      └─ 수자원공사_2024_1월.xlsx
```

## 🔧 기술 스택

- **Backend**: Flask
- **Database**: SQLite (python-pptx, openpyxl)
- **Frontend**: HTML5, CSS3, JavaScript
- **Libraries**:
  - `python-pptx`: PowerPoint 생성
  - `openpyxl`: 엑셀 생성
  - `Pillow`: 이미지 처리
  - `Flask-SQLAlchemy`: ORM

## 📚 API 엔드포인트

### 현장관리
- `GET /api/projects` - 현장 목록
- `POST /api/projects` - 현장 생성

### 사진관리
- `POST /api/upload_photos/<project_id>` - 사진 업로드
- `GET /api/photos/<project_id>` - 사진 조회
- `DELETE /api/photo/<photo_id>` - 사진 삭제

### 보고서
- `POST /api/generate_report/<project_id>` - 보고서 생성
- `GET /download/<project_id>/<file_type>` - 파일 다운로드 (ppt/pdf/excel)
- `GET /open_folder/<project_id>` - 폴더 열기

## 🛠️ 향후 개선 사항

- [ ] 사용자 인증 (로그인)
- [ ] 사진 필터링 및 정렬
- [ ] 사진 태그 기능
- [ ] 보고서 템플릿 커스터마이징
- [ ] 클라우드 저장소 연동 (Google Drive, OneDrive)
- [ ] 모바일 앱

## 📝 라이선스

MIT License

## 👨‍💼 지원

문제 발생 시 [Issues](https://github.com/kjw68103993-droid/-v1.0/issues)에 보고해주세요.
