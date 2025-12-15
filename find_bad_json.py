import json
import re

# `raw_decode`を使って、巨大なJSON配列を1オブジェクトずつ処理する
# 参考: https://stackoverflow.com/questions/21209997/python-json-loads-shows-valueerror-extra-data
def iter_json_array(s):
    decoder = json.JSONDecoder()
    s = s.strip()
    if not s.startswith('['):
        raise ValueError("JSON array must start with '['")
    s = s[1:] # 開始の'['を削除
    idx = 0
    while idx < len(s):
        s = s[idx:].lstrip()
        if not s:
            break
        if s.startswith(']'): # 配列の終わり
            break
        
        try:
            obj, end = decoder.raw_decode(s)
            yield obj
            idx = end
            # 次のオブジェクトの前にカンマがあるはず
            s = s[end:]
            if s.startswith(','):
                s = s[1:]
                idx = 1
            elif s.startswith(']'): # 最後の要素のあと
                break
            else: # カンマがない → エラー
                # エラー箇所を特定しやすくするために、周辺のテキストを表示
                error_pos = len(content) - len(s)
                raise ValueError(f"Expecting ',' delimiter at char {error_pos}")

        except json.JSONDecodeError as e:
            # エラーが発生した位置を計算して表示
            error_pos = len(content) - len(s) + e.pos
            print(f"JSON Decode Error detected near character {error_pos}")
            print("--- Error context ---")
            print(content[max(0, error_pos-50):error_pos+50])
            print("--- End of context ---")
            raise e

# --- メイン処理 ---
try:
    with open('questions.json', 'r', encoding='utf-8') as f:
        content = f.read()

    print("Checking questions.json for errors...")
    
    # すべてのオブジェクトをイテレートして問題がないか確認
    all_questions = list(iter_json_array(content))
    
    print(f"Successfully parsed {len(all_questions)} questions. The JSON file seems to be valid.")

except (ValueError, json.JSONDecodeError) as e:
    print(f"An error occurred: {e}")

