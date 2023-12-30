from tools import Wallet, Session, timestr_to_time, Recharge, User, get_session
import json, requests, time
from datetime import datetime, timedelta
from sqlalchemy.orm import joinedload


class Spider():
    def __init__(self):
        self.url = "https://api.trongrid.io/v1/accounts/TAZ5gPwfU4bn14dKRqJXbCZJGJMqgoJsaf/transactions/trc20?only_to=true&limit=10&contract_address=TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/112.0.0.0 Safari/537.36",
        }
        self.proxies = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
        self.result = []

    def parse(self):
        try:
            data = json.loads(requests.get(self.url, headers=self.headers, proxies=self.proxies).content.decode())
        except Exception as e:
            print(e)
            return 0
        for line in data.get("data", []):
            self.result.append(line)
        if not self.result:
            return 0
        return 1

    def run(self):
        if self.parse():
            print("获取数据成功！")
            return self.result
        return []


def update_wallte():
    session = get_session()
    spider = Spider()
    result = spider.run()

    for line in result:
        # 2.判断数据是否在数据库中
        order_id = line.get("transaction_id", "")
        block_timestamp = line.get("block_timestamp", "")
        if block_timestamp:
            create_time = timestr_to_time(block_timestamp / 1000)
            print("钱包转账时间：%s" % create_time)
        else:
            create_time = None
        try:
            obj = session.query(Wallet).filter_by(id=order_id).first()
        except Exception as e:
            print(e)
            continue
        if obj:
            continue
        money = int(line.get("value"))
        sender = line.get("from")
        recipient = line.get("to")
        print(sender)
        try:
            obj = Wallet(id=order_id, money=money, sender=sender, recipient=recipient, create_time=create_time)
        except Exception as e:
            print(e)
            continue
        # 3.入库
        try:
            session.add(obj)
            session.commit()
        except Exception as e:
            print(e)
            session.rollback()
            continue
    session.close()


print("开始工作中")
# 每过一分钟检测一下数据库的充值订单数据
while True:
    # 读取数据库数据
    session = Session()
    session.expire_all()
    try:
        orders = session.query(Recharge).options(joinedload('*')).filter_by(status=2).all()
    except Exception as e:
        print(e)
        orders = []
    if not orders:
        time.sleep(30)
        session.close()
        continue
    # 更新钱包记录
    update_wallte()
    for order in orders:
        # 订单金额
        money = str(int(float(order.money) * 1000000))
        print(money)
        # tg的id
        t_id = order.t_id
        # 订单创建时间
        create_time = order.create_time
        delta = timedelta(minutes=10)
        print("订单创建时间为：%s" % create_time)
        end_date = create_time + delta
        print("订单截止时间为：%s" % end_date)
        now = datetime.now()
        if now > end_date:
            print("订单已超时！并且设置了订单为超时状态。")
            # 设置订单状态为已超时
            order.status = 3
            try:
                session.add(order)
                session.commit()
            except Exception as e:
                print(e)
                session.rollback()
            continue
        # 通过订单金额去匹配钱包记录
        try:
            obj = session.query(Wallet).options(joinedload('*')).filter(Wallet.money == money,
                                                                        Wallet.create_time.between(create_time,
                                                                                                   end_date), ).first()
        except Exception as e:
            print(e)
            continue
        if not obj:
            print("没有匹配的订单")
            continue
        # 设置充值成功，根据tgid定位用户，给用户添加余额 TODO
        try:
            user = session.query(User).options(joinedload('*')).filter_by(t_id=t_id).first()
        except Exception as e:
            print(e)
            continue
        if not user:
            continue
        num = order.money
        print("充值前用户余额为：%s" % user.balance)
        user.balance = int(user.balance) + num
        print("充值后用户余额为：%s" % user.balance)
        order.status = 1
        flag = 1
        try:
            session.add(user)
            session.add(order)
            session.commit()
        except Exception as e:
            print(e)
            session.rollback()
            flag = 2
        if flag == 1:
            print("充值成功！")
        else:
            print("充值失败")
            order.status = 0
            try:
                session.add(order)
                session.commit()
            except Exception as e:
                session.rollback()
                continue
    time.sleep(6)
    session.close()
