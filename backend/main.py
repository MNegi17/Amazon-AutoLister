import os
import shutil
import uuid
import json
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from .database import engine, Base, get_db, SessionLocal, Session

from .models import SourceFile, LearnedMapping, ValueMapping, HardcodedDefault, AdminRule, GenerationTask
from .services.learning_engine import LearningEngine
from .services.generation_service import GenerationService
from .services.excel_processor import ExcelProcessor
from .seed_manager import seed_database

# Initialize database tables
Base.metadata.create_all(bind=engine)
try:
    seed_database()
except Exception as _seed_err:
    print(f"⚠️  Seed skipped (will retry on next operation): {_seed_err}")

app = FastAPI(title="Amazon Auto Lister API", version="1.0.0")

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./data/uploads")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./data/outputs")

# Create directories
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Health check
@app.get("/")
def root():
    return {"status": "ok", "service": "Amazon Auto Lister API"}

@app.get("/health")
def health():
    return {"status": "ok"}

# FILE UPLOAD & MANAGEMENT ENDPOINTS
# ----------------------------------------------------

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    file_type: str = Form(...), # item_directory, master_sheet, content_sheet, amazon_template, historical_listing
    db: Session = Depends(get_db)
):
    if file_type not in ["item_directory", "master_sheet", "content_sheet", "amazon_template", "historical_listing"]:
        raise HTTPException(status_code=400, detail="Invalid file type.")
        
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    safe_filename = f"{file_type}_{file_id}{ext}"
    filepath = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    source_file = SourceFile(
        file_type=file_type,
        filename=file.filename,
        filepath=filepath
    )
    db.add(source_file)
    db.commit()
    db.refresh(source_file)
    
    return {
        "id": source_file.id,
        "file_type": source_file.file_type,
        "filename": source_file.filename,
        "uploaded_at": source_file.uploaded_at
    }

@app.get("/api/files")
def get_files(db: Session = Depends(get_db)):
    files = db.query(SourceFile).order_by(SourceFile.uploaded_at.desc()).all()
    # Group by file_type
    grouped = {
        "item_directory": [],
        "master_sheet": [],
        "content_sheet": [],
        "amazon_template": [],
        "historical_listing": []
    }
    for f in files:
        if f.file_type in grouped:
            grouped[f.file_type].append({
                "id": f.id,
                "filename": f.filename,
                "uploaded_at": f.uploaded_at
            })
    return grouped

@app.delete("/api/files/{file_id}")
def delete_file(file_id: str, db: Session = Depends(get_db)):
    file_record = db.query(SourceFile).filter(SourceFile.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
        
    # Delete from disk
    if os.path.exists(file_record.filepath):
        try:
            os.remove(file_record.filepath)
        except Exception as e:
            pass
            
    db.delete(file_record)
    db.commit()
    return {"status": "success", "message": "File deleted successfully"}

# ----------------------------------------------------
# AI TRAINING ENDPOINTS
# ----------------------------------------------------

def run_training_task(history_id: int, directory_id: Optional[int], master_id: Optional[int], content_id: Optional[int], db_session_creator):
    db = db_session_creator()
    try:
        # If master_id is not provided, default to directory_id since Item Directory and Master Sheet are the same
        if directory_id and not master_id:
            master_id = directory_id
        history_file = db.query(SourceFile).filter(SourceFile.id == history_id).first()
        dir_file = db.query(SourceFile).filter(SourceFile.id == directory_id).first() if directory_id else None
        master_file = db.query(SourceFile).filter(SourceFile.id == master_id).first() if master_id else None
        content_file = db.query(SourceFile).filter(SourceFile.id == content_id).first() if content_id else None
        
        if not history_file:
            return
            
        LearningEngine.learn_from_historical_listing(
            db,
            history_file.filepath,
            dir_file.filepath if dir_file else None,
            master_file.filepath if master_file else None,
            content_file.filepath if content_file else None
        )
    except Exception as e:
        print(f"Error in training background task: {e}")
    finally:
        db.close()

@app.post("/api/train")
def train_engine(
    background_tasks: BackgroundTasks,
    history_id: int = Form(...),
    directory_id: Optional[int] = Form(None),
    master_id: Optional[int] = Form(None),
    content_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    # Verify history file exists
    history_file = db.query(SourceFile).filter(SourceFile.id == history_id).first()
    if not history_file:
        raise HTTPException(status_code=404, detail="Historical listing file not found.")
        
    # Trigger training in background
    background_tasks.add_task(
        run_training_task,
        history_id,
        directory_id,
        master_id,
        content_id,
        lambda: SessionLocal() if 'SessionLocal' in globals() else engine.connect()
    )
    
    return {"status": "processing", "message": "Training has been started in the background."}

# ----------------------------------------------------
# MAPPINGS AND VALUES REVIEW
# ----------------------------------------------------

@app.get("/api/mappings")
def get_mappings(db: Session = Depends(get_db)):
    columns = db.query(LearnedMapping).order_by(LearnedMapping.confidence_score.desc()).all()
    values = db.query(ValueMapping).order_by(ValueMapping.confidence_score.desc()).all()
    return {
        "column_mappings": [
            {
                "id": m.id,
                "amazon_attribute": m.amazon_attribute,
                "internal_column": m.internal_column,
                "confidence_score": m.confidence_score,
                "is_active": m.is_active
            } for m in columns
        ],
        "value_mappings": [
            {
                "id": v.id,
                "amazon_attribute": v.amazon_attribute,
                "internal_value": v.internal_value,
                "amazon_value": v.amazon_value,
                "confidence_score": v.confidence_score
            } for v in values
        ]
    }

@app.post("/api/mappings/column/{mapping_id}/toggle")
def toggle_column_mapping(mapping_id: str, db: Session = Depends(get_db)):
    m = db.query(LearnedMapping).filter(LearnedMapping.id == mapping_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Mapping not found")
    m.is_active = not m.is_active
    db.commit()
    return {"status": "success", "is_active": m.is_active}

@app.post("/api/mappings/column")
def create_or_override_column_mapping(
    amazon_attribute: str = Form(...),
    internal_column: str = Form(...),
    db: Session = Depends(get_db)
):
    m = db.query(LearnedMapping).filter(LearnedMapping.amazon_attribute == amazon_attribute).first()
    if not m:
        m = LearnedMapping(amazon_attribute=amazon_attribute)
        db.add(m)
    m.internal_column = internal_column
    m.confidence_score = 1.0 # manual override
    m.is_active = True
    db.commit()
    return {"status": "success"}

@app.delete("/api/mappings/value/{mapping_id}")
def delete_value_mapping(mapping_id: str, db: Session = Depends(get_db)):
    v = db.query(ValueMapping).filter(ValueMapping.id == mapping_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Mapping not found")
    db.delete(v)
    db.commit()
    return {"status": "success"}

# ----------------------------------------------------
# ADMIN CONFIG & SETTINGS ENDPOINTS
# ----------------------------------------------------

@app.get("/api/settings/defaults")
def get_defaults(db: Session = Depends(get_db)):
    defs = db.query(HardcodedDefault).all()
    return {d.amazon_attribute: d.default_value for d in defs if d.is_active}

@app.post("/api/settings/defaults")
def update_defaults(defaults: dict, db: Session = Depends(get_db)):
    # Clear existing defaults
    db.query(HardcodedDefault).delete()
    for attr, val in defaults.items():
        if val is not None and str(val).strip() != "":
            d = HardcodedDefault(amazon_attribute=attr, default_value=str(val).strip(), is_active=True)
            db.add(d)
    db.commit()
    return {"status": "success"}

@app.get("/api/settings/rules")
def get_rules(db: Session = Depends(get_db)):
    rules = db.query(AdminRule).all()
    return [
        {
            "id": r.id,
            "scope": r.scope,
            "scope_value": r.scope_value,
            "amazon_attribute": r.amazon_attribute,
            "rule_type": r.rule_type,
            "rule_value": r.rule_value
        } for r in rules
    ]

@app.post("/api/settings/rules")
def create_rule(
    scope: str = Form(...),
    scope_value: str = Form(""),
    amazon_attribute: str = Form(...),
    rule_value: str = Form(...),
    db: Session = Depends(get_db)
):
    r = AdminRule(
        scope=scope,
        scope_value=scope_value.strip() or None,
        amazon_attribute=amazon_attribute,
        rule_type="hardcoded",
        rule_value=rule_value
    )
    db.add(r)
    db.commit()
    return {"status": "success", "id": r.id}

@app.delete("/api/settings/rules/{rule_id}")
def delete_rule(rule_id: str, db: Session = Depends(get_db)):
    r = db.query(AdminRule).filter(AdminRule.id == rule_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(r)
    db.commit()
    return {"status": "success"}

# ----------------------------------------------------
# GENERATION ENGINE ENDPOINTS
# ----------------------------------------------------

def run_generation_task(
    task_id: str,
    skus_input: str,
    directory_path: str,
    master_path: str,
    content_path: str,
    template_path: str,
    output_path: str,
    db_session_creator
):
    db = db_session_creator()
    task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    
    logs = []
    def task_log(msg):
        logs.append(msg)
        task.log_messages = "\n".join(logs)
        db.commit()
        
    try:
        task.status = "processing"
        task.progress = 20
        task_log("🚀 Starting listing generation engine...")
        db.commit()
        
        # Execute Generation Service
        result = GenerationService.generate_listings(
            db=db,
            skus_input=skus_input,
            item_directory_path=directory_path,
            master_sheet_path=master_path,
            content_sheet_path=content_path,
            template_path=template_path,
            output_path=output_path,
            task_logger=task_log
        )
        
        task.progress = 100
        task.status = "completed"
        task.output_file_path = output_path
        task.validation_report = json.dumps(result["validation"])
        task_log("🎉 All listings generated! Your file is ready to download.")
        
    except Exception as e:
        task.status = "failed"
        task.progress = 100
        task_log(f"ERROR: {str(e)}")
        import traceback
        task_log(traceback.format_exc())
    finally:
        import datetime
        task.completed_at = datetime.datetime.utcnow()
        db.commit()
        db.close()

@app.post("/api/generate")
def start_generation(
    skus_input: str = Form(...),
    directory_id: int = Form(...),
    master_id: Optional[int] = Form(None),
    content_id: int = Form(...),
    template_id: int = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    # If master_id is not provided, default to directory_id since Item Directory and Master Sheet are the same
    if master_id is None:
        master_id = directory_id

    # Verify all files
    dir_f = db.query(SourceFile).filter(SourceFile.id == directory_id).first()
    mst_f = db.query(SourceFile).filter(SourceFile.id == master_id).first()
    cnt_f = db.query(SourceFile).filter(SourceFile.id == content_id).first()
    tmp_f = db.query(SourceFile).filter(SourceFile.id == template_id).first()
    
    if not (dir_f and mst_f and cnt_f and tmp_f):
        raise HTTPException(status_code=404, detail="One or more required sheets/templates was not found.")
        
    # Create background task
    task_id = str(uuid.uuid4())
    task = GenerationTask(
        id=task_id,
        skus_input=skus_input,
        status="pending",
        progress=0,
        log_messages="Task added to queue."
    )
    db.add(task)
    db.commit()
    
    output_filename = f"Amazon_Listing_{task_id}.xlsm"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    background_tasks.add_task(
        run_generation_task,
        task_id,
        skus_input,
        dir_f.filepath,
        mst_f.filepath,
        cnt_f.filepath,
        tmp_f.filepath,
        output_path,
        lambda: SessionLocal()
    )
    
    return {"task_id": task_id, "status": "pending"}

@app.get("/api/tasks")
def list_tasks(db: Session = Depends(get_db)):
    tasks = db.query(GenerationTask).order_by(GenerationTask.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "status": t.status,
            "progress": t.progress,
            "created_at": t.created_at,
            "completed_at": t.completed_at,
            "skus_count": len([x for x in t.skus_input.split(",") if x.strip()]) if t.skus_input else 0
        } for t in tasks
    ]

@app.get("/api/tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    t = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
        
    val_report = {}
    try:
        if t.validation_report:
            val_report = json.loads(t.validation_report)
    except:
        pass
        
    return {
        "id": t.id,
        "status": t.status,
        "progress": t.progress,
        "log_messages": t.log_messages,
        "validation": val_report,
        "created_at": t.created_at,
        "completed_at": t.completed_at,
        "has_download": t.status == "completed" and os.path.exists(t.output_file_path) if t.output_file_path else False
    }

@app.get("/api/tasks/{task_id}/download")
def download_task_file(task_id: str, db: Session = Depends(get_db)):
    t = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    if not t or not t.output_file_path or not os.path.exists(t.output_file_path):
        raise HTTPException(status_code=404, detail="Generated file not found.")
    return FileResponse(
        t.output_file_path,
        media_type="application/vnd.ms-excel.sheet.macroEnabled.12",
        filename=os.path.basename(t.output_file_path)
    )
