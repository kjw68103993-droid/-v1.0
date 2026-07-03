from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Project(db.Model):
    """현장(프로젝트) 정보"""
    __tablename__ = 'project'
    
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(100), nullable=False)  # 회사명 (수자원공사)
    project_name = db.Column(db.String(100), nullable=False)  # 현장명
    year = db.Column(db.Integer, nullable=False)  # 년도
    month = db.Column(db.Integer, nullable=False)  # 월
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    photos = db.relationship('Photo', backref='project', lazy=True, cascade='all, delete-orphan')
    reports = db.relationship('Report', backref='project', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Project {self.company} - {self.project_name} {self.year}년 {self.month}월>"


class Photo(db.Model):
    """사진 정보"""
    __tablename__ = 'photo'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)  # 저장 경로
    filename = db.Column(db.String(100), nullable=False)  # 파일명
    category = db.Column(db.String(20), nullable=False)  # '작업전', '작업중', '작업후'
    timestamp = db.Column(db.DateTime)  # EXIF 타임스탬프
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Photo {self.filename} - {self.category}>"


class Report(db.Model):
    """보고서 정보"""
    __tablename__ = 'report'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    ppt_path = db.Column(db.String(255))  # PPT 파일 경로
    pdf_path = db.Column(db.String(255))  # PDF 파일 경로
    excel_path = db.Column(db.String(255))  # 엑셀 파일 경로
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Report {self.project_id}>"
