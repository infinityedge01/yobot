from io import BytesIO
import os
import requests
from PIL import Image
from aiocqhttp.api import Api
import matplotlib.pyplot as plt
import base64
import time
import aiohttp
import asyncio

import sqlite3
from PIL import Image,ImageFont,ImageDraw

class Create_resignation_report:
    def __init__(self,glo_setting,bot_api,*args, **kwargs):
        self.setting = glo_setting
        self.api = bot_api
        self.constellation_set = {'1':'射手','2':'摩羯','3':'水瓶','4':'双鱼','5':'白羊','6':'金牛','7':'双子','8':'巨蟹','9':'狮子','10':'处女','11':'天秤','12':'天蝎'}
        self.time = time.localtime(time.time())
        self.month = '9'#str(self.time.tm_mon)
        self.year = str(self.time.tm_year)
        self.constellation = '处女'#self.constellation_set[self.month]
        self.port = self.setting['port']
        
    async def execute_async(self,ctx):
        cmd = ctx['raw_message']
        if cmd == '生成离职报告':
            moban = '公会离职报告模板.jpg'
        elif cmd == '生成会战报告':
            moban = '公会本期报告模板.jpg'
        else:
            return
        uid = ctx['user_id']
        nickname = ctx['sender']['nickname']
        gid = ctx['group_id']
        try:
            apikey = get_apikey(gid)
        except:
            await self.api.send_msg(group_id=gid, message='没有找到您的会战信息')
            return
        url = f'http://127.0.0.1:{self.port}/yobot/clan/{gid}/statistics/api/?apikey={apikey}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                data = await resp.json()
        clanname = data['groupinfo'][0]['group_name']
        challenges: list = data['challenges']
        is_continue = 0
        for chl in challenges[::-1]:
            if chl['qqid'] != uid:
                challenges.remove(chl)
            elif chl['is_continue'] == True:
                is_continue += 1
        total_chl = len(challenges) - is_continue
        damage_to_boss: list = [0 for i in range(5)]
        challenge_to_boss: list = [0 for i in range(5)]
        total_damage = 0
        for chl in challenges[::-1]:
            damage_to_boss[chl['boss_num']-1] += chl['damage']
            total_damage += chl['damage']
        avg_day_damage = int(total_damage/6)
        for chl in challenges[::-1]:
            if chl['damage'] != 0:
                if chl['health_ramain'] == 0 or chl['is_continue'] == True:
                    challenge_to_boss[chl['boss_num']-1] += 0.5
                else:
                    challenge_to_boss[chl['boss_num']-1] += 1
                challenges.remove(chl)
        Miss_chl = len(challenges)     
        if total_chl >= 18:
            disable_chl = 0
            attendance_rate = 100
        else:
            disable_chl = 18 - total_chl
            attendance_rate = round(total_chl/18*100,2)
        
        #设置中文字体
        plt.rcParams['font.family'] = ['Microsoft YaHei']
        plt.figure(figsize=(3.5, 3.5))
        labels = [f'{x+1}王' for x in range(0,5) if challenge_to_boss[x] != 0]
        sizes = [x for x in challenge_to_boss if x != 0]
        patches, l_text, p_text = plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90,labeldistance=1.1)
        for t in l_text:
            #为标签设置字体大小
            t.set_size(15)
        for t in p_text:
            #为比例设置字体大小
            t.set_size(10)
        buf = BytesIO()
        plt.savefig(buf, format='png', transparent=True, dpi=120)
        pie_img = Image.open(buf)

        #清空饼图
        plt.clf()

        x = [f'{x}王' for x in range(1,6)]
        y = damage_to_boss
        plt.figure(figsize=(4.3,2.8))
        ax = plt.axes()

        #设置标签大小
        plt.tick_params(labelsize=15)

        #设置y轴不显示刻度
        plt.yticks([])

        #绘制柱状图
        recs = ax.bar(x,y,width=0.618)

        #删除边框
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)

        #设置数量显示
        for i in range(0,5):
            rec = recs[i]
            h = rec.get_height()
            plt.text(rec.get_x()-0.1, h*1.05, f'{int(damage_to_boss[i]/10000)}万',fontdict={"size":15})

        buf = BytesIO()
        plt.savefig(buf, format='png', transparent=True, dpi=120)
        bar_img = Image.open(buf)

        #将饼图和柱状图粘贴到模板图,mask参数控制alpha通道，括号的数值对是偏移的坐标
        current_folder = os.path.dirname(__file__)
        img = Image.open(os.path.join(current_folder,moban))
        img.paste(pie_img, (635,910), mask=pie_img.split()[3])
        img.paste(bar_img, (130,950), mask=bar_img.split()[3])
        #添加文字到img
        row1 = f'''
        {total_chl}

        {disable_chl}

        {total_damage}
        '''
        row2 = f'''
        {attendance_rate}%

        {Miss_chl}

        {avg_day_damage}
        '''
        
        add_text(img, row1, position=(310,630), textsize=35)
        add_text(img, row2, position=(770,630), textsize=35)
        add_text(img, self.year, position=(355,443), textsize=40)
        add_text(img, self.month, position=(565,443), textsize=40)
        add_text(img, self.constellation, position=(710,443), textsize=40)
        if len(clanname) <= 7:
            add_text(img, clanname, position=(300+(7-len(clanname))/2*40, 515), textsize=40)
        else:
            add_text(img, clanname, position=(300+(10-len(clanname))/2*30, 520), textsize=30)
        add_text(img, nickname, position=(300,361), textsize=39)
        #输出
        buf = BytesIO()
        img.save(buf,format='JPEG')
        base64_str = f'base64://{base64.b64encode(buf.getvalue()).decode()}'
        await self.api.send_msg(group_id=gid, message=f'[CQ:image,file={base64_str}]')

font_path = os.path.join(os.path.dirname(__file__), 'TXQYW3.ttf')
def add_text(img: Image,text:str,textsize:int,font=font_path,textfill='black',position:tuple=(0,0)):
    #textsize 文字大小
    #font 字体，默认微软雅黑
    #textfill 文字颜色，默认黑色
    #position 文字偏移（0,0）位置，图片左上角为起点
    img_font = ImageFont.truetype(font=font,size=textsize)
    draw = ImageDraw.Draw(img)
    draw.text(xy=position,text=text,font=img_font,fill=textfill)
    return img

def get_apikey(gid: int) -> str:

    #请指定下一行代码中yobot的数据库绝对路径
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),'yobot_data','yobotdata.db')
    #例：db_path = 'C:/Users/Administrator/Desktop/yobot/yobot/src/client/yobot_data/yobotdata.db'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(f'select apikey from clan_group where group_id={gid}')
    apikey = cur.fetchall()[0][0]
    cur.close()
    conn.close()
    return apikey 




    
