import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from database import db
from model import Question, User, QuizResult
import random
from itertools import groupby

app = Flask(__name__)
app.secret_key = "test123"

# DB設定を追加
basedir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "instance", "quiz.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

#起動時にテーブルだけ作成
with app.app_context():
    db.create_all()

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
        return redirect(url_for("home"))
    else:
        return render_template("login.html", error="ログインに失敗しました")
    

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if request.method == "POST":
        email = request.form.get("email")
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(current_password):
            return render_template("change_password.html", error="IDまたは現在のパスワードが正しくありません。")
        
        if not new_password or new_password != confirm_password:
            return render_template("change_password.html", error="新しいパスワードが一致しません。")

        user.set_password(new_password)
        db.session.commit()
        
        # パスワード変更後はログイン画面に戻す
        return redirect(url_for("login"))

    # GET request
    return render_template("change_password.html")


# ホーム
@app.route("/home")
def home():
    if "user" not in session:
        return redirect("/")
    return render_template("home.html", user=session["user"])

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
    
    q_list = Question.query.filter_by(category=category).all()
    if not q_list:
        return f"カテゴリ「{category}」の問題がDBにありません"
    
    # 10問をランダムに選ぶ
    if len(q_list) > 10:
        q_list = random.sample(q_list, 10)
    
    return render_template("section_test.html", questions=q_list, category_name=category)

@app.route("/section_test", methods=["POST"])
def section_test_redirect():
    if "user" not in session:
        return redirect("/")
    
    category = request.form.get("category")
    if category:
        return redirect(url_for("section_test", category=category))
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

# 過去演習
@app.route("/practice", methods=["GET", "POST"])
def practice():
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        # --- 回答処理 (submit_section_testのロジックを流用) ---
        answers = request.form
        question_ids = [key.split('_')[1] for key in answers.keys() if key.startswith('answer_')]
        
        if not question_ids:
            return redirect(url_for("practice"))

        # 現在のユーザーのIDを取得
        current_user_email = session["user"]
        current_user = User.query.filter_by(email=current_user_email).first()
        if not current_user:
            return redirect("/") # ユーザーが見つからない場合はログインページへ

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
        
        return render_template("practice.html", 
            results=results, 
            score=score,
            total=total,
            percentage=f"{percentage:.1f}"
        )

    # --- 問題表示 (GETリクエスト) ---
    # クエリパラメータから問題数を取得、デフォルトは10
    try:
        num_questions = int(request.args.get('num', 10))
    except (ValueError, TypeError):
        num_questions = 10

    # 全ての問題を取得
    all_questions = Question.query.all()
    if not all_questions:
        return render_template("practice.html", questions=[]) # 空のリストを渡す

    # 指定された問題数をランダムに選ぶ
    num_to_sample = min(len(all_questions), num_questions)
    q_list = random.sample(all_questions, num_to_sample)

    return render_template("practice.html", questions=q_list)

from itertools import groupby

@app.route("/practice_incorrect", methods=["GET"])
def practice_incorrect():
    if "user" not in session:
        return redirect("/")

    current_user_email = session["user"]
    current_user = User.query.filter_by(email=current_user_email).first()
    if not current_user:
        return redirect("/")

    try:
        num_questions = int(request.args.get('num', 10))
    except (ValueError, TypeError):
        num_questions = 10

    # ユーザーのすべての解答履歴を問題ごと、タイムスタンプ降順で取得
    all_results = QuizResult.query.filter_by(user_id=current_user.id).order_by(QuizResult.question_id, QuizResult.timestamp.desc()).all()

    incorrect_question_ids = []
    # question_id でグループ化
    for q_id, results_group in groupby(all_results, key=lambda r: r.question_id):
        # グループをリストに変換
        recent_results = list(results_group)
        
        # 解答が2回以上あるかチェック
        if len(recent_results) >= 2:
            # 直近2回のうち、少なくとも1回が不正解かチェック
            if not recent_results[0].is_correct or not recent_results[1].is_correct:
                incorrect_question_ids.append(q_id)
        # 解答が1回しかない場合
        elif len(recent_results) == 1:
            # その1回が不正解かチェック
            if not recent_results[0].is_correct:
                incorrect_question_ids.append(q_id)

    if not incorrect_question_ids:
        return render_template("practice.html", questions=[], message="直近2回以上正解しなかった問題はありません。")

    # Questionオブジェクトを取得
    all_incorrect_questions = Question.query.filter(Question.id.in_(incorrect_question_ids)).all()

    # 指定された問題数をランダムに選ぶ
    num_to_sample = min(len(all_incorrect_questions), num_questions)
    q_list = random.sample(all_incorrect_questions, num_to_sample)

    return render_template("practice.html", questions=q_list, title="過去問演習（直近２回以上正解しなかった問題）")

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
    return render_template("admin.html")

#
if __name__ == "__main__":
    app.run(debug=True)