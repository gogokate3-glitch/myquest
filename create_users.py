import os
from app import app, db
from model import User

def create_users():
    """データベースに初期ユーザーを追加します。"""
    with app.app_context():
        # データベースファイルを削除して再作成する
        basedir = os.path.abspath(os.path.dirname(__file__))
        db_path = os.path.join(basedir, "instance", "quiz.db")
        if os.path.exists(db_path):
            os.remove(db_path)
            print("既存のデータベースを削除しました。")

        # データベーステーブルを作成
        db.create_all()

        # 追加するユーザーのリスト
        users_to_add = [
            {"email": "admin@example.com", "password": "pass123", "nickname": "管理者"},
            {"email": "user1@example.com", "password": "password", "nickname": "user1"},
            {"email": "user2@example.com", "password": "password", "nickname": "user2"}
        ]

        for user_data in users_to_add:
            # ユーザーが既に存在するか確認
            existing_user = User.query.filter_by(email=user_data["email"]).first()
            if not existing_user:
                new_user = User(email=user_data["email"], nickname=user_data["nickname"])
                new_user.set_password(user_data["password"])
                db.session.add(new_user)
                print(f"ユーザー '{user_data['email']}' を追加しました。")
            else:
                print(f"ユーザー '{user_data['email']}' は既に存在します。")

        # 変更をコミット
        db.session.commit()
        print("ユーザーの追加処理が完了しました。")

if __name__ == "__main__":
    create_users()