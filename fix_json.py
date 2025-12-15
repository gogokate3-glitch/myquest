import os

try:
    with open('questions.json', 'r', encoding='utf-8') as f:
        content = f.read()

    # 複数のエラーがある可能性を考慮し、すべて置換する
    fixed_content = content.replace('"} {"', '"}, {"')

    # ファイルが実際に変更されたか確認
    if content != fixed_content:
        with open('questions_fixed.json', 'w', encoding='utf-8') as f:
            f.write(fixed_content)

        # 元のファイルをバックアップして、修正済みファイルで置き換え
        # バックアップファイルが既に存在する場合は上書きしないようにする
        if not os.path.exists('questions.json.bak'):
            os.rename('questions.json', 'questions.json.bak')
        else:
            # 既にバックアップがあるので、元のファイルは削除
            os.remove('questions.json')
            
        os.rename('questions_fixed.json', 'questions.json')

        print("JSON file has been fixed.")
    else:
        print("No issues found that require fixing.")

except FileNotFoundError:
    print("Error: questions.json not found.")
except Exception as e:
    print(f"An error occurred: {e}")
