from nonebot import get_driver

from .config import Config

from nonebot import on_command
from nonebot.permission import SUPERUSER
from nonebot.log import logger

import aiohttp
import aiofiles
import re
import zipfile
import shutil
import yaml
import sqlite3
import os

global_config = get_driver().config
config = Config.parse_obj(global_config)

root = global_config.ROOT
db = global_config.DB
cur = global_config.CUR

matcher = on_command("更新", permission=SUPERUSER)


@matcher.handle()
async def handle():
    await matcher.send("数据库开始更新")
    async with aiohttp.ClientSession() as session:
        html = await session.get("https://developers.eveonline.com/resource")
        html = await html.text()
        link = re.findall(r'<a href="(.*?)">sde-TRANQUILITY.zip</a>', html)[0]
        logger.info(f"下载链接解析完成：{link}")
        content = await session.get(link)
        async with aiofiles.open(f"{root}/sde.zip", "wb") as file:
            await file.write(await content.content.read())
    logger.info("文件下载完成")

    file = zipfile.ZipFile(f"{root}/sde.zip")
    file.extractall(root)

    logger.info("文件解压完成")

    shutil.copy(f"{root}/sde/fsd/typeIDs.yaml", f"{root}/")

    file = open(f"{root}/typeIDs.yaml", "r", encoding="utf-8").read()
    data = yaml.load(file, Loader=yaml.FullLoader)

    items = data.keys()

    logger.info("文件读取完成")

    try:
        cur.execute("create table item(name TEXT,id TEXT,description TEXT,ename TEXT);")
    except sqlite3.OperationalError:
        logger.info("数据表已存在")

    cur.execute("delete from item")
    logger.info("旧数据已删除")

    for i in items:
        try:
            name_zh = data[i]["name"]["zh"]
            name_en = data[i]["name"]["en"]
        except KeyError:
            name_zh = data[i]["name"]["en"]
            name_en = "此物品暂无官方中文名"
        try:
            description = data[i]["description"]["zh"].replace("\n", "").replace(" ", "")
            description = re.sub(r"<.*?>", "", description)
        except KeyError:
            description = "无描述"

        cur.execute('INSERT INTO item VALUES(?, ?, ?, ?);', (name_zh, str(i), description, name_en))

    db.commit()

    logger.info("数据库写入完成")

    shutil.rmtree(f"{root}/sde")
    os.remove(f"{root}/sde.zip")
    os.remove(f"{root}/typeIDs.yaml")

    await matcher.finish("数据库更新完成")
