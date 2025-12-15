with open('questions.json', 'r', encoding='utf-8') as f:
    content = f.read()
with open('debug.txt', 'w', encoding='utf-8') as df:
    df.write(content[5600:5800])
print("Wrote a snippet of questions.json to debug.txt")
