from dataclasses import MISSING
from nonebot import on_command
from nonebot import rule
from nonebot import on_request
from nonebot import on_notice
from nonebot.adapters import Bot,Event
from nonebot.adapters.cqhttp.event import MessageEvent, Status
from nonebot.rule import to_me
from nonebot.adapters.cqhttp.permission import GROUP_ADMIN, GROUP_OWNER, PRIVATE_FRIEND
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.adapters.cqhttp import Bot,Message,GroupMessageEvent,bot,FriendRequestEvent,GroupRequestEvent,GroupDecreaseNoticeEvent
from nonebot.adapters.cqhttp.message import MessageSegment
from nonebot import require
from nonebot.log import logger
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from . import data_source
from . import model
from . import config
import asyncio
import nonebot
import threading
model.Init()
config.token=data_source.init()
tweet_index=0
def flush_token():
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.71 Safari/537.36 Edg/94.0.992.38') #设置user-agent请求头
    dcap["phantomjs.page.settings.loadImages"] = False #禁止加载图片
    driver=webdriver.PhantomJS(desired_capabilities=dcap)
    driver.set_page_load_timeout(20)
    driver.set_script_timeout(20)
    try:
        driver.get('https://mobile.twitter.com/Twitter')
    except:
        logger.error('twitter.com请求超时！')
        driver.execute_script("window.stop()")
    data=driver.get_cookie('gt') 
    driver.close()
    driver.quit()
    if data==None:
        logger.error('token更新失败，请检查网络/代理是否正常！')
        raise Exception('token更新失败，请检查代理设置，详见项目主页')
    token=data['value']
    logger.success('token更新成功！')
    config.token=token
scheduler = require('nonebot_plugin_apscheduler').scheduler
@scheduler.scheduled_job('interval',minutes=5,id='flush_token')
async def flush():#定时刷新token
    flush=threading.Thread(target=flush_token)
    flush.start()
    logger.info('开始刷新token')
@scheduler.scheduled_job('interval',seconds=15,id='tweet')
async def tweet():#定时推送用户最新推文
    if model.Empty():
        return
    (schedBot,)=nonebot.get_bots().values()
    global tweet_index
    users=model.GetUserList()
    tweet_index %=len(users)
    tweet_id,data=await data_source.get_latest_tweet(users[tweet_index][2],config.token)
    if tweet_id=='' or users[tweet_index][3]==tweet_id:
        tweet_index+=1
        return
    logger.info('检测到 %s 的推特已更新'%(users[tweet_index][1]))
    model.UpdateTweet(users[tweet_index][0],tweet_id)
    text,translate,media_list,url=data_source.get_tweet_details(data)
    translate=await data_source.baidu_translate(config.appid,translate,config.baidu_token)
    media=''
    for item in media_list:
        media+=MessageSegment.image(item)+'\n'
    cards=model.GetALLCard(users[tweet_index][0])
    for card in cards:
        if card[1]==1:#是群聊
            if card[2]==1:#需要翻译
                await schedBot.call_api('send_msg',**{
                    'message':text+translate+media+url,
                        'group_id':card[0]
                })
            else:#不需要翻译
                await schedBot.call_api('send_msg',**{
                        'message':text+media+url,
                        'group_id':card[0]
                })
        else:#私聊
            if card[2]==1:#需要翻译
                await schedBot.call_api('send_msg',**{
                    'message':text+translate+media+url,
                    'user_id':card[0]
                })
            else:
                await schedBot.call_api('send_msg',**{
                    'message':text+media+url,
                    'user_id':card[0]
                })
    tweet_index+=1
adduser = on_command('推特关注',rule=to_me(),priority=5,permission=GROUP_ADMIN|GROUP_OWNER|PRIVATE_FRIEND|SUPERUSER,)
@adduser.handle()#添加用户
async def handle(bot: Bot, event: MessageEvent, state: T_State):
    is_group=int(isinstance(event,GroupMessageEvent))
    id=event.get_session_id()
    if not id.isdigit():
        id=id.split('_')[1]
    args = str(event.get_message()).strip()
    msg = '指令格式错误！请按照：推特关注 推特ID'
    if args!='':
        user=model.GetUserInfo(args)
        if len(user)!=0:
                status=model.AddCard(args,id,is_group)
                if status==0:
                    msg='{}({})添加成功！'.format(user[1],args) #待测试
                else:
                    msg='{}({})已存在！'.format(user[1],args) #待测试
        else:
            user_name,user_id=await data_source.get_user_info(args,config.token)
            if(user_id!=''):
                model.AddNewUser(args,user_name,user_id)
                model.AddCard(args,id,is_group)
                msg='{}({})添加成功！'.format(user_name,args) #待测试
            else:
                msg='{} 推特ID不存在或网络错误！'.format(args)
    Msg = Message(msg)
    await adduser.finish(Msg)
    
removeuser = on_command('推特取关',rule=to_me(),priority=5,permission=GROUP_ADMIN|GROUP_OWNER|PRIVATE_FRIEND|SUPERUSER,)
@removeuser.handle()#取关用户
async def handle(bot: Bot, event: MessageEvent, state: T_State):
    is_group=int(isinstance(event,GroupMessageEvent))
    id=event.get_session_id()
    if not id.isdigit():
        id=id.split('_')[1]
    args = str(event.get_message()).strip()
    msg = '指令格式错误！请按照：推特取关 UID'
    if args!='':
        user=model.GetUserInfo(args)
        if len(user)==0:
            msg = '{} 用户不存在！请检查推特ID是否错误'.format(args)
        else:
            status=model.DeleteCard(args,id,is_group)
            if status!=0:
                msg='{}({})不在当前群组/私聊关注列表'.format(user[1],args)
            else:
                msg='{}({})删除成功！'.format(user[1],args)
    Msg = Message(msg)
    await adduser.finish(Msg)

alllist = on_command('推特列表',rule=to_me(),priority=5,permission=GROUP_ADMIN|GROUP_OWNER|PRIVATE_FRIEND|SUPERUSER,)
@alllist.handle()#显示当前群聊/私聊中的关注列表
async def handle(bot: Bot, event: MessageEvent, state: T_State):
    is_group=int(isinstance(event,GroupMessageEvent))
    id=event.get_session_id()
    if not id.isdigit():
        id=id.split('_')[1]
    msg='用户名(推特ID)\n'
    content=''
    if not id.isdigit():
        id=id.split('_')[1]
    user=model.GetUserList()
    for index in user:
        card=model.GetCard(index[0],id,is_group)
        if len(card)!=0:
            content+='{}({})\n{}\n'.format(index[1],index[0],str(card[2]).replace('1','推文翻译：开').replace('0','推文翻译：关'))
    if content=='':
        msg='当前群聊/私聊关注列表为空！'
    else:
        msg=msg+content
    Msg=Message(msg)
    await alllist.finish(Msg)

ontranslate = on_command('开启翻译',rule=to_me(),priority=5,permission=GROUP_ADMIN|GROUP_OWNER|PRIVATE_FRIEND|SUPERUSER,)
@ontranslate.handle()#开启推文翻译
async def handle(bot: Bot, event: MessageEvent, state: T_State):
    is_group=int(isinstance(event,GroupMessageEvent))
    id=event.get_session_id()
    if not id.isdigit():
        id=id.split('_')[1]
    args = str(event.get_message()).strip()
    msg = '指令格式错误！请按照：开启翻译 推特ID'
    if args!='':
        user=model.GetUserInfo(args)
        if len(user)==0:
            msg = '{} 用户不存在！请检查UID是否错误'.format(args)
        else:
            card=model.GetCard(args,id,is_group)
            if len(card)==0:
                msg='{}({})不在当前群组/私聊关注列表！'.format(user[1],args)
            else:
                model.TranslateON(args,id,is_group)
                msg='{}({})开启推文翻译！'.format(user[1],args)
    Msg=Message(msg)
    await ontranslate.finish(Msg)

offtranslate = on_command('关闭翻译',rule=to_me(),priority=5,permission=GROUP_ADMIN|GROUP_OWNER|PRIVATE_FRIEND|SUPERUSER,)
@offtranslate.handle()#关闭推文翻译
async def handle(bot: Bot, event: MessageEvent, state: T_State):
    is_group=int(isinstance(event,GroupMessageEvent))
    id=event.get_session_id()
    if not id.isdigit():
        id=id.split('_')[1]
    args = str(event.get_message()).strip()
    msg = '指令格式错误！请按照：关闭翻译 推特ID'
    if args!='':
        user=model.GetUserInfo(args)
        if len(user)==0:
            msg = '{} 用户不存在！请检查UID是否错误'.format(args)
        else:
            card=model.GetCard(args,id,is_group)
            if len(card)==0:
                msg='{}({})不在当前群组/私聊关注列表！'.format(user[1],args)
            else:
                model.TranslateOFF(args,id,is_group)
                msg='{}({})关闭推文翻译！'.format(user[1],args)
    Msg=Message(msg)
    await offtranslate.finish(Msg)

help = on_command('推特帮助',rule=to_me(),priority=5,permission=GROUP_ADMIN|GROUP_OWNER|PRIVATE_FRIEND|SUPERUSER,)
@help.handle()#启动动态推送
async def handle(bot: Bot, event: MessageEvent, state: T_State):
    menu='HanayoriBot(推特插件)目前支持的功能：\n(请将ID替换为需操作的推特ID，也即@后面的名称)\n推特关注 ID\n推特取关 ID\n推特列表\n开启翻译 ID\n关闭翻译 ID\n'
    info='当前版本：v0.1\n作者：鹿乃ちゃんの猫\n反馈邮箱：kano@hanayori.top'
    msg=menu+info
    Msg=Message(msg)
    await help.finish(Msg)

group_decrease = on_notice(priority=5)
@group_decrease.handle()
async def _(bot: Bot, event: GroupDecreaseNoticeEvent, state: T_State):
    id=event.get_session_id()
    if not id.isdigit():
        id=id.split('_')[1]
    if event.self_id == event.user_id:
        model.DeleteGroupCard(id)
