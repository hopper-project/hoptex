import pymysql.cursors
import subprocess

def reset():
    db = pymysql.connect(host='128.59.9.239', user='root', port=3306, db='arxiv')
    cursor = db.cursor()

    sql_command = """TRUNCATE equation_metadata"""
    cursor.execute(sql_command)

    sql_command = """TRUNCATE article_equations"""
    cursor.execute(sql_command)

    db.commit()
    db.close()

    subprocess.call(["rm","-rf","./dest/json_dest/*"])
    subprocess.call(["rm","-rf","./dest/xhtml/*"])
    subprocess.call(["rm","-rf","./sep/*"])
