import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from database import db
from model import Question, User, QuizResult
import random
from itertools import groupby

# home.html からコピーした章のリスト
# 順序を維持するためにリスト・オブ・タプルを使用
CHAPTERS = [
    (1, "1. やる気を高めよう"),
    (2, "2. Python インタプリタを使う"),
    (3, "3. 形式ばらない Python の紹介"),
    (4, "4. その他の制御フローツール"),
    (5, "5. データ構造"),
    (6, "6. モジュール"),
    (7, "7. 入力と出力"),
    (8, "8. エラーと例外"),
    (9, "9. クラス"),
    (10, "10. 標準ライブラリミニツアー"),
    (11, "11. 標準ライブラリミニツアー --- その 2"),
    (12, "12. 仮想環境とパッケージ"),
    (14, "14. 対話入力編集と履歴置換"),
]

app = Flask(__name__)
app.secret_key = "test123"

# DB設定を追加
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "instance", "quiz.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# ログイン
@app.route("/")
def login():
    return render_template("login.html")

@app.route("/try_login", methods=["post"])
def try_login():
    email = request.form.get("email")
    pw = request.form.get("password")

    user = User.query.filter_by(email=email).first()

    if user and user.check_password(pw):
        session["user"] = user.email
        session["nickname"] = user.nickname or user.email.split('@')[0] # ニックネームがなければemailの@より前を使う
        return redirect(url_for("home"))
    else:
        return render_template("login.html", error="ログインに失敗しました")
    

@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("nickname", None)
    return redirect("/")

@app.route("/change_user_info", methods=["GET", "POST"])
def change_user_info():
    if "user" not in session:
        flash("ログインしてください。", "warning")
        return redirect("/")

    current_user_email = session["user"]
    user = User.query.filter_by(email=current_user_email).first()

    if not user:
        session.pop("user", None)
        session.pop("nickname", None)
        flash("ユーザーが見つかりません。", "danger")
        return redirect("/")

    if request.method == "POST":
        nickname = request.form.get("nickname")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        
        # ニックネームを更新
        if nickname:
            user.nickname = nickname
            session["nickname"] = nickname # セッションのニックネームも更新
            flash("ニックネームを更新しました。", "success")
        else:
            flash("ニックネームは空にできません。", "danger")
            # Return to render_template with current user info
            return render_template("change_password.html", email=user.email, nickname=user.nickname)

        # パスワードが入力されている場合のみ更新
        if new_password:
            if new_password != confirm_password:
                flash("新しいパスワードが一致しません。", "danger")
                return render_template("change_password.html", email=user.email, nickname=user.nickname)
            user.set_password(new_password)
            flash("パスワードを更新しました。", "success")
        
        db.session.commit()
        flash("ユーザー情報を更新しました。", "success")
        return redirect(url_for("change_user_info"))

    # GET request
    return render_template("change_password.html", email=user.email, nickname=user.nickname)


# ホーム
@app.route("/home")
def home():
    if "user" not in session:
        return redirect("/")
    nickname = session.get("nickname", "Guest")
    return render_template("home.html", nickname=nickname, email=session["user"])

@app.route("/home_action", methods=["POST"])
def home_action():
    if "user" not in session:
        return redirect("/")
    
    selected_option = request.form.get("selected_option")
    if selected_option:
        return redirect(selected_option)
    else:
        # Handle case where no option was selected, though a default is set in HTML
        return redirect(url_for("home"))

# 教材
@app.route("/material")
def material():
    if "user" not in session:
        return redirect("/")
    return render_template("material.html")

# 章末テスト
@app.route("/section_test/<category>")
def section_test(category):
    if "user" not in session:
        return redirect("/")
    
    # クエリパラメータから問題数を取得、デフォルトは10
    try:
        num_questions = int(request.args.get("num_questions", 10))
    except (ValueError, TypeError):
        num_questions = 10 # 無効な値の場合はデフォルトの10問

    q_list = Question.query.filter_by(category=category).all()
    if not q_list:
        return f"カテゴリ「{category}」の問題がDBにありません"
    
    # 指定された問題数をランダムに選ぶ
    num_to_sample = min(len(q_list), num_questions)
    q_list = random.sample(q_list, num_to_sample)
    
    return render_template("section_test.html", questions=q_list, category_name=category)

@app.route("/section_test", methods=["POST"])
def section_test_redirect():
    if "user" not in session:
        return redirect("/")
    
    category = request.form.get("category")
    num_questions = request.form.get("num_questions", 10) # デフォルトは10問
    
    if category:
        return redirect(url_for("section_test", category=category, num_questions=num_questions))
    else:
        return redirect(url_for("home"))


@app.route("/submit_section_test", methods=["POST"])
def submit_section_test():
    if "user" not in session:
        return redirect("/")

    answers = request.form
    category_name = answers.get("category_name", "")
    question_ids = [key.split('_')[1] for key in answers.keys() if key.startswith('answer_')]
    
    if not question_ids:
        if category_name:
            return redirect(url_for("section_test", category=category_name))
        else:
            return redirect(url_for("home"))

    results = []
    questions = Question.query.filter(Question.id.in_(question_ids)).all()
    question_map = {str(q.id): q for q in questions}

    # 現在のユーザーのIDを取得
    current_user_email = session["user"]
    current_user = User.query.filter_by(email=current_user_email).first()
    if not current_user:
        return redirect("/") # ユーザーが見つからない場合はログインページへ

    score = 0
    for q_id in question_ids:
        question = question_map.get(q_id)
        if question:
            user_answer_val = answers.get(f'answer_{q_id}')
            if user_answer_val is None:
                user_answer_val = -1
            else:
                user_answer_val = int(user_answer_val)
            
            is_correct = (user_answer_val == question.correct)
            if is_correct:
                score += 1

            choices = [question.choice1, question.choice2, question.choice3, question.choice4]
            
            user_choice_text = choices[user_answer_val - 1] if 0 < user_answer_val <= 4 else "未回答"
            correct_choice_text = choices[question.correct - 1] if 0 < question.correct <= 4 else ""

            results.append({
                "question": question,
                "user_answer": user_answer_val,
                "user_choice_text": user_choice_text,
                "correct_answer": question.correct,
                "correct_choice_text": correct_choice_text,
                "is_correct": is_correct
            })

            # QuizResultを保存
            from model import QuizResult # Import inside function to avoid circular dependency
            quiz_result = QuizResult(
                user_id=current_user.id,
                question_id=question.id,
                is_correct=is_correct
            )
            db.session.add(quiz_result)
    
    db.session.commit() # すべての結果をコミット
    
    total = len(questions)
    percentage = (score / total) * 100 if total > 0 else 0
    
    if not category_name and questions:
        category_name = questions[0].category

    return render_template("section_test.html", 
        results=results, 
        category_name=category_name,
        score=score,
        total=total,
        percentage=f"{percentage:.1f}"
    )


@app.route("/check_answer", methods=["POST"])
def check_answer():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    question_id = data.get("question_id")
    user_answer = data.get("user_answer")

    if not question_id or not user_answer:
        return jsonify({"error": "Missing data"}), 400

    question = Question.query.get(question_id)
    if not question:
        return jsonify({"error": "Question not found"}), 404

    is_correct = (int(user_answer) == question.correct)
    
    # 正解の選択肢のテキストを取得
    correct_choice_text = ""
    if question.correct == 1:
        correct_choice_text = question.choice1
    elif question.correct == 2:
        correct_choice_text = question.choice2
    elif question.correct == 3:
        correct_choice_text = question.choice3
    elif question.correct == 4:
        correct_choice_text = question.choice4

    return jsonify({
        "correct": is_correct,
        "correct_answer": question.correct,
        "correct_choice_text": correct_choice_text
    })

from sqlalchemy import desc
from itertools import groupby

# ... (他のルートは変更なし) ...

# 過去演習
@app.route("/practice", methods=["GET", "POST"])
def practice():
    if "user" not in session:
        return redirect("/")

    current_user_email = session.get("user")
    current_user = User.query.filter_by(email=current_user_email).first()
    if not current_user:
        flash("ユーザーが見つかりません。", "danger")
        return redirect("/")

    if request.method == "POST":
        # --- 回答処理 ---
        answers = request.form
        question_ids = [key.split('_')[1] for key in answers.keys() if key.startswith('answer_')]
        
        if not question_ids:
            return redirect(url_for("practice", **request.args))

        results = []
        questions = Question.query.filter(Question.id.in_(question_ids)).all()
        question_map = {str(q.id): q for q in questions}

        score = 0
        for q_id in question_ids:
            question = question_map.get(q_id)
            if question:
                user_answer_val = answers.get(f'answer_{q_id}')
                if user_answer_val is None:
                    user_answer_val = -1
                else:
                    user_answer_val = int(user_answer_val)
                
                is_correct = (user_answer_val == question.correct)
                if is_correct:
                    score += 1

                choices = [question.choice1, question.choice2, question.choice3, question.choice4]
                
                user_choice_text = choices[user_answer_val - 1] if 0 < user_answer_val <= 4 else "未回答"
                correct_choice_text = choices[question.correct - 1] if 0 < question.correct <= 4 else ""

                results.append({
                    "question": question,
                    "user_answer": user_answer_val,
                    "user_choice_text": user_choice_text,
                    "correct_answer": question.correct,
                    "correct_choice_text": correct_choice_text,
                    "is_correct": is_correct
                })

                quiz_result = QuizResult(
                    user_id=current_user.id,
                    question_id=question.id,
                    is_correct=is_correct
                )
                db.session.add(quiz_result)
        
        db.session.commit()

        num_questions_for_retry = request.form.get('num_questions')
        practice_type_for_retry = request.form.get('type')

        total = len(questions)
        percentage = (score / total) * 100 if total > 0 else 0
        
        return render_template("practice.html", 
            results=results, 
            score=score,
            total=total,
            percentage=f"{percentage:.1f}",
            num_questions=num_questions_for_retry,
            practice_type=practice_type_for_retry,
            title="テスト結果"
        )

    # --- 問題表示 (GETリクエスト) ---
    try:
        num_questions = int(request.args.get('num_questions', 10))
    except (ValueError, TypeError):
        num_questions = 10
    
    practice_type = request.args.get('type', 'all')
    
    question_pool = []
    title = ""
    
    if practice_type == 'exclude_answered':
        title = "過去問演習（2回以上正解した問題を除く）"
        all_results = db.session.query(QuizResult).filter_by(user_id=current_user.id).order_by(QuizResult.question_id, desc(QuizResult.timestamp)).all()
        
        results_by_question = {k: list(v) for k, v in groupby(all_results, key=lambda r: r.question_id)}

        exclude_question_ids = set()
        for q_id, results in results_by_question.items():
            if len(results) >= 2 and results[0].is_correct and results[1].is_correct:
                exclude_question_ids.add(q_id)
        
        question_pool = Question.query.filter(Question.id.notin_(exclude_question_ids)).all()

    else: # practice_type == 'all'
        title = "過去問演習（全問題）"
        question_pool = Question.query.all()

    if not question_pool:
        return render_template("practice.html", questions=[], message="対象の問題がありません。", title=title)

    num_to_sample = min(len(question_pool), num_questions)
    q_list = random.sample(question_pool, num_to_sample)

    return render_template("practice.html", questions=q_list, title=title)

# 結果
@app.route("/result")
def result():
    if "user" not in session:
        return redirect("/")
    ok = request.args.get("ok") == "True"
    return render_template("result.html", ok=ok)

# 管理者画面
@app.route("/admin")
def admin():
    if "user" not in session or session["user"] != "admin@example.com":
        return redirect("/")
    return render_template("admin.html", chapters=CHAPTERS)

@app.route("/api/questions/<category>")
def get_questions_by_category(category):
    if "user" not in session or session["user"] != "admin@example.com":
        return jsonify({"error": "Unauthorized"}), 401
    
    questions = Question.query.filter_by(category=category).all()
    
    # SQLAlchemyオブジェクトを辞書のリストに変換
    q_list = [
        {
            "id": q.id,
            "question": q.question,
        }
        for q in questions
    ]
    
    return jsonify(q_list)

@app.route("/api/question/<int:question_id>")
def get_question_details(question_id):
    if "user" not in session or session["user"] != "admin@example.com":
        return jsonify({"error": "Unauthorized"}), 401
        
    question = Question.query.get(question_id)
    
    if not question:
        return jsonify({"error": "Question not found"}), 404
        
    # SQLAlchemyオブジェクトを辞書に変換
    q_data = {
        "id": question.id,
        "question": question.question,
        "choice1": question.choice1,
        "choice2": question.choice2,
        "choice3": question.choice3,
        "choice4": question.choice4,
        "correct": question.correct,
        "category": question.category,
        "hint": question.hint,
        "url": question.url
    }
    
    return jsonify(q_data)

@app.route("/api/question/update/<int:question_id>", methods=["POST"])
def update_question(question_id):
    if "user" not in session or session["user"] != "admin@example.com":
        return jsonify({"error": "Unauthorized"}), 401
        
    question = Question.query.get(question_id)
    if not question:
        return jsonify({"error": "Question not found"}), 404
        
    data = request.json
    
    # フォームデータでquestionオブジェクトを更新
    question.question = data.get("question", question.question)
    question.choice1 = data.get("choice1", question.choice1)
    question.choice2 = data.get("choice2", question.choice2)
    question.choice3 = data.get("choice3", question.choice3)
    question.choice4 = data.get("choice4", question.choice4)
    # correctは整数に変換
    try:
        correct_val = int(data.get("correct"))
        if 1 <= correct_val <= 4:
            question.correct = correct_val
    except (ValueError, TypeError):
        # 不正な値の場合は更新しない
        pass
    question.category = data.get("category", question.category)
    question.hint = data.get("hint", question.hint)
    question.url = data.get("url", question.url)
    
    db.session.commit()
    
    return jsonify({"success": True, "message": "Question updated successfully"})

# ユーザー管理
@app.route("/user_management")
def user_management():
    if "user" not in session or session["user"] != "admin@example.com":
        return redirect("/")
    
    # admin以外のユーザーを取得
    users = User.query.filter(User.email != "admin@example.com").all()
    return render_template("user_management.html", users=users)

@app.route("/add_user", methods=["POST"])
def add_user():
    if "user" not in session or session["user"] != "admin@example.com":
        return redirect("/")
        
    email = request.form.get("email")
    password = request.form.get("password")

    if not email or not password:
        flash("メールアドレスとパスワードは必須です。", "danger")
        return redirect(url_for("user_management"))

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash("このメールアドレスは既に使用されています。", "warning")
        return redirect(url_for("user_management"))

    new_user = User(email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    flash(f"ユーザー「{email}」を登録しました。", "success")
    return redirect(url_for("user_management"))

@app.route("/delete_user", methods=["POST"])
def delete_user():
    if "user" not in session or session["user"] != "admin@example.com":
        return redirect("/")
        
    email = request.form.get("email")
    if not email:
        flash("削除するユーザーを選択してください。", "warning")
        return redirect(url_for("user_management"))

    if email == "admin@example.com":
        flash("管理者ユーザーは削除できません。", "danger")
        return redirect(url_for("user_management"))

    user_to_delete = User.query.filter_by(email=email).first()
    if user_to_delete:
        # 関連するQuizResultも削除する必要がある場合
        QuizResult.query.filter_by(user_id=user_to_delete.id).delete()
        
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f"ユーザー「{email}」を削除しました。", "success")
    else:
        flash("指定されたユーザーが見つかりません。", "danger")
        
    return redirect(url_for("user_management"))

@app.route("/admin_change_password", methods=["POST"])
def admin_change_password():
    if "user" not in session or session["user"] != "admin@example.com":
        return redirect("/")
        
    email = request.form.get("email")
    new_password = request.form.get("new_password")

    if not email or not new_password:
        flash("対象ユーザーと新しいパスワードを入力してください。", "warning")
        return redirect(url_for("user_management"))

    user_to_change = User.query.filter_by(email=email).first()
    if user_to_change:
        user_to_change.set_password(new_password)
        db.session.commit()
        flash(f"ユーザー「{email}」のパスワードを変更しました。", "success")
    else:
        flash("指定されたユーザーが見つかりません。", "danger")
        
    return redirect(url_for("user_management"))


#
if __name__ == "__main__":
    app.run(debug=True)