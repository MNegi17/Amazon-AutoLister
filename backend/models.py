import datetime
import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from .database import Base

class SourceFile(Base):
    __tablename__ = "source_files"
    
    id = Column(Integer, primary_key=True, index=True)
    file_type = Column(String(50), nullable=False) # item_directory, master_sheet, content_sheet, amazon_template, historical_listing
    filename = Column(String(255), nullable=False)
    filepath = Column(String(512), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

class LearnedMapping(Base):
    __tablename__ = "learned_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    amazon_attribute = Column(String(255), nullable=False, index=True)
    internal_column = Column(String(255), nullable=False)
    confidence_score = Column(Float, default=1.0)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class ValueMapping(Base):
    __tablename__ = "value_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    amazon_attribute = Column(String(255), nullable=False, index=True)
    internal_value = Column(String(255), nullable=False)
    amazon_value = Column(String(255), nullable=False)
    confidence_score = Column(Float, default=1.0)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class HardcodedDefault(Base):
    __tablename__ = "hardcoded_defaults"
    
    id = Column(Integer, primary_key=True, index=True)
    amazon_attribute = Column(String(255), nullable=False, unique=True, index=True)
    default_value = Column(String(512), nullable=False)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class AdminRule(Base):
    __tablename__ = "admin_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    scope = Column(String(50), nullable=False) # global, category, brand, product_type
    scope_value = Column(String(255), nullable=True) # e.g. "SHIRT", "Purple United Kids"
    amazon_attribute = Column(String(255), nullable=False, index=True)
    rule_type = Column(String(50), nullable=False) # hardcoded, copy_column, value_translate
    rule_value = Column(String(512), nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class GenerationTask(Base):
    __tablename__ = "generation_tasks"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    skus_input = Column(Text, nullable=True)
    status = Column(String(50), default="pending") # pending, processing, completed, failed
    progress = Column(Integer, default=0) # 0 to 100
    log_messages = Column(Text, default="")
    validation_report = Column(Text, default="{}") # JSON string
    output_file_path = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
