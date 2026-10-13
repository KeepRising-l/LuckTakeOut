"""把同目录的 takeout_sqlite_full.sql 恢复为项目的 takeout/db.sqlite3。

用法（任何装了 Python 的电脑，无需 Django 环境）：
    python import_snapshot.py

说明：
- 目标位置已有 db.sqlite3 时会拒绝执行（防止误覆盖），请先手动改名或删除；
- 这就是"在别的电脑上快速恢复完整演示数据库"的一键脚本。
"""

import sqlite3
import sys
from pathlib import Path

base = Path(__file__).resolve().parents[2]          # 项目根目录（E:\pythonTakeOut）
db_path = base / 'takeout' / 'db.sqlite3'
sql_path = Path(__file__).with_name('takeout_sqlite_full.sql')

if not sql_path.exists():
    print(f'找不到 SQL 快照文件：{sql_path}')
    sys.exit(1)

if db_path.exists():
    print(f'目标数据库已存在：{db_path}')
    print('为避免覆盖现有数据，请先手动改名或删除它，再重新运行本脚本。')
    sys.exit(1)

con = sqlite3.connect(db_path)
con.executescript(sql_path.read_text(encoding='utf-8'))
con.close()
print(f'数据库已恢复：{db_path}')
