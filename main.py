from telegram import Update
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, user, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
from lxml import etree
import telegram, base64, os, re, requests, time, json, schedule
from tools import get_session, Record, Recharge, register, get_order_id, User, Session
from datetime import datetime
import random, threading

TOKEN = ""
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher
admin_ids = ["1707841429"]
admin_id = "1707841429"
channal_id = ""
group_id = ""
admin_name = ""


def is_template_reply(text):
    if "项目名称" not in text:
        return 0
    if "项目介绍" not in text:
        return 0
    if "价格" not in text:
        return 0
    if "联系人" not in text:
        return 0
    return 1


def get_num():
    a = random.randint(1, 999)
    # 将整数转换为三位数的字符串
    a_str = str(a).zfill(3)
    return a_str


def turn_off(update, context):
    context.bot.delete_message(update.effective_chat.id, message_id=update.callback_query.message.message_id)
    context.bot.answer_callback_query(callback_query_id=update.callback_query.id, text='已关闭！')


# 取消订单
def move_order(update, context):
    print("开始取消订单")
    session = get_session()
    info = update.callback_query.to_dict()
    # tg的id
    t_id = info["from"]["id"]
    try:
        order = session.query(Recharge).filter_by(t_id=t_id, status=2).first()
    except Exception as e:
        print("查询订单出错")
        context.bot.send_message(update.effective_chat.id, "取消订单失败，请联系客服：@%s" % admin_name)
        session.close()
        return
    if not order:
        print("订单不存在")
        context.bot.send_message(update.effective_chat.id, "取消订单失败，请联系客服：@%s" % admin_name)
        session.close()
        return
    order.status = 4
    try:
        session.add(order)
        session.commit()
    except Exception as e:
        print(e)
        session.rollback()
        context.bot.send_message(update.effective_chat.id, "取消订单失败，请联系客服：@%s" % admin_name)
        return
    order_id = order.id
    firstname = order.firstname
    create_time = order.create_time
    money = order.money
    content = """
              <b>亲爱的客户：%s，您的订单id为：%s已被取消</b>
            
            ➖➖➖➖➖➖➖➖➖➖
            订单创建时间：%s
            转账金额: %s USDT
            ➖➖➖➖➖➖➖➖➖➖

    """ % (firstname, order_id, create_time, money)
    button_list = []
    for each in ['关闭', "再次充值"]:
        button_list.append(InlineKeyboardButton(each, callback_data=each))
    inline_button = InlineKeyboardMarkup(build_menu(button_list, n_cols=3))
    context.bot.send_message(update.effective_chat.id, content, parse_mode=ParseMode.HTML, reply_markup=inline_button)
    dispatcher.add_handler(CallbackQueryHandler(turn_off, pattern='^关闭$'))
    dispatcher.add_handler(CallbackQueryHandler(recharge, pattern='^再次充值$'))


def listen_order(order_id, chat_id, context):
    now1 = datetime.now()
    print("开始监听的时间为：%s" % str(now1))
    while True:
        session = Session()
        session.expire_all()
        print("监听订单中 %s" % str(now1))
        now = datetime.now()
        # 1.查询改订单id
        try:
            order = session.query(Recharge).filter_by(id=order_id).first()
        except Exception as e:
            print(e)
            time.sleep(20)
            continue
        print("查询出的订单状态：%s" % str(order.status))
        # 没有订单数据
        if not order:
            time.sleep(10)
            session.close()
            break
        if order.status == 1:
            # 用户支付成功
            print("订单完成！！")
            context.bot.send_message(chat_id, "订单充值成功！")
            context.bot.send_message(admin_id, "有新订单充值成功啦！\n时间：%s\n金额：%s\n昵称：%s" % (
                str(now), order.money, order.firstname))
            session.close()
            break
        if order.status == 3:
            print("订单超时！！")
            context.bot.send_message(chat_id, "订单已超时！")
            session.close()
            break
        if order.status == 4:
            print("订单已取消！！")
            session.close()
            break
        if order.status == 2:
            print("当前订单状态还是待支付！")
            # 判断是否已超时
            if (now - order.create_time).seconds > 600:
                print("订单已超时，现在设置为超时状态！")
                print(now)
                print(order.create_time)
                order.status = 3
                try:
                    session.add(order)
                    session.commit()
                except Exception as e:
                    print(e)
                    session.close()
        session.close()
        time.sleep(5)

    print("已退出监听订单代码")


def create_order(update, context):
    session = get_session()
    info = update.callback_query.to_dict()
    # tg的id
    t_id = info["from"]["id"]
    # 1.检测是否存在待支付的订单
    try:
        order = session.query(Recharge).filter_by(status=2, t_id=t_id).first()
    except Exception as e:
        print(e)
        context.bot.send_message(update.effective_chat.id, "创建订单失败，请联系客服：@%s" % admin_name)
        return
    if order:
        money = order.money
        now = order.create_time
        # 我的钱包地址
        myaddress = "TAZ5gPwfU4bn14dKRqJXbCZJGJMqgoJsaf"
        content = """
                    <b>充值订单创建成功，订单有效期为10分钟，请立即支付！</b>
\n➖➖➖➖➖➖➖➖➖➖\n转账地址: <code>%s</code> (TRC-20网络)\n转账金额: %s USDT 注意小数点！！！\n转账金额: %s USDT 注意小数点！！！\n转账金额: %s USDT 注意小数点！！！\n➖➖➖➖➖➖➖➖➖➖\n请注意转账金额务必与上方的转账金额一致，否则无法自动到账\n支付完成后, 请等待1分钟左右查询，自动到账。\n订单创建时间：%s
                """ % (myaddress, money, money, money, now)
        button_list = []
        for each in ['关闭', "取消订单", '联系客服']:
            if each == '联系客服':
                button_list.append(InlineKeyboardButton(each, url="https://t.me/%s" % admin_name))
            else:
                button_list.append(InlineKeyboardButton(each, callback_data=each))
        inline_button = InlineKeyboardMarkup(build_menu(button_list, n_cols=3))
        context.bot.send_message(update.effective_chat.id, content, parse_mode=ParseMode.HTML,
                                 reply_markup=inline_button)
        context.bot.send_message(update.effective_chat.id, content)
        dispatcher.add_handler(CallbackQueryHandler(move_order, pattern='^取消订单$'))
        return

    # 3.用户昵称
    first_name = info["from"]["first_name"]
    # 4.下单时间
    now = str(datetime.now())
    # 5.创建订单金额
    back_num = get_num()

    try:
        money = float(update.callback_query.data.replace(" USDT", ".") + back_num)
    except Exception as e:
        print("金额出错了！！")
        return
    # 我的钱包地址
    myaddress = "TAZ5gPwfU4bn14dKRqJXbCZJGJMqgoJsaf"
    content = """
            <b>充值订单创建成功，订单有效期为10分钟，请立即支付！</b>
            
➖➖➖➖➖➖➖➖➖➖
转账地址: <code>%s</code> (TRC-20网络)
转账金额: %s USDT 注意小数点！！！
转账金额: %s USDT 注意小数点！！！
转账金额: %s USDT 注意小数点！！！
➖➖➖➖➖➖➖➖➖➖
请注意转账金额务必与上方的转账金额一致，否则无法自动到账
支付完成后, 请等待1分钟左右查询，自动到账。
订单创建时间：%s
        """ % (myaddress, money, money, money, now)
    button_list = []
    for each in ['关闭', "取消订单", '联系客服']:
        if each == '联系客服':
            button_list.append(InlineKeyboardButton(each, url="https://t.me/%s" % admin_name))
        else:
            button_list.append(InlineKeyboardButton(each, callback_data=each))

    try:
        user = session.query(User).filter_by(t_id=t_id).first()
    except Exception as e:
        print("查询用户出错")
        context.bot.send_message(update.effective_chat.id, "创建订单失败，请联系客服：@%s" % admin_name)
        session.close()
        return
    if not user:
        print("用户不存在")
        context.bot.send_message(update.effective_chat.id, "创建订单失败，请联系客服：@%s" % admin_name)
        session.close()
        return

    # 将订单入库
    try:
        order = Recharge(status=2, from_address=myaddress, t_id=t_id, money=money, user_id=1, firstname=first_name)
        session.add(order)
        session.commit()
    except Exception as e:
        print("订单入库失败")
        session.rollback()
        context.bot.send_message(update.effective_chat.id, "创建订单失败，请联系客服：@%s" % admin_name)
        session.close()
        return
    inline_button = InlineKeyboardMarkup(build_menu(button_list, n_cols=3))
    context.bot.send_message(update.effective_chat.id, content, parse_mode=ParseMode.HTML, reply_markup=inline_button)
    dispatcher.add_handler(CallbackQueryHandler(turn_off, pattern='^关闭$'))
    # 监听取消订单
    dispatcher.add_handler(CallbackQueryHandler(move_order, pattern='^取消订单$'))

    # 开启另一个线程，监听订单完成与否，，出发发送消息至客户中
    t1 = threading.Thread(target=listen_order, args=(order.id, update.effective_chat.id, context))
    t1.start()
    session.close()


def recharge(update, context):
    print("触发充值！")
    button_list = []
    for each in ['30 USDT', '100 USDT', '200 USDT', '500 USDT', '1000 USDT', '2000 USDT', '关闭', '联系客服']:
        if each == '联系客服':  # tg://user?id=1707841429
            button_list.append(InlineKeyboardButton(each, url="t.me/%s" % admin_name))
        else:
            button_list.append(InlineKeyboardButton(each, callback_data=each))

    inline_button = InlineKeyboardMarkup(build_menu(button_list, n_cols=3))

    context.bot.send_message(update.effective_chat.id,
                             "—————💰寰球充值活动💰—————\n寰球供需初步定价为30u，充值优惠政策如下\n充值30u\n充值100u赠送50u\n充值200u赠送100u\n充值500u赠送500u\n充值1000u赠送1000u\n充值2000u赠送2000u\n——————————————\n公群老板发布供需，优惠政策  可联系客服： @%s\n\n 更变日期： 2023.6.1  \n\n请选择充值金额👇" % admin_name,
                             reply_markup=inline_button)

    dispatcher.add_handler(CallbackQueryHandler(create_order, pattern='^\d{1,} USDT$'))
    dispatcher.add_handler(CallbackQueryHandler(turn_off, pattern='^关闭$'))


def pass_con(update, context):
    # 通过审核，调用机器人发布数据
    reply_text = update.callback_query.to_dict()
    text = reply_text["message"]["text"]
    # 如何定位这个通过，是通过哪条记录的需求
    t_id = text.split("\n")[4].split("：")[-1]
    r_id = text.split("\n")[2].split("：")[-1]
    session = Session()
    session.expire_all()
    try:
        r_obj = session.query(Record).filter_by(status=2, t_id=t_id, id=r_id).first()
        user = session.query(User).filter_by(t_id=t_id).first()
    except Exception as e:
        print("查询数据库出错")
        updater.bot.send_message(admin_id, "记录为%s的需求审核失败！" % r_id)
        session.close()
        return
    if not r_obj or not user:
        print("没有记录")
        updater.bot.send_message(admin_id, "记录为%s的需求审核失败！" % r_id)
        session.close()
        return
    r_obj.status = 1
    try:
        count = session.query(Record).filter_by(status=1, t_id=t_id).count()
    except Exception as e:
        print("查询数据库出错")
        updater.bot.send_message(admin_id, "记录为%s的需求审核失败！" % r_id)
        session.close()
        return
    try:
        session.add(r_obj)
        session.commit()
    except Exception as e:
        print(e)
        session.rollback()

    print("开始发送至频道中！")
    # 审核成功，将该数据进行发送至设置的群聊当中
    content = "\n".join(text.split("\n")[6:])
    tmp = "\n用户：#%s【累计发布%s次】\n————————————————\n本条广告为公群付费广告，已开通寰球公群，寰球担保为您的资金保驾护航  ✅" % (
        user.invite_lj, count)
    content += tmp

    button = InlineKeyboardButton("官方群组", url="https://t.me/iluoboya")
    button2 = InlineKeyboardButton("发布广告", url="https://t.me/deepluobo_bot")
    keyboard = InlineKeyboardMarkup([[button, button2]])
    updater.bot.send_message(channal_id, content, reply_markup=keyboard)
    button3 = InlineKeyboardButton("官方频道", url="https://t.me/iluobo")
    keyboard = InlineKeyboardMarkup([[button, button3]])
    # 告知用户已发布
    updater.bot.send_message(t_id, "您的需求广告已发布，请移至频道查看！", reply_markup=keyboard)
    session.close()


def reject(update, context):
    # 通过审核，调用机器人发布数据
    reply_text = update.callback_query.to_dict()
    text = reply_text["message"]["text"]
    # 如何定位这个通过，是通过哪条记录的需求
    t_id = text.split("\n")[4].split("：")[-1]
    r_id = text.split("\n")[2].split("：")[-1]
    session = Session()
    session.expire_all()
    try:
        r_obj = session.query(Record).filter_by(status=2, t_id=t_id, id=r_id).first()
        user = session.query(User).filter_by(t_id=t_id).first()
    except Exception as e:
        print("查询数据库出错")
        updater.bot.send_message(admin_id, "记录为%s的需求审核失败！" % r_id)
        session.close()
        return
    if not r_obj:
        print("没有记录")
        updater.bot.send_message(admin_id, "记录为%s的需求审核失败！" % r_id)
        session.close()
        return
    r_obj.status = 0
    user.balance = str(int(user.balance) + 30)
    try:
        session.add(r_obj)
        session.add(user)
        session.commit()
    except Exception as e:
        print(e)
        session.rollback()
    session.close()

    button = InlineKeyboardButton("官方群组", url="https://t.me/iluoboya")
    button3 = InlineKeyboardButton("官方频道", url="https://t.me/iluobo")
    keyboard = InlineKeyboardMarkup([[button, button3]])
    # 告知用户已发布
    updater.bot.send_message(t_id, "您的需求广告审核不通过！\n请尝试重新发布，若还有疑问请及时联系管理员！",
                             reply_markup=keyboard)


# 监听用户回复的函数
def handle_user_reply(update, context):
    try:
        chat_id = update.message.chat_id
    except Exception:
        return
    reply_text = update.message.text
    print(chat_id)
    # 当前用户对象
    user = register(update)
    # 发布需求
    if is_template_reply(reply_text) and str(chat_id) != group_id:
        # 1.判断是否余额充足
        if not user:
            context.bot.send_message(chat_id=chat_id, text="提交信息失败，请稍后再试！")
        if user.balance < 30:
            # 创建充值按钮
            button = InlineKeyboardButton("立即充值", callback_data="recharge")
            button2 = InlineKeyboardButton("查看余额", callback_data="check_myself")
            keyboard = InlineKeyboardMarkup([[button, button2]])
            context.bot.send_message(chat_id=chat_id, text="当前余额为：%s\n余额不足，请及时充值！" % user.balance,
                                     reply_markup=keyboard)
            updater.dispatcher.add_handler(CallbackQueryHandler(recharge, pattern='^recharge$'))
            updater.dispatcher.add_handler(CallbackQueryHandler(personal2, pattern='^check_myself$'))
            return
        user.balance = user.balance - 30
        firstname = user.firstname
        session = get_session()
        reply_text2 = base64.b64encode(reply_text.encode()).decode()
        # 2.提交后台审核
        try:
            record = Record(status=2, t_id=user.t_id, user_id=user.id, firstname=user.firstname, values=reply_text2)
            session.add(user)
            session.add(record)
            session.commit()
        except Exception:
            session.rollback()
            context.bot.send_message(chat_id=chat_id, text="提交信息失败，请稍后再试！")
            session.close()
            return

        context.bot.send_message(chat_id=chat_id, text="提交信息成功！等待后台审核！")
        # 发送信息告知管理员
        button = InlineKeyboardButton("通过", callback_data="pass")
        button2 = InlineKeyboardButton("拒绝", callback_data="reject")
        keyboard = InlineKeyboardMarkup([[button, button2]])
        now = str(datetime.now())
        context.bot.send_message(chat_id=admin_id,
                                 text="您有新的供需广告需要审核！\n客户：%s\n内容id为：%s\n当前时间：%s\nid为：%s\n\n%s" % (
                                     firstname, record.id, now, user.t_id, reply_text),
                                 reply_markup=keyboard)
        updater.dispatcher.add_handler(CallbackQueryHandler(pass_con, pattern='^pass$'))
        updater.dispatcher.add_handler(CallbackQueryHandler(reject, pattern='^reject$'))
        session.close()
    elif update.message.reply_to_message:
        if update.message.reply_to_message["text"] == "供需机器人向您提供需求推送服务！ \n\n请选择下方菜单：":
            send_template(update, context)

    elif reply_text.strip() == "‍商务合作":
        context.bot.send_message(chat_id=chat_id, text="联系客服：@%s" % admin_name)

    elif reply_text == "✉️ 发布广告":
        send_template(update, context)

    elif reply_text == "💰 我要充值":
        recharge(update, context)

    elif reply_text == "👤 个人中心":
        personal(update, context)


    else:
        # 如果是在群聊则不发送
        if str(chat_id) != group_id:
            context.bot.send_message(chat_id=chat_id, text="未匹配到相关操作，请用/start命令重新开启。")


def build_menu(buttons, n_cols=2, header_buttons=None, footer_buttons=None):
    """
    Returns a list of inline buttons used to generate inlinekeyboard responses

    :param buttons: `List` of InlineKeyboardButton
    :param n_cols: 设置每行按钮数
    :param header_buttons: First button value
    :param footer_buttons: Last button value
    :return: `List` of inline buttons
    """
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


# 设置首页按钮 done
all_button_list = []
for i in ["✉️ 发布广告", "‍商务合作", '💰 我要充值', '👤 个人中心']:
    all_button_list.append(KeyboardButton(text=i, callback_data=i))
button = ReplyKeyboardMarkup(build_menu(all_button_list, n_cols=2), resize_keyboard=True)


def personal(update, context):
    button_list = []
    for each in ["立即充值", "关闭"]:
        button_list.append(InlineKeyboardButton(each, callback_data=each))

    inline_button = InlineKeyboardMarkup(build_menu(button_list))

    # 如果数据库中没有数据
    user = register(update)
    t_id = user.t_id
    firstname = user.firstname
    balance = user.balance
    # 需要从数据库中提取个人相关信息
    text = '*个人信息*\n\nTG昵称： *%s* \nTG ID： %s\n\n可用余额：*%s* USDT' % (firstname, t_id, balance)

    context.bot.send_message(update.effective_chat.id, text=text, reply_markup=inline_button,
                             parse_mode=telegram.ParseMode.MARKDOWN)

    dispatcher.add_handler(CallbackQueryHandler(turn_off, pattern='^关闭$'))
    updater.dispatcher.add_handler(CallbackQueryHandler(recharge, pattern='^立即充值$'))


def personal2(update, context):
    button_list = []
    for each in ["立即充值", "关闭"]:
        button_list.append(InlineKeyboardButton(each, callback_data=each))

    inline_button = InlineKeyboardMarkup(build_menu(button_list))
    info = update.callback_query.to_dict()
    # tg的id
    t_id = info["from"]["id"]
    session = get_session()
    try:
        user = session.query(User).filter_by(t_id=t_id).first()
    except Exception as e:
        print("查询用户出错")
        return
    t_id = user.t_id
    firstname = user.firstname
    balance = user.balance
    # 需要从数据库中提取个人相关信息
    text = '*个人信息*\n\nTG昵称： *%s* \nTG ID： %s\n\n可用余额：*%s* USDT' % (firstname, t_id, balance)

    context.bot.send_message(update.effective_chat.id, text=text, reply_markup=inline_button,
                             parse_mode=telegram.ParseMode.MARKDOWN)

    dispatcher.add_handler(CallbackQueryHandler(turn_off, pattern='^关闭$'))
    updater.dispatcher.add_handler(CallbackQueryHandler(recharge, pattern='^立即充值$'))


def send_template(update, context):
    template_message = "—————💰寰球付费广告💰—————\n寰球供需服务条款\n使用 @deepluobo_bot 发送广告默认遵守此条款【30/条】\n———————————————————\n1: ✅请按照模板编辑统一发送，广告行数不能超过10行.\n\n2: 🈲如有寰球频道用户举报被骗并且提供证据余额清空 对发布人进行拉黑处理，无退款渠道，无解封渠道。\n\n3: 🈲虚假广告 同行倒流 假项目 外部链接 不审核 不退回 发布请慎重❗️❗️❗️\n\n请按照下方模版编写好 发送给本机器人👇👇👇️"
    user_id = update.message.chat_id
    context.bot.send_message(chat_id=user_id, text=template_message)
    temp2 = "<code>项目名称：\n项目介绍：\n价格：\n联系人：\n频道：【选填/没频道可以不填】</code>"
    context.bot.send_message(chat_id=user_id, parse_mode=ParseMode.HTML, text=temp2)


# start函数 done
def start(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="👏欢迎使用寰球机器人\n耗资百万购买短位id，筹备6月之久只为见证实力担保  为您的交易保驾护航！\n👏欢迎加入官方频道：@hqgx0\n👏欢迎加入官方交流群：@MCG_Club",
                             reply_markup=button)

    register(update)


def alluser(update, context):
    chat_id = update.message.chat_id
    if str(chat_id) not in admin_ids:
        return
    session = Session()
    try:
        users = session.query(User).all()
    except Exception as e:
        print(e)
        return
    for user in users:
        name = user.firstname
        # 用户名
        t_id = user.t_id
        # 余额
        balance = user.balance

        # 查看所有会员信息
        context.bot.send_message(chat_id=update.message.chat_id,
                                 text="昵称：%s\ntg：%s\n余额：%s" % (name, t_id, balance))

    session.close()


def adminrecharge(update, context):
    chat_id = update.message.chat_id
    # 获取传递的参数
    args = context.args

    if str(chat_id) not in admin_ids:
        return
    # 处理参数逻辑，这里只是简单地将参数打印出来
    for arg in args:
        try:
            arg = int(arg)
        except Exception as e:
            return
    t_id = args[0]
    money = int(args[1])
    if len(args) > 2:
        return
    session = get_session()
    try:
        user = session.query(User).filter_by(t_id=t_id).first()
    except Exception as e:
        print(e)
        context.bot.send_message(chat_id=update.message.chat_id, text="数据库出错")
        return
    print("要充值的金额为：", money)
    user.balance = user.balance + money
    try:
        session.add(user)
        session.commit()
    except Exception as e:
        print(e)
        context.bot.send_message(chat_id=update.message.chat_id, text="充值失败")
        return
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="用户：%s\ntg：%s\n充值金额：%s\n状态：成功" % (user.firstname, t_id, money))
    context.bot.send_message(chat_id=t_id,
                             text="亲爱的用户：%s\n您的充值订单已完成\n金额%s已到账，请查收" % (user.firstname, money))


def send_help(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="供需机器人主要提供任务内容发布推送服务，广告信息将推送至频道：@hqgx0，官方交流群：@MCG_Club，每条需求30U，一经发布概不退换！使用/start命令开始使用吧！")


# 注册消息处理器
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('help', send_help))
dispatcher.add_handler(CommandHandler('alluser', alluser))
dispatcher.add_handler(CommandHandler('recharge', adminrecharge))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_user_reply))


def task():
    os.system("python task.py")


def send_advertisement():
    while True:
        now = str(datetime.now())
        content = """
<b>寰球供需频道定时广告</b>

➖➖➖➖➖➖➖➖➖➖
标题: <b>接机器人定制，机器人源码</b>
供需发布机器人: @deepluobo_bot
官方群组: @iluoboya
官方频道: @iluobo
➖➖➖➖➖➖➖➖➖➖
商务合作请联系：@%s
置顶广告请联系：@%s
当前时间：%s
                        """ % (admin_name, admin_name, now[:19])
        button = InlineKeyboardButton("官方群组", url="https://t.me/iluoboya")
        button1 = InlineKeyboardButton("商务合作", url="https://t.me/%s" % admin_name)
        button2 = InlineKeyboardButton("发布广告", url="https://t.me/deepluobo_bot")
        keyboard = InlineKeyboardMarkup([[button, button1, button2]])
        try:
            updater.bot.send_message(channal_id, content, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except Exception as e:
            time.sleep(600)
            continue
        time.sleep(600)


# 读取所有未审核的记录，发送至管理员
def get_allrecord():
    session = get_session()
    try:
        records = session.query(Record).filter_by(status=2).all()
    except Exception as e:
        print(e)
        return
    for obj in records:
        # 内容
        content = base64.b64decode(obj.values).decode()
        create_time = obj.create_time
        firstname = obj.firstname

        t_id = obj.t_id
        try:
            user = session.query(User).filter_by(t_id=t_id).first()
        except Exception as e:
            print(e)
            continue
        if not user:
            continue
        # 发送信息告知管理员
        button = InlineKeyboardButton("通过", callback_data="pass")
        button2 = InlineKeyboardButton("拒绝", callback_data="reject")
        keyboard = InlineKeyboardMarkup([[button, button2]])
        now = str(datetime.now())
        updater.bot.send_message(chat_id=admin_id,
                                 text="您有新的供需广告需要审核！\n客户：%s\n内容id为：%s\n创建时间：%s\nid为：%s\n\n%s" % (
                                     firstname, obj.id, str(create_time), user.t_id, content),
                                 reply_markup=keyboard)
        updater.dispatcher.add_handler(CallbackQueryHandler(pass_con, pattern='^pass$'))
        updater.dispatcher.add_handler(CallbackQueryHandler(reject, pattern='^reject$'))


# 运行定时任务
t2 = threading.Thread(target=task)
t2.start()

# t3 = threading.Thread(target=send_advertisement)
# t3.start()

get_allrecord()

if __name__ == '__main__':
    print('working.....')
    updater.start_polling()
