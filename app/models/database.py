from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(20), nullable=False, index=True)
    state = Column(String(50), nullable=False, default="inicio")
    context = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Conversation(phone='{self.phone}', state='{self.state}')>"

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(String(20), nullable=False, index=True)
    patient_name = Column(String(100), nullable=False)
    patient_phone = Column(String(20), nullable=False, index=True)
    appointment_date = Column(DateTime(timezone=True), nullable=False)
    appointment_type = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="scheduled")  # scheduled, cancelled, completed
    reminder_sent = Column(Boolean, default=False)
    gestaods_id = Column(String(50), nullable=True)  # ID do agendamento no GestãoDS
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Appointment(patient='{self.patient_name}', date='{self.appointment_date}')>"

class WaitingList(Base):
    __tablename__ = "waiting_list"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(String(20), nullable=False, index=True)
    patient_name = Column(String(100), nullable=False)
    patient_phone = Column(String(20), nullable=False, index=True)
    preferred_dates = Column(JSON, nullable=True)  # Lista de datas preferidas
    priority = Column(Integer, default=1)  # Prioridade (1-5, sendo 1 mais alta)
    notified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<WaitingList(patient='{self.patient_name}', priority={self.priority})>"

class MessageLog(Base):
    __tablename__ = "message_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(20), nullable=False, index=True)
    message_id = Column(String(100), nullable=True)
    direction = Column(String(10), nullable=False)  # "in" ou "out"
    message_type = Column(String(20), nullable=False, default="text")
    content = Column(Text, nullable=True)
    status = Column(String(20), nullable=True)  # sent, delivered, read, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<MessageLog(phone='{self.phone}', direction='{self.direction}')>" 