import pymysql.cursors
import subprocess

def main():
    db = pymysql.connect(host='128.59.9.239', user='root', port=3306, db='arxiv')
    cursor = db.cursor()

    cursor.execute("SELECT DATABASE()")
    data = cursor.fetchone()
    print ("Database name : %s " % data)

    sql_command = """TRUNCATE TABLE equation_metadata"""
    cursor.execute(sql_command)

    sql_command = """TRUNCATE TABLE article_equations"""
    cursor.execute(sql_command)

    db.commit()
    db.close()

    subprocess.call(["rm -rf ./dest/json_dest/*"], shell=True)
    subprocess.call(["rm -rf ./dest/xhtml_dest/*"], shell=True)
    subprocess.call(["rm -rf ./sep/*"], shell=True)

if __name__ == "__main__":
    main()
