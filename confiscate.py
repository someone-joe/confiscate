import time
import datetime
import os
import re

# import pymysql

# 连接数据库并将值传入
# db = pymysql.connect(host='localhost', port=3306, user='root', password='123qwe+++', db='confiscate', charset='utf8')
# cursor = db.cursor()
"""
字段分别为：   
    id              INT UNSIGNED AUTO_INCREMENT,
    money_old       VARCHAR(20) COMMENT '运算时输入的打卡金额',
    date_old        varchar(15)	COMMENT '运算时输入的打卡时间',
    total           VARCHAR(20) COMMENT '此次运算的打卡金额',
    date_added      date	comment'此次运算的添加时间',
    next_money      VARCHAR(20) comment '下次执行数据',
    next_date_up    VARCHAR(20) comment '下次执行开始时间，即上一个的添加时间'
"""


def new_confiscate(db_date, money, is_exec = 0):
    """
    输入断开签到的月日，和最近一天签到金额，算出续签的金额
    :param data: "2022-04-11"
    :param money: 35.4
    """
    logger = {"confiscate_info": [], "is_exec": {"y": [], "n": []}, }
    confiscate_info = logger["confiscate_info"]
    exec_y_result = logger["is_exec"]["y"]
    exec_n_result = logger["is_exec"]["n"]

    ISOTIMEFORMAT = "%Y-%m-%d"
    now = time.strftime(ISOTIMEFORMAT)
    # now = "2022-06-10"
    # 当前日期的月和日
    now_date = datetime.datetime.strptime(now, ISOTIMEFORMAT).date()

    old_date = datetime.datetime.strptime(db_date, ISOTIMEFORMAT).date()

    # 间隔天数
    interval = (now_date - old_date).days

    # 这里开始计算金额
    remain_interval = sum = confiscate_date = cur_confiscate = 0
    if interval:
        for i in range(1, interval + 1):
            cur_confiscate = round(money + i * 0.1, 1)
            # 若是满了一年，则停止累加，开始新的一轮
            if cur_confiscate > 36.5:
                info = "哇~又过了一年了，真棒！"
                confiscate_info.append(info)
                print(info)
                remain_interval = interval - i
                break
            sum += cur_confiscate
            confiscate_date = old_date + datetime.timedelta(days=i)
            info = "{}，需支付{}元！".format(confiscate_date, cur_confiscate)
            confiscate_info.append(info)
            print(info)

        if remain_interval:
            for i in range(1, remain_interval + 1):
                cur_confiscate = round(i * 0.1, 1)
                new_confiscate_date = confiscate_date + datetime.timedelta(days=i)
                sum += cur_confiscate
                info = "{}，需支付{}元！".format(new_confiscate_date, cur_confiscate)
                confiscate_info.append(info)
                print(info)

        info = "与上次提交时隔{}天，总共需支付{}元".format(interval, round(sum, 1))
        confiscate_info.append(info)
        print(info)

        # 用于转账时的简短描述
        description = "算了，看着有点复杂"
        next_money = cur_confiscate
        next_date_up = now_date

        # 构造待写入 SQL 脚本的数据行
        record = {
            'money_old': str(money),
            'date_old': str(old_date),
            'total': str(round(sum, 1)),
            'date_added': str(now_date),
            'next_money': str(next_money),
            'next_date_up': str(next_date_up),
        }
        logger['record'] = record

        if is_exec in ('y', 'Y', 'yes', 'yep'):
            info = "正在存入数据库..."
            exec_y_result.append(info)
            print(info)
            sql = "insert into confiscate values (null,%s, '%s',%s, now(), %s,'%s')" \
                  % (str(money), str(old_date), str(round(sum, 1)), str(next_money), str(next_date_up))
            # 检查连接是否断开，如果断开就进行重连
            db.ping(reconnect=True)
            try:
                cursor.execute(sql)
                db.commit()
            except Exception as e:
                info = "数据库储存有点异常~\n没有存进去！", e
                exec_y_result.append({'failed': info})
                print(info)
            else:
                info = "数据库存储成功！"
                exec_y_result.append({'successful': info})
                print(info)
        else:
            info = '好的，不执行'
            exec_n_result.append(info)
            print(info)

    elif interval == 0:
        info = "输入时间为当天~"
        confiscate_info.append(info)
    else:
        info = "时间间隔出了问题，请确认！"
        confiscate_info.append(info)

    return logger


def deal_date():
    sql1 = 'select next_date_up from confiscate order by id desc limit 1;'
    sql2 = 'select next_money from confiscate order by id desc  limit 1;'
    # 检查连接是否断开，如果断开就进行重连
    db.ping(reconnect=True)
    cursor.execute(sql1)
    for data in cursor.fetchall():
        next_date_up = data[0]

    cursor.execute(sql2)
    for data in cursor.fetchall():
        next_money = float(data[0])

    print(next_date_up, next_money)
    return [next_date_up, next_money]

def del_last_record():
    """
    待测，不太能行
    :return:
    """
    sql = 'delete from confiscate where id=(select id from confiscate order by id desc limit 1);'
    cursor.execute(sql)
    db.commit()

def close_py():
    cursor.close()

if __name__ == '__main__':
    # date, money = deal_date()
    # 根据前面的查询执行
    # result = new_confiscate(date, money, 'N')
    result = new_confiscate("2026-07-16", 8.1)
    print(result)
    x = input("111")
