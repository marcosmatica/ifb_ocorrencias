import re


def convert_url(url):
    """Converte URL do Google Drive de uc?export=view para thumbnail"""
    # Extrair FILE_ID do formato: uc?export=view&id=FILE_ID
    match = re.search(r'[?&]id=([^&]+)', url)
    if match:
        file_id = match.group(1)
        print(file_id)
        return f"https://drive.google.com/thumbnail?id={file_id}&sz=w400"
    return url


# ===== OPÇÃO 1: SQLite =====
def update_sqlite(db_path, table_name='core_estudante', url_column='foto_url'):
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(f"SELECT id, {url_column} FROM {table_name}")
    students = cursor.fetchall()

    for student_id, url in students:
        if url and 'uc?export=view' in url:
            new_url = convert_url(url)
            cursor.execute(f"UPDATE {table_name} SET {url_column} = ? WHERE id = ?",
                           (new_url, student_id))

    conn.commit()
    conn.close()
    print(f"✓ {cursor.rowcount} URLs atualizados no SQLite")


# ===== OPÇÃO 2: MySQL/PostgreSQL =====
def update_mysql(host, user, password, database, table_name='students', url_column='photo_url'):
    import mysql.connector
    conn = mysql.connector.connect(host=host, user=user, password=password, database=database)
    cursor = conn.cursor()

    cursor.execute(f"SELECT id, {url_column} FROM {table_name}")
    students = cursor.fetchall()

    for student_id, url in students:
        if url and 'uc?export=view' in url:
            new_url = convert_url(url)
            cursor.execute(f"UPDATE {table_name} SET {url_column} = %s WHERE id = %s",
                           (new_url, student_id))

    conn.commit()
    conn.close()
    print(f"✓ {cursor.rowcount} URLs atualizados no MySQL")


# ===== OPÇÃO 3: JSON =====
def update_json(file_path, url_field='photo_url'):
    import json

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    count = 0
    for student in data:
        if url_field in student and 'uc?export=view' in student[url_field]:
            student[url_field] = convert_url(student[url_field])
            count += 1

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✓ {count} URLs atualizados no JSON")


# ===== OPÇÃO 4: CSV =====
def update_csv(file_path, url_column='photo_url'):
    import csv

    rows = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if url_column in row and 'uc?export=view' in row[url_column]:
                row[url_column] = convert_url(row[url_column])
            rows.append(row)

    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    print(f"✓ {len(rows)} linhas processadas no CSV")


# ===== EXECUTAR =====
if __name__ == "__main__":
    # Escolha o método conforme seu banco:

    # SQLite:
    update_sqlite('db.sqlite3')

    # MySQL:
    # update_mysql('localhost', 'user', 'password', 'dbname')

    # JSON:
    # update_json('students.json')

    # CSV:
    # update_csv('students.csv')

    #print("Escolha e descomente o método apropriado acima")