from flask import Flask, render_template, request, jsonify, send_file
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
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Flask 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yg_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
app.config['JSON_AS_ASCII'] = False

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
    """임시 파일 정리"""
    try:
        photo_manager.cleanup_temp()
    except:
        pass

# ==================== 라우트 ====================

@app.route('/')
def index():
    """대시보드"""
    try:
        projects = Project.query.order_by(Project.created_at.desc()).all()
        total_photos = sum(len(p.photos) for p in projects)
        total_reports = sum(len(p.reports) for p in projects)
        
        return render_template('dashboard.html', 
                             projects=projects,
                             total_photos=total_photos,
                             total_reports=total_reports)
    except Exception as e:
        logger.error(f"대시보드 오류: {e}")
        return render_template('dashboard.html', projects=[], total_photos=0, total_reports=0)

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    """프로젝트 상세 페이지"""
    try:
        project = Project.query.get_or_404(project_id)
        return render_template('project_detail.html', project=project)
    except Exception as e:
        logger.error(f"프로젝트 조회 오류: {e}")
        return render_template('error.html', 
                             title='프로젝트 오류',
                             message='프로젝트를 찾을 수 없습니다.'), 404

# ==================== API ====================

@app.route('/api/projects', methods=['POST'])
def create_project():
    """새 현장 생성"""
    try:
        data = request.get_json()
        
        # 필수 필드 검증
        if not data.get('company') or not data.get('project_name'):
            return jsonify({'ok': False, 'msg': '필수 정보가 누락되었습니다.'}), 400
        
        # 중복 확인
        existing = Project.query.filter_by(
            company=data['company'],
            project_name=data['project_name'],
            year=int(data.get('year', 2024)),
            month=int(data.get('month', 1))
        ).first()
        
        if existing:
            return jsonify({'ok': False, 'msg': '이미 존재하는 현장입니다.'}), 409
        
        project = Project(
            company=data['company'],
            project_name=data['project_name'],
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
            logger.warning(f"폴더 생성 실패: {e}")
        
        return jsonify({'ok': True, 'msg': '현장이 생성되었습니다.', 'id': project.id}), 201
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"현장 생성 오류: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500

@app.route('/api/project/<int:project_id>/photos/upload', methods=['POST'])
def upload_photos(project_id):
    """사진 업로드 및 자동정리"""
    try:
        project = Project.query.get_or_404(project_id)
        files = request.files.getlist('photos')
        
        if not files or all(f.filename == '' for f in files):
            return jsonify({'ok': False, 'msg': '파일을 선택하세요.'}), 400
        
        files = [f for f in files if f.filename != '']
        
        # 사진 자동정리
        organized = photo_manager.auto_organize_photos(
            project.company, project.year, project.month, files
        )
        
        # DB 저장
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
                    logger.error(f"사진 저장 오류: {e}")
                    continue
        
        db.session.commit()
        
        return jsonify({
            'ok': True,
            'msg': f'{total_saved}장의 사진이 저장되었습니다.',
            'stats': {k: len(v) for k, v in organized.items()}
        }), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"사진 업로드 오류: {traceback.format_exc()}")
        return jsonify({'ok': False, 'msg': str(e)}), 500

@app.route('/api/project/<int:project_id>/photos', methods=['GET'])
def get_photos(project_id):
    """프로젝트의 사진 조회"""
    try:
        category = request.args.get('category')
        query = Photo.query.filter_by(project_id=project_id)
        
        if category:
            query = query.filter_by(category=category)
        
        photos = query.order_by(Photo.upload_date).all()
        
        return jsonify([{
            'id': p.id,
            'filename': p.filename,
            'category': p.category,
            'upload_date': p.upload_date.strftime('%Y-%m-%d %H:%M')
        } for p in photos])
    except Exception as e:
        logger.error(f"사진 조회 오류: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500

@app.route('/api/project/<int:project_id>/photos/stats', methods=['GET'])
def get_photo_stats(project_id):
    """사진 통계"""
    try:
        stats = {}
        for category in ['작업전', '작업중', '작업후']:
            count = Photo.query.filter_by(
                project_id=project_id,
                category=category
            ).count()
            stats[category] = count
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"통계 조회 오류: {e}")
        return jsonify({}), 500

@app.route('/api/project/<int:project_id>/report/generate', methods=['POST'])
def generate_report(project_id):
    """보고서 생성"""
    try:
        project = Project.query.get_or_404(project_id)
        
        project_folder = photo_manager.get_project_folder(
            project.company, project.year, project.month
        )
        photos_folder = project_folder / "사진"
        
        filename = f"{project.company}_{project.year}_{project.month:02d}월"
        
        # 1. PPT 생성
        ppt = ppt_generator.create_presentation(
            project.company, project.project_name,
            project.year, project.month, photos_folder
        )
        ppt_path = project_folder / f"{filename}.pptx"
        ppt_generator.save_ppt(ppt_path)
        
        files = {'ppt': str(ppt_path)}
        
        # 2. PDF 변환
        pdf_path = project_folder / f"{filename}.pdf"
        pdf_result = ppt_generator.ppt_to_pdf(str(ppt_path), str(pdf_path))
        files['pdf'] = str(pdf_result) if pdf_result else None
        
        # 3. 엑셀 생성
        photos_info = {}
        for category in ['작업전', '작업중', '작업후']:
            photos_info[category] = Photo.query.filter_by(
                project_id=project_id,
                category=category
            ).count()
        
        excel_path = project_folder / f"{filename}.xlsx"
        ppt_generator.generate_excel(
            project.company, project.project_name,
            project.year, project.month, photos_info, excel_path
        )
        files['excel'] = str(excel_path)
        
        # DB 저장
        report = Report(
            project_id=project_id,
            ppt_path=str(ppt_path),
            pdf_path=files['pdf'],
            excel_path=str(excel_path)
        )
        db.session.add(report)
        db.session.commit()
        
        msg = '보고서가 생성되었습니다.'
        if not files['pdf']:
            msg += ' (PDF는 LibreOffice 필요)'
        
        return jsonify({'ok': True, 'msg': msg, 'files': files}), 200
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"보고서 생성 오류: {traceback.format_exc()}")
        return jsonify({'ok': False, 'msg': str(e)}), 500

@app.route('/download/<int:project_id>/<file_type>')
def download_report(project_id, file_type):
    """파일 다운로드"""
    try:
        report = Report.query.filter_by(project_id=project_id).first_or_404()
        
        if file_type == 'ppt':
            file_path = report.ppt_path
        elif file_type == 'pdf':
            file_path = report.pdf_path
        elif file_type == 'excel':
            file_path = report.excel_path
        else:
            return jsonify({'ok': False, 'msg': '잘못된 형식'}), 400
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({'ok': False, 'msg': '파일을 찾을 수 없습니다.'}), 404
        
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        logger.error(f"다운로드 오류: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500

@app.route('/api/project/<int:project_id>/folder/open')
def open_folder(project_id):
    """폴더 열기"""
    try:
        project = Project.query.get_or_404(project_id)
        
        folder_path = photo_manager.get_project_folder(
            project.company, project.year, project.month
        )
        
        if platform.system() == 'Windows':
            subprocess.Popen(f'explorer "{folder_path}"')
        elif platform.system() == 'Darwin':
            subprocess.Popen(['open', str(folder_path)])
        else:
            subprocess.Popen(['xdg-open', str(folder_path)])
        
        return jsonify({'ok': True, 'msg': '폴더가 열렸습니다.'})
    except Exception as e:
        logger.error(f"폴더 열기 오류: {e}")
        return jsonify({'ok': False, 'msg': str(e)}), 500

# ==================== 에러 핸들러 ====================

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html',
                         title='404 오류',
                         message='페이지를 찾을 수 없습니다.'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html',
                         title='500 오류',
                         message='서버 오류가 발생했습니다.'), 500

if __name__ == '__main__':
    print("\n🚀 YG-Manager 시스템 시작...")
    print("📍 http://localhost:5000\n")
    app.run(debug=True, host='127.0.0.1', port=5000)
