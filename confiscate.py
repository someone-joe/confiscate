#!/usr/bin/env python3
"""存钱打卡小工具

规则：每天比前一天多存 0.1 元；金额累计满一年（达到 36.5 元 = 365 × 0.1）
后，于次日从 0.1 元重新起算（跨年重置）。

用法：
    python confiscate.py                 # 取 SQL 最近一条作起点，算到今天
    python confiscate.py 2026-08-01      # 同上，但算到指定结束日期
    python confiscate.py 2026-07-16 8.1  # 手动指定起点（上次日期/金额）
"""

from __future__ import annotations

import argparse
import re
from datetime import date, timedelta

STEP = 0.1        # 每日递增金额
YEAR_CAP = 36.5   # 年度上限：365 天 × 0.1 元
SQL_FILE = "confiscate_241011.sql"

_DATE = re.compile(r"\d{4}-\d{1,2}-\d{1,2}")
_NUM = re.compile(r"\d+(\.\d+)?")


def _norm_date(text: str):
    """把 '2026-3-18' 这类未补零的日期解析为 date，失败返回 None。"""
    try:
        y, m, d = text.split("-")
        return date(int(y), int(m), int(d))
    except (ValueError, AttributeError):
        return None


def parse_date(text: str) -> date:
    """解析 '2026-07-16' 或 '2026-7-16' 两种写法。"""
    return date.fromisoformat(text)


def build_plan(start_date: date, start_amount: float, end_date: date):
    """生成从 start_date 的次日到 end_date 的每日应存计划。

    返回 (明细[(日期, 金额)], 总额, 末日金额, 跨年重置次数)。
    末日金额即下一次打卡的起始金额。
    """
    details: list[tuple[date, float]] = []
    total = 0.0
    resets = 0
    amount = start_amount
    day = start_date
    while day < end_date:
        day += timedelta(days=1)
        amount = round(amount + STEP, 1)
        if amount > YEAR_CAP:          # 跨年重置
            amount = STEP
            resets += 1
        total += amount
        details.append((day, amount))
    return details, round(total, 1), amount, resets


def latest_record():
    """读取 SQL 中日期最近的一条记录，返回 (last_date, last_amount) 作为默认值。

    记录形如 (id, ..., total, start_date, end_amount, end_date)，
    取其中最大的日期为上次打卡日，取最后一个数值字段为上次打卡金额。
    文件缺失或无记录时返回 (None, None)。
    """
    try:
        with open(SQL_FILE, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return None, None

    # 按真实日期挑出“最近一条”，避免 '2026-3-18' 这类未补零字符串误判最大
    best_obj = None
    best_str = None
    best_fields = None
    for t in re.findall(r"\((\d+,\s*[^()]*)\)", text):
        fields = [x.strip().strip("'").strip('"') for x in t.split(",")]
        cand = None
        for x in fields:
            if _DATE.fullmatch(x):
                d = _norm_date(x)
                if d and (cand is None or d > cand[0]):
                    cand = (d, x)
        if cand and (best_obj is None or cand[0] > best_obj):
            best_obj, best_str, best_fields = cand[0], cand[1], fields
    if best_fields is None:
        return None, None

    amounts = [x for x in best_fields if _NUM.fullmatch(x)]
    last_amount = float(amounts[-1]) if amounts else None
    return best_str, last_amount


def next_id():
    """读取 sql 文件中的最大 id，返回下一个 id（文件缺失时返回 None）。"""
    try:
        with open(SQL_FILE, encoding="utf-8") as f:
            ids = [int(m) for m in re.findall(r"\((\d+),", f.read())]
    except FileNotFoundError:
        return None
    return max(ids) + 1 if ids else 1


def make_insert(id_, start_date, start_amount, total, end_date, end_amount) -> str:
    """拼出一条与历史结构一致的 INSERT 值列表。"""
    id_text = "NULL" if id_ is None else str(id_)
    return (f"({id_text}, '{start_amount}', '{start_date}', '{total}', "
            f"'{end_date}', '{end_amount}', '{end_date}')")


def report(start_date, start_amount, end_date, plan, from_sql=False):
    details, total, end_amount, resets = plan
    src = "（取自 SQL 最近一条）" if from_sql else ""
    print(f"上次：{start_date} 存 {start_amount} 元{src}")
    print(f"本次：算到 {end_date}")

    if not details:
        print("间隔 0 天，今日无需计算。")
        return

    interval = (end_date - start_date).days
    print(f"间隔 {interval} 天，跨年重置 {resets} 次，合计需存 {total} 元")
    print(f"末日（{end_date}）应存 {end_amount} 元，作为下次起点")

    if interval <= 31:
        print("明细：", "  ".join(f"{d.month:02d}-{d.day:02d}:{a}" for d, a in details))

    values = make_insert(next_id(), start_date, start_amount, total, end_date, end_amount)
    print("\n待写入 SQL：")
    print(values + ",")


def main() -> None:
    MISSING = object()  # 哨兵：用于区分“用户未填”与“填了空值”
    parser = argparse.ArgumentParser(description="存钱打卡计算器")
    parser.add_argument("last_date", nargs="?", default=MISSING,
                        help="上次打卡日期，如 2026-07-16（默认取 SQL 最近一条）")
    parser.add_argument("last_amount", nargs="?", type=float, default=MISSING,
                        help="上次打卡金额，如 8.1（默认取 SQL 最近一条）")
    parser.add_argument("end_date", nargs="?", default=date.today().isoformat(),
                        help="本次算到的日期，默认今天")
    args = parser.parse_args()

    from_sql = False
    if args.last_date is MISSING or args.last_amount is MISSING:
        sql_date, sql_amount = latest_record()
        if args.last_date is MISSING:
            args.last_date = sql_date
        if args.last_amount is MISSING:
            args.last_amount = sql_amount
        from_sql = True

    if args.last_date is None or args.last_amount is None:
        print("未能从 SQL 读取默认的上次日期/金额，请手动指定：")
        print("  python confiscate.py 2026-07-16 8.1 [结束日期]")
        return

    start_date = parse_date(args.last_date)
    end_date = parse_date(args.end_date)
    report(start_date, args.last_amount, end_date,
           build_plan(start_date, args.last_amount, end_date), from_sql)


if __name__ == "__main__":
    main()
