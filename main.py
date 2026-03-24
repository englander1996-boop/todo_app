# Todoアプリのバックエンド (FastAPI)
#
# 1. DB設定: SQLiteを使用したデータ保存ファイル（todos.db）の作成と接続準備。
# 2. データ検証・スキーマ: Pydanticを用いた入出力データの型チェックとバリデーション設定。
# 3. サーバー設定: FastAPIアプリケーションの立ち上げとCORS（クロスオリジン通信）の許可。
# 4. APIエンドポイント群: フロントエンドから呼び出せる以下の機能を提供。
#    - 取得 (GET /tasks): タスク一覧を取得。完了状態の絞り込みや、作成日時の並び替えに対応。
#    - 作成 (POST /tasks): 新しいタスクをデータベースに保存。
#    - 更新 (PUT /tasks/{id}): 指定タスクのタイトル、詳細、完了状態、重要度などを更新。
#    - 削除 (DELETE /tasks/{id}): 指定タスクをデータベースから削除。
#    - エクスポート (GET /tasks/export): 全タスクをJSONファイルとして一括ダウンロード。
#    - インポート (POST /tasks/import): JSONファイルからタスクを一括登録（バルクインサート）。
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
from typing import List, Optional
from fastapi.responses import JSONResponse

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
    is_important = Column(Boolean, default=False)
    deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Pydanticモデル (データの入力・出力定義)
class TaskCreate(BaseModel):
    title: str = Field(..., example="買い物に行く")
    description: Optional[str] = Field(None, example="牛乳と卵を買う")
    deadline: Optional[datetime] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_completed: Optional[bool] = None
    is_important: Optional[bool] = None
    deadline: Optional[datetime] = None

class TaskImport(BaseModel):
    title: str
    description: Optional[str] = None
    is_completed: Optional[bool] = False
    is_important: Optional[bool] = False
    deadline: Optional[datetime] = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    is_completed: bool
    is_important: bool
    deadline: Optional[datetime] = None
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
@app.get("/tasks/export")
def export_tasks(db: Session = Depends(get_db)):
    """全タスクをJSONファイルとしてエクスポートする"""
    tasks = db.query(Task).all()
    # データベースのデータをJSONで出力できる形に変換
    task_list = [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "is_completed": t.is_completed,
            "is_important": t.is_important,
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "created_at": t.created_at.isoformat()
        }
        for t in tasks
    ]
    # ファイルとしてダウンロードさせるための設定をつけて返す
    return JSONResponse(
        content=task_list,
        headers={"Content-Disposition": 'attachment; filename="tasks.json"'}
    )
@app.post("/tasks/import")
def import_tasks(tasks: List[TaskImport], db: Session = Depends(get_db)):
    """JSONデータからタスクを一括インポートする"""
    imported_count = 0
    for t in tasks:
        db_task = Task(
            title=t.title,
            description=t.description,
            is_completed=t.is_completed,
            is_important=t.is_important,
            deadline=t.deadline
        )
        db.add(db_task)
        imported_count += 1
    
    db.commit()
    return {"message": f"{imported_count} tasks imported successfully"}

@app.post("/tasks", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """新しいタスクを作成する"""
    db_task = Task(title=task.title, description=task.description, deadline=task.deadline)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.get("/tasks", response_model=List[TaskResponse])
def read_tasks(skip: int = 0, limit: int = 100, status: Optional[str] = None, order: Optional[str] = "desc", db: Session = Depends(get_db)):
    """タスクの一覧を取得する"""
    query = db.query(Task)
    
    # 完了・未完了のフィルタリング用
    if status == "completed":
        query = query.filter(Task.is_completed == True)
    elif status == "uncompleted":
        query = query.filter(Task.is_completed == False)
    
    # 並び替え機能を追加（新しい順 or 古い順）
    if order == "desc":
        query = query.order_by(Task.created_at.desc())
    else:
        query = query.order_by(Task.created_at.asc())
    
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