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
import traceback

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

@app.teardown_appcontext
def cleanup(exception=None):
    """앱 종료 시 임시 파일 정리"""
    try:
        photo_manager.cleanup_temp()
    except:
        pass

# ==================== 대시보드 ====================

@app.route('/')
def dashboard():
    """대시보드"""
    try:
        projects = Project.query.all()
        return render_template('dashboard.html', projects=projects)
    except Exception as e:
        print(f"대시보드 오류: {e}")
        return render_template('dashboard.html', projects=[])

# ==================== 현장관리 ====================

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """현장 목록 조회"""
    try:
        projects = Project.query.all()
        return jsonify([{
            'id': p.id,
            'company': p.company,
            'project_name': p.project_name,
            'year': p.year,
            'month': p.month,
            'created_at': p.created_at.isoformat(),
            'photo_count': len(p.photos),
            'has_report': len(p.reports) > 0
        } for p in projects])
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/projects', methods=['POST'])
def create_project():
    """새 현장 생성"""
    try:
        data = request.json
        
        # 필수 필드 검증
        if not data.get('company') or not data.get('project_name'):
            return jsonify({'status': 'error', 'message': '필수 정보가 누락되었습니다.'}), 400
        
        project = Project(
            company=data.get('company'),
            project_name=data.get('project_name'),
            year=int(data.get('year', 2024)),
            month=int(data.get('month', 1)),
            description=data.get('description', '')
        )
        
        db.session.add(project)
        db.session.commit()
        
        # 폴더 생성
        try:
            photo_manager.get_project_folder(project.company, project.year, project.month)
        except Exception as e:
            print(f"폴더 생성 오류: {e}")
        
        return jsonify({
            'id': project.id,
            'status': 'success',
            'message': '✅ 현장이 생성되었습니다.'
        }), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== 사진관리 ====================

@app.route('/api/upload_photos/<int:project_id>', methods=['POST'])
def upload_photos(project_id):
    """사진 업로드 및 자동정리"""
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'status': 'error', 'message': '프로젝트를 찾을 수 없습니다.'}), 404
        
        files = request.files.getlist('photos')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'status': 'error', 'message': '파일을 선택하세요.'}), 400
        
        # 빈 파일 제거
        files = [f for f in files if f.filename != '']
        
        # 사진 자동정리
        organized = photo_manager.auto_organize_photos(
            project.company,
            project.year,
            project.month,
            files
        )
        
        # DB에 저장
        total_saved = 0
        for category, photos in organized.items():
            for photo_info in photos:
                try:
                    photo = Photo(
                        project_id=project_id,
                        filename=photo_info['filename'],
                        file_path=photo_info['filepath'],
                        category=category,
                        timestamp=photo_info['timestamp']
                    )
                    db.session.add(photo)
                    total_saved += 1
                except Exception as e:
                    print(f"DB 저장 오류: {e}")
                    continue
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'✅ {total_saved}장의 사진이 저장되었습니다.',
            'organized': {k: len(v) for k, v in organized.items()}
        }), 200
    
    except Exception as e:
        db.session.rollback()
        print(f"사진 업로드 오류: {traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': f'오류 발생: {str(e)}'}), 500

@app.route('/api/photos/<int:project_id>', methods=['GET'])
def get_photos(project_id):
    """프로젝트의 사진 조회"""
    try:
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
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/photo/<int:photo_id>', methods=['DELETE'])
def delete_photo(photo_id):
    """사진 삭제"""
    try:
        photo = Photo.query.get(photo_id)
        if not photo:
            return jsonify({'status': 'error', 'message': '사진을 찾을 수 없습니다.'}), 404
        
        # 파일 삭제
        try:
            if os.path.exists(photo.file_path):
                os.remove(photo.file_path)
        except Exception as e:
            print(f"파일 삭제 오류: {e}")
        
        # DB 삭제
        db.session.delete(photo)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': '✅ 사진이 삭제되었습니다.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== 보고서 ====================

@app.route('/api/generate_report/<int:project_id>', methods=['POST'])
def generate_report(project_id):
    """보고서 생성 (PPT → PDF → 엑셀)"""
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'status': 'error', 'message': '프로젝트를 찾을 수 없습니다.'}), 404
        
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
        ppt_path = project_folder / f"{filename}.pptx"
        ppt_generator.save_ppt(ppt_path)
        
        files_created = {'ppt': str(ppt_path)}
        
        # 2. PDF 변환
        pdf_path = project_folder / f"{filename}.pdf"
        pdf_result = ppt_generator.ppt_to_pdf(str(ppt_path), str(pdf_path))
        if pdf_result:
            files_created['pdf'] = str(pdf_result)
        else:
            files_created['pdf'] = None
        
        # 3. 엑셀 생성
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
        files_created['excel'] = str(excel_path)
        
        # DB에 저장
        report = Report(
            project_id=project_id,
            ppt_path=str(ppt_path),
            pdf_path=files_created.get('pdf'),
            excel_path=str(excel_path)
        )
        db.session.add(report)
        db.session.commit()
        
        message = "✅ 보고서가 생성되었습니다."
        if not files_created.get('pdf'):
            message += " (PDF 변환 불가 - LibreOffice 설치 필요)"
        
        return jsonify({
            'status': 'success',
            'message': message,
            'files': files_created
        }), 200
    
    except Exception as e:
        db.session.rollback()
        print(f"보고서 생성 오류: {traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': f'오류 발생: {str(e)}'}), 500

@app.route('/download/<int:project_id>/<file_type>', methods=['GET'])
def download_report(project_id, file_type):
    """보고서 다운로드"""
    try:
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
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/open_folder/<int:project_id>', methods=['GET'])
def open_folder(project_id):
    """폴더 열기 (탐색기)"""
    try:
        project = Project.query.get(project_id)
        if not project:
            return jsonify({'status': 'error', 'message': '프로젝트를 찾을 수 없습니다.'}), 404
        
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
        
        return jsonify({'status': 'success', 'message': '📁 폴더가 열렸습니다.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== 에러 핸들러 ====================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'status': 'error', 'message': '페이지를 찾을 수 없습니다.'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'status': 'error', 'message': '서버 오류가 발생했습니다.'}), 500

if __name__ == '__main__':
    print("🚀 YG-Manager 시스템 시작...")
    print("📍 http://localhost:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)
