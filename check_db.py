from app import app
from database import db
from model import Question, User

def setup_database():
    with app.app_context():
        # すべてのテーブルを作成（Userテーブルも含まれる）
        print("--- テーブルを作成します ---")
        db.create_all()
        print("--- テーブル作成完了 ---")

        # 初期ユーザーを登録
        print("--- 初期ユーザーを登録します ---")
        student_exists = User.query.filter_by(email='student@example.com').first()
        admin_exists = User.query.filter_by(email='admin@example.com').first()

        if not student_exists:
            student = User(email='student@example.com')
            student.set_password('pass123')
            db.session.add(student)
            print("student@example.com を登録しました。")
        else:
            print("student@example.com は既に登録されています。")

        if not admin_exists:
            admin = User(email='admin@example.com')
            admin.set_password('admin123')
            db.session.add(admin)
            print("admin@example.com を登録しました。")
        else:
            print("admin@example.com は既に登録されています。")
        
        db.session.commit()
        print("--- 初期ユーザー登録完了 ---")


def read_all_questions():
    with app.app_context():
        questions = Question.query.all()

        print("\n=== questions テーブルの内容 ===")

        if not questions:
            print("（データなし）")
            return

        for q in questions:
            print(f"[ID] {q.id}")
            print(f"   問題　　： {q.question}")
            print(f"   選択肢１： {q.choice1}")
            print(f"   選択肢２： {q.choice2}")
            print(f"   選択肢３： {q.choice3}")
            print(f"   選択肢４： {q.choice4}")
            print(f"   正解　　： {q.correct}")
            print(f"   区分　　： {q.category}")
            print(f"   ヒント　： {q.hint}")
            print(f"   URL　　 ： {q.url}")
            print(f"-" * 40)

if __name__ == "__main__":
    setup_database()
    read_all_questions()