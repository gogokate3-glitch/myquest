from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from database import db
from model import Question
import random

app = Flask(__name__)
app.secret_key = "test123"

# DB設定を追加
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///quiz.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

#起動時にテーブルだけ作成
with app.app_context():
    db.create_all()

# 簡易ユーザー
USERS = {
    "student@example.com": "pass123",
    "admin@example.com": "admin123"
}

# ログイン
@app.route("/")
def login():
    return render_template("login.html")

@app.route("/try_login", methods=["post"])
def try_login():
    email = request.form.get("email")
    pw = request.form.get("password")

    if email in USERS and USERS[email] == pw:
        session["user"] = email
        return redirect(url_for("home"))
    else:
        return render_template("login.html", error="ログインに失敗しました")
    

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

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
@app.route("/section_test", methods=["GET", "POST"])
def section_test():
    if "user" not in session:
        return redirect("/")
    
    if request.method == "POST":
        # home.html からのカテゴリ選択POSTの場合
        if "category" in request.form:
            category = request.form.get("category")
            q_list = Question.query.filter_by(category=category).all()
            if not q_list:
                return f"カテゴリ「{category}」の問題がDBにありません"
            
            # 10問をランダムに選ぶ
            if len(q_list) > 10:
                q_list = random.sample(q_list, 10)
            
            return render_template("section_test.html", questions=q_list, category_name=category)

        # 予期しないPOSTの場合はhomeに戻す
        else:
            return redirect(url_for("home"))
    
    # GETで直接アクセスされた場合はhomeへリダイレクト
    return redirect(url_for("home"))


@app.route("/submit_section_test", methods=["POST"])
def submit_section_test():
    if "user" not in session:
        return redirect("/")

    answers = request.form
    question_ids = [key.split('_')[1] for key in answers.keys() if key.startswith('answer_')]
    
    results = []
    questions = Question.query.filter(Question.id.in_(question_ids)).all()
    question_map = {str(q.id): q for q in questions}

    for q_id in question_ids:
        question = question_map.get(q_id)
        if question:
            user_answer_val = answers.get(f'answer_{q_id}')
            # ユーザーが回答しなかった場合
            if user_answer_val is None:
                user_answer_val = -1 # 未回答を示す値
            else:
                user_answer_val = int(user_answer_val)
            
            is_correct = (user_answer_val == question.correct)

            choices = [question.choice1, question.choice2, question.choice3, question.choice4]
            
            # ユーザーの回答テキスト
            user_choice_text = choices[user_answer_val - 1] if 0 < user_answer_val <= 4 else "未回答"
            # 正解のテキスト
            correct_choice_text = choices[question.correct - 1] if 0 < question.correct <= 4 else ""

            results.append({
                "question": question,
                "user_answer": user_answer_val,
                "user_choice_text": user_choice_text,
                "correct_answer": question.correct,
                "correct_choice_text": correct_choice_text,
                "is_correct": is_correct
            })
    
    # category_name を取得するために、最初の質問のカテゴリを使用
    category_name = questions[0].category if questions else ""

    return render_template("section_test.html", results=results, category_name=category_name)


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
        answer = int(request.form.get("choice"))
        correct = int(request.form.get("correct"))
        result = (answer == correct)
        return redirect(url_for("result", ok=result))
    
    q_list = Question.query.filter_by(category="practice").all()
    if not q_list:
        return "過去問の問題がありません"
    
    q = random.choice(q_list)

    return render_template(
        "practice.html",
        question=q.question,
        choices=[q.choice1, q.choice2, q.choice3, q.choice4],
        correct=q.correct,
    )

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
    if session.get("user") != "admin@example.com":
        return redirect("/")
    return render_template("admin.html")

#
if __name__ == "__main__":
    app.run(debug=True)