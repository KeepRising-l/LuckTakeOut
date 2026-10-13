"""重新导出 takeout/db.sqlite3 的完整 SQL 快照。

用法（在项目任意位置执行均可）：
    python export_snapshot.py

输出：覆盖同目录的 takeout_sqlite_full.sql（结构 + 全部数据）。
演示数据变化后，跑一次本脚本即可刷新"数据库脚本"。
"""

import sqlite3
import time
from pathlib import Path

base = Path(__file__).resolve().parents[2]          # 项目根目录
db_path = base / 'takeout' / 'db.sqlite3'
out_path = Path(__file__).with_name('takeout_sqlite_full.sql')

if not db_path.exists():
    raise SystemExit(f'找不到数据库文件：{db_path}')

con = sqlite3.connect(db_path)
with out_path.open('w', encoding='utf-8', newline='\n') as f:
    f.write('-- LuckTakeOut SQLite 完整数据库脚本（结构 + 演示数据）\n')
    f.write(f'-- 由 takeout/db.sqlite3 于 {time.strftime("%Y-%m-%d %H:%M")} 导出\n')
    f.write('-- 恢复方法见同目录 import_snapshot.py 或 08-部署与数据库说明.md\n\n')
    f.write('BEGIN TRANSACTION;\n')
    for line in con.iterdump():
        if line.strip() in ('BEGIN TRANSACTION;', 'COMMIT;'):
            continue
        f.write(line + '\n')
    f.write('COMMIT;\n')
con.close()
print(f'已导出：{out_path}')
