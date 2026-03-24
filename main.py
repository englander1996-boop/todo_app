#Todoアプリのバックエンド
#DB設定: データを保存するファイル（SQLite）の作成と接続準備 。
#データ検証のルール: 画面とやり取りするデータが正しい形かを自動チェックする設定 。
#サーバー準備: FastAPIを用いたWebアプリケーション本体の立ち上げ 。
#APIの作成: 画面から呼び出せる4つの機能を提供。
#   作成 (POST): 新しいタスクを保存 。
#   取得 (GET): 全タスクを一覧で返す
#   更新 (PUT): タスクの内容や完了状態を上書き 。
#   削除 (DELETE): 指定タスクを消去 。

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
from typing import List, Optional

#データベース設定 (SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///./todos.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

#データベースモデル
class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Pydanticモデル (データの入力・出力定義)
class TaskCreate(BaseModel):
    title: str = Field(..., example="買い物に行く")
    description: Optional[str] = Field(None, example="牛乳と卵を買う")

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_completed: Optional[bool] = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    is_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True

#FastAPIアプリケーション
app = FastAPI(title="Todo API")

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Todo API")

#以下のCORS設定を追記
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# DBセッションを取得する関数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#APIエンドポイント

@app.post("/tasks", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """新しいタスクを作成する"""
    db_task = Task(title=task.title, description=task.description)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.get("/tasks", response_model=List[TaskResponse])
def read_tasks(skip: int = 0, limit: int = 100, status: Optional[str] = None, db: Session = Depends(get_db)):
    """タスクの一覧を取得する"""
    query = db.query(Task)
    # 完了・未完了のフィルタリング用
    if status == "completed":
        query = query.filter(Task.is_completed == True)
    elif status == "uncompleted":
        query = query.filter(Task.is_completed == False)
    
    tasks = query.offset(skip).limit(limit).all()
    return tasks

@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db)):
    """タスクを更新する（タイトル、詳細、完了状態）"""
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = task_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)
    
    db.commit()
    db.refresh(db_task)
    return db_task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """タスクを削除する"""
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(db_task)
    db.commit()
    return {"message": "Task deleted successfully"}