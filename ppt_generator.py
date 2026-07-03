from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pathlib import Path
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
import subprocess
import platform

class PPTGenerator:
    """PowerPoint 및 보고서 생성 클래스"""
    
    def __init__(self):
        self.prs = None
    
    def create_presentation(self, company, project_name, year, month, photos_path):
        """PPT 프레젠테이션 생성"""
        self.prs = Presentation()
        self.prs.slide_width = Inches(10)
        self.prs.slide_height = Inches(7.5)
        
        # 슬라이드 1: 제목
        self._add_title_slide(company, project_name, year, month)
        
        # 슬라이드 2: 프로젝트 개요
        self._add_overview_slide(company, project_name, year, month)
        
        # 슬라이드 3-5: 사진 슬라이드 (작업전/중/후)
        self._add_photo_slides(photos_path)
        
        # 슬라이드 6: 요약
        self._add_summary_slide()
        
        return self.prs
    
    def _add_title_slide(self, company, project_name, year, month):
        """제목 슬라이드 추가"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])  # 빈 슬라이드
        
        # 배경색
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = None  # 기본색
        
        # 제목
        title_box = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(8), Inches(1))
        title_frame = title_box.text_frame
        title_frame.text = f"{company}"
        title_frame.paragraphs[0].font.size = Pt(60)
        title_frame.paragraphs[0].font.bold = True
        title_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        
        # 부제목
        subtitle_box = slide.shapes.add_textbox(Inches(1), Inches(4), Inches(8), Inches(1))
        subtitle_frame = subtitle_box.text_frame
        subtitle_frame.text = f"{project_name}\n{year}년 {month}월"
        subtitle_frame.paragraphs[0].font.size = Pt(32)
        subtitle_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    
    def _add_overview_slide(self, company, project_name, year, month):
        """프로젝트 개요 슬라이드"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[1])
        title = slide.shapes.title
        title.text = "프로젝트 정보"
        
        # 내용
        content_box = slide.shapes.add_textbox(Inches(1), Inches(1.5), Inches(8), Inches(5))
        text_frame = content_box.text_frame
        
        info = [
            f"회사: {company}",
            f"현장명: {project_name}",
            f"년도: {year}년",
            f"월: {month}월",
            f"작성일: {datetime.now().strftime('%Y년 %m월 %d일')}"
        ]
        
        for i, line in enumerate(info):
            if i == 0:
                p = text_frame.paragraphs[0]
            else:
                p = text_frame.add_paragraph()
            p.text = line
            p.font.size = Pt(24)
            p.level = 0
    
    def _add_photo_slides(self, photos_path):
        """사진 슬라이드 추가 (작업전/중/후)"""
        photos_path = Path(photos_path)
        categories = ['작업전', '작업중', '작업후']
        
        for category in categories:
            slide = self.prs.slides.add_slide(self.prs.slide_layouts[1])
            title = slide.shapes.title
            title.text = f"작업 사진 - {category}"
            
            category_path = photos_path / category
            
            if category_path.exists():
                photos = list(category_path.glob('*'))
                
                # 최대 3개 사진 표시
                for idx, photo in enumerate(photos[:3]):
                    try:
                        left = Inches(1 + idx * 3)
                        top = Inches(2)
                        pic = slide.shapes.add_picture(str(photo), left, top, width=Inches(2.5))
                    except Exception as e:
                        print(f"사진 추가 오류: {e}")
    
    def _add_summary_slide(self):
        """요약 슬라이드"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[1])
        title = slide.shapes.title
        title.text = "작업 완료"
        
        content_box = slide.shapes.add_textbox(Inches(2), Inches(3), Inches(6), Inches(3))
        text_frame = content_box.text_frame
        text_frame.text = "보고서 작성이 완료되었습니다."
        text_frame.paragraphs[0].font.size = Pt(36)
        text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    
    def save_ppt(self, file_path):
        """PPT 파일 저장"""
        self.prs.save(str(file_path))
        return file_path
    
    def ppt_to_pdf(self, ppt_path, pdf_path):
        """PPT를 PDF로 변환"""
        try:
            if platform.system() == 'Windows':
                # Windows: LibreOffice 사용
                subprocess.run([
                    'soffice',
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', str(Path(pdf_path).parent),
                    str(ppt_path)
                ], check=True)
            else:
                # macOS/Linux
                subprocess.run([
                    'libreoffice',
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', str(Path(pdf_path).parent),
                    str(ppt_path)
                ], check=True)
            return pdf_path
        except Exception as e:
            print(f"PDF 변환 오류: {e}")
            return None
    
    def generate_excel(self, company, project_name, year, month, photos_info, file_path):
        """엑셀 파일 생성"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "보고서"
        
        # 헤더 스타일
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        
        # 제목
        ws['A1'] = f"{company} - {project_name} ({year}년 {month}월)"
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:D1')
        
        # 프로젝트 정보
        ws['A3'] = "프로젝트 정보"
        ws['A3'].font = header_font
        ws['A3'].fill = header_fill
        
        row = 4
        info = [
            ("회사", company),
            ("현장명", project_name),
            ("년도", year),
            ("월", month),
            ("작성일", datetime.now().strftime('%Y-%m-%d'))
        ]
        
        for label, value in info:
            ws[f'A{row}'] = label
            ws[f'B{row}'] = value
            row += 1
        
        # 사진 통계
        row += 2
        ws[f'A{row}'] = "사진 통계"
        ws[f'A{row}'].font = header_font
        ws[f'A{row}'].fill = header_fill
        
        row += 1
        ws[f'A{row}'] = "카테고리"
        ws[f'B{row}'] = "개수"
        
        for cell in [ws[f'A{row}'], ws[f'B{row}']]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        
        row += 1
        for category, count in photos_info.items():
            ws[f'A{row}'] = category
            ws[f'B{row}'] = count
            row += 1
        
        # 열 너비 조정
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 15
        
        wb.save(str(file_path))
        return file_path
