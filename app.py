from flask import Flask, render_template, request, jsonify, send_file, url_for
from flask_sqlalchemy import SQLAlchemy
from database import db, Project, Photo, Report
from photo_manager import PhotoManager
from ppt_generator import PPTGenerator
from pathlib import Path
from datetime import datetime
import os
import subprocess
import platform

app = Flask(__name__)

# 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yg_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

db.init_app(app)

# 매니저 초기화
photo_manager = PhotoManager()
ppt_generator = PPTGenerator()

@app.before_request
def create_tables():
    """데이터베이스 테이블 생성"""
    db.create_all()

# ==================== 대시보드 ====================

@app.route('/')
def dashboard():
    """대시보드"""
    projects = Project.query.all()
    return render_template('dashboard.html', projects=projects)

# ==================== 현장관리 ====================

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """현장 목록 조회"""
    projects = Project.query.all()
    return jsonify([{
        'id': p.id,
        'company': p.company,
        'project_name': p.project_name,
        'year': p.year,
        'month': p.month,
        'created_at': p.created_at.isoformat()
    } for p in projects])

@app.route('/api/projects', methods=['POST'])
def create_project():
    """새 현장 생성"""
    data = request.json
    
    project = Project(
        company=data.get('company'),
        project_name=data.get('project_name'),
        year=data.get('year'),
        month=data.get('month'),
        description=data.get('description', '')
    )
    
    db.session.add(project)
    db.session.commit()
    
    # 폴더 생성
    photo_manager.get_project_folder(project.company, project.year, project.month)
    
    return jsonify({
        'id': project.id,
        'status': 'success',
        'message': '현장이 생성되었습니다.'
    }), 201

# ==================== 사진관리 ====================

@app.route('/api/upload_photos/<int:project_id>', methods=['POST'])
def upload_photos(project_id):
    """사진 업로드 및 자동정리"""
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'status': 'error', 'message': '프로젝트를 찾을 수 없습니다.'}), 404
    
    files = request.files.getlist('photos')
    if not files:
        return jsonify({'status': 'error', 'message': '파일을 선택하세요.'}), 400
    
    try:
        # 사진 자동정리
        organized = photo_manager.auto_organize_photos(
            project.company,
            project.year,
            project.month,
            files
        )
        
        # DB에 저장
        for category, photos in organized.items():
            for photo_info in photos:
                photo = Photo(
                    project_id=project_id,
                    filename=photo_info['filename'],
                    file_path=photo_info['filepath'],
                    category=category,
                    timestamp=photo_info['timestamp']
                )
                db.session.add(photo)
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'{len(files)}장의 사진이 저장되었습니다.',
            'organized': {k: len(v) for k, v in organized.items()}
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/photos/<int:project_id>', methods=['GET'])
def get_photos(project_id):
    """프로젝트의 사진 조회"""
    category = request.args.get('category')
    
    query = Photo.query.filter_by(project_id=project_id)
    if category:
        query = query.filter_by(category=category)
    
    photos = query.all()
    
    return jsonify([{
        'id': p.id,
        'filename': p.filename,
        'category': p.category,
        'upload_date': p.upload_date.isoformat()
    } for p in photos])

@app.route('/api/photo/<int:photo_id>', methods=['DELETE'])
def delete_photo(photo_id):
    """사진 삭제"""
    photo = Photo.query.get(photo_id)
    if not photo:
        return jsonify({'status': 'error', 'message': '사진을 찾을 수 없습니다.'}), 404
    
    try:
        # 파일 삭제
        if os.path.exists(photo.file_path):
            os.remove(photo.file_path)
        
        # DB 삭제
        db.session.delete(photo)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': '사진이 삭제되었습니다.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== 보고서 ====================

@app.route('/api/generate_report/<int:project_id>', methods=['POST'])
def generate_report(project_id):
    """보고서 생성 (PPT → PDF → 엑셀)"""
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'status': 'error', 'message': '프로젝트를 찾을 수 없습니다.'}), 404
    
    try:
        # 프로젝트 폴더
        project_folder = photo_manager.get_project_folder(
            project.company,
            project.year,
            project.month
        )
        
        # 사진 폴더
        photos_folder = project_folder / "사진"
        
        # 파일명
        filename = f"{project.company}_{project.year}_{project.month}월"
        
        # 1. PPT 생성
        ppt = ppt_generator.create_presentation(
            project.company,
            project.project_name,
            project.year,
            project.month,
            photos_folder
        )
        ppt_path = project_folder / f"{filename}.ppt"
        ppt_generator.save_ppt(ppt_path)
        
        # 2. PDF 변환
        pdf_path = project_folder / f"{filename}.pdf"
        ppt_generator.ppt_to_pdf(str(ppt_path), str(pdf_path))
        
        # 3. 엑셀 생성
        # 사진 개수 통계
        photos_info = {}
        for category in ['작업전', '작업중', '작업후']:
            count = photo_manager.get_photo_count(
                project.company,
                project.year,
                project.month,
                category
            )
            photos_info[category] = count
        
        excel_path = project_folder / f"{filename}.xlsx"
        ppt_generator.generate_excel(
            project.company,
            project.project_name,
            project.year,
            project.month,
            photos_info,
            excel_path
        )
        
        # DB에 저장
        report = Report(
            project_id=project_id,
            ppt_path=str(ppt_path),
            pdf_path=str(pdf_path),
            excel_path=str(excel_path)
        )
        db.session.add(report)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '보고서가 생성되었습니다.',
            'files': {
                'ppt': str(ppt_path),
                'pdf': str(pdf_path),
                'excel': str(excel_path)
            }
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/download/<int:project_id>/<file_type>', methods=['GET'])
def download_report(project_id, file_type):
    """보고서 다운로드"""
    report = Report.query.filter_by(project_id=project_id).first()
    if not report:
        return jsonify({'status': 'error', 'message': '보고서를 찾을 수 없습니다.'}), 404
    
    if file_type == 'ppt':
        file_path = report.ppt_path
    elif file_type == 'pdf':
        file_path = report.pdf_path
    elif file_type == 'excel':
        file_path = report.excel_path
    else:
        return jsonify({'status': 'error', 'message': '잘못된 파일 형식입니다.'}), 400
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({'status': 'error', 'message': '파일을 찾을 수 없습니다.'}), 404
    
    return send_file(file_path, as_attachment=True)

@app.route('/open_folder/<int:project_id>', methods=['GET'])
def open_folder(project_id):
    """폴더 열기 (탐색기)"""
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'status': 'error', 'message': '프로젝트를 찾을 수 없습니다.'}), 404
    
    try:
        folder_path = photo_manager.get_project_folder(
            project.company,
            project.year,
            project.month
        )
        
        if platform.system() == 'Windows':
            subprocess.Popen(f'explorer "{folder_path}"')
        elif platform.system() == 'Darwin':  # macOS
            subprocess.Popen(['open', str(folder_path)])
        else:  # Linux
            subprocess.Popen(['xdg-open', str(folder_path)])
        
        return jsonify({'status': 'success', 'message': '폴더가 열렸습니다.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
