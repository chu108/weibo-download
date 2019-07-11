# -*- coding: utf-8 -*-
from __future__ import print_function
import urllib
from gen_cookies import get_cookies
import datetime
import requests
import wget
from wget import bar_adaptive
import threadpool
import re
import os
import time
import io
import json
import hashlib
from bs4 import BeautifulSoup
import random

dir="ycy"
url_page="https://weibo.com/u/6409273841?profile_ftype=1&page={}&is_all=1"
url_ajax= "https://weibo.com/p/aj/v6/mblog/mbloglist?ajwvr=6&domain=100505&profile_ftype=1&is_all=1&pagebar={}&id=1005056409273841&feed_type=0&page={}&pre_page={}&__rnd={}"
session=requests.session()
origin = 'http'
protocol = 'https'
root_url = 'weibo.com'
ext_group=["jpg","png","gif","jpeg","bmp"]
page_now=1
reserved={}
paths={}
download_videos=True

def fack_ua():
    first_num = random.randint(55, 64)
    third_num = random.randint(0, 3240)
    fourth_num = random.randint(0, 140)
    chrome_version = 'Chrome/{}.0.{}.{}'.format(first_num, third_num, fourth_num)
    return "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) {} Safari/537.36 Core/1.63.6788.400 QQBrowser/10.3.2864.400".format(chrome_version)

def get_time():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def get_page(page):
    global page_now
    page_now=page
    cookies=get_cookies()
    url=url_page.format(page)
    headers = {
        "User-Agent": fack_ua(),
        "Cookie": "SUBP={}; SUB={}; ".format(cookies['SUBP'],cookies['SUB']),
        'Accept-Encoding': 'gzip, deflate, sdch',
        'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Connection': 'keep-alive'
    }
    count=0
    while True:
        try:
            result = requests.get(url, headers=headers,timeout=8)
            break
        except:
            count+=1
            if count>=2:
                print(page)
                exit(-1)
            continue
    print("{}-1".format(page))
    html=result.text
    parser_page(html)
    for i in range(2):
        print("{}-{}".format(page,i+2))
        url=url_ajax.format(i, page, page, int(time.time() * 1000))
        headers["User-Agent"]=fack_ua()
        count = 0
        while True:
            try:
                result = requests.get(url, headers=headers,timeout=8)
                html = result.json()["data"]
                break
            except:
                count += 1
                if count >= 2:
                    print(page)
                    exit(-1)
                continue
        parser_html(html)

def url_filter(url):
    return ':'.join([protocol, url]) if protocol not in url and origin not in url else url

def parser_html(html):
    global result,reserved
    set_id=set([item["id"] for item in result])
    soup = BeautifulSoup(html, "html.parser")
    items = soup.find_all(attrs={"action-type": "feed_list_item"})
    for item in items:
        data = {}
        item_from = item.find("div", attrs={"class": "WB_from S_txt2"})
        if item_from == None:
            item_from = get_time()
        else:
            item_from = item_from.text
        text = item.find("div", attrs={"class": "WB_text W_f14"})
        if text != None:
            item_a = text.find_all("a")
            for each_item_a in item_a:
                each_item_a.extract()
            text = text.text.strip("\n").strip()
            id = text + item_from
            id = hashlib.md5(id.encode("utf-8")).hexdigest()
        else:
            text = ''
            id = item_from
            id = hashlib.md5(id.encode("utf-8")).hexdigest()
        try:
            imgs = str(item.find(attrs={'node-type': 'feed_content'}).find(
                attrs={'node-type': 'feed_list_media_prev'}).find_all('img'))
            imgs = map(url_filter, re.findall(r"src=\"(.+?)\"", imgs))
            imgs = [img.replace("thumb150", "large") for img in imgs]
        except:
            imgs = []
        if download_videos:
            try:
                li = str(item.find(attrs={'node-type': 'feed_content'}).find(
                    attrs={'node-type': 'feed_list_media_prev'}).find_all('li'))
                videos = re.findall(r"video_src=(.+?)&amp;", li)
                videos = [url_filter(urllib.unquote(video.replace("is_https%3D1",""))) for video in videos]
                vidoes_hidden = re.findall(r"gif_ourl=(.+?)&", li)
                vidoes_hidden = [url_filter(urllib.unquote(video)) for video in vidoes_hidden]
                videos += vidoes_hidden
            except:
                videos = []
            videos_done = []
            for video in videos:
                count = 0
                while True:
                    try:
                        print(video)
                        title = text
                        if title == '':
                            title = u"未命名"
                        else:
                            title = validate(title)
                        if title in reserved:
                            reserved[title] += 1
                            filename = u"{}-{}.mp4".format(title, reserved[title])
                        else:
                            reserved[title] = 1
                            filename = u"{}.mp4".format(title)
                        # filename = hashlib.md5(get_time() + str(random.randint(0, 9999))).hexdigest() + ".mp4"
                        if os.path.exists(os.path.join(dir, "attachments", filename)):
                            continue
                        wget.download(video, os.path.join(dir, "attachments", filename), bar=bar_adaptive)
                        videos_done.append(filename)
                        break
                    except:
                        count += 1
                        if count >= 4:
                            print(page_now)
                            exit(-1)
                        continue
            data["videos"] = videos_done
        data["id"] = id
        data["text"] = text
        data["images"] = imgs
        if not id in set_id:
            result.append(data)
    dump_json()
    return len(items)

def parser_page(html):
    scripts=re.findall("(?<=<script>FM.view\().+?(?=\)</script>)",html)
    for script in scripts:
        script=json.loads(script)
        if script["ns"]=="pl.content.homeFeed.index":
            html=script["html"]
            count=parser_html(html)
            if count>0:
                break

def dump_json():
    text = json.dumps(result, ensure_ascii=False, indent=4)
    if type(text)==str:
        text=text.decode("utf-8")
    with io.open(os.path.join(dir, "result.json"), "w", encoding="utf-8") as fd:
        fd.write(text)
    text = json.dumps(record, ensure_ascii=False, indent=4)
    if type(text)==str:
        text=text.decode("utf-8")
    with io.open(os.path.join(dir, "record.json"), "w", encoding="utf-8") as fd:
        fd.write(text)
    text = json.dumps(crawlered, ensure_ascii=False, indent=4)
    if type(text)==str:
        text=text.decode("utf-8")
    with io.open(os.path.join(dir, "crawlered.json"), "w", encoding="utf-8") as fd:
        fd.write(text)
    text = json.dumps(downloaded, ensure_ascii=False, indent=4)
    if type(text)==str:
        text=text.decode("utf-8")
    with io.open(os.path.join(dir, "downloaded.json"), "w", encoding="utf-8") as fd:
        fd.write(text)

def compact():
    set_result=set()
    result_compact=[]
    for item in result:
        id=item["id"]
        if not id in set_result:
            set_result.add(id)
            result_compact.append(item)
    text = json.dumps(result_compact, ensure_ascii=False, indent=4)
    if type(text)==str:
        text=text.decode("utf-8")
    with io.open(os.path.join(dir, "result_compact.json"), "w", encoding="utf-8") as fd:
        fd.write(text)

def remove():
    set_videos=set()
    for item in result:
        videos=item["videos"]
        for video in videos:
            set_videos.add(video)
    for filename in os.listdir(os.path.join(dir,"attachments")):
        if not filename.decode("utf-8") in set_videos:
            print(filename)
            os.remove(os.path.join(dir,"attachments",filename))

def validate(title):
    rstr = r"[\.\/\\\:\*\?\"\<\>\|]"
    new_title = re.sub(rstr, "_", title)
    return new_title

def rename():
    reserved={}
    for item in result:
        videos=item["videos"]
        title=item["text"]
        for video in videos:
            if not os.path.exists(os.path.join(dir,"attachments",video)):
                continue
            if title=='':
                title=u"未命名"
            else:
                title=validate(title)
            if title in reserved:
                reserved[title]+=1
                filename = u"{}-{}.mp4".format(title, reserved[title])
            else:
                reserved[title]=1
                filename = u"{}.mp4".format(title)
            os.rename(os.path.join(dir,"attachments",video),os.path.join(dir,"attachments",filename))

def get_images(index):
    global paths
    item=result[index]
    print(index)
    title=item["text"]
    title = validate(title)
    images=item["images"]
    path=os.path.join(dir,"images",title)
    if title in paths:
        count=paths[title]
        paths[title]=count+1
        path = u"{}-{}".format(path, count)
    else:
        paths[title]=1
    if not os.path.exists(path):
        os.mkdir(path)
    for image in images:
        index=images.index(image)+1
        exts=re.findall("(?<=\.)[a-z]{3,4}",image)
        ext="jpg"
        for ext_name in exts:
            if ext_name in ext_group:
                ext=ext_name
                break
        path_image=os.path.join(path,"{}.{}".format(index,ext))
        if os.path.exists(path_image):
            continue
        else:
            path_image_jpg=os.path.join(path,"{}.jpg".format(index))
            if os.path.exists(path_image_jpg):
                os.remove(path_image_jpg)
        while True:
            try:
                response=requests.get(image,timeout=10)
            except:
                continue
            if response.status_code!=200:
                continue
            with open(path_image,"wb") as fd:
                fd.write(response.content)
            break

def get_images_by_threadpool():
    queue=[i for i in range(len(result))]
    pool = threadpool.ThreadPool(64)
    request = threadpool.makeRequests(get_images, queue)
    [pool.putRequest(req) for req in request]
    pool.wait()

def init():
    global result,crawlered,downloaded,record
    if not os.path.exists(dir):
        os.mkdir(dir)
    if not os.path.exists(os.path.join(dir,"attachments")):
        os.mkdir(os.path.join(dir,"attachments"))
    if not os.path.exists(os.path.join(dir,"images")):
        os.mkdir(os.path.join(dir,"images"))
    if not os.path.exists(os.path.join(dir,"backup")):
        os.mkdir(os.path.join(dir,"backup"))
    if os.path.exists(os.path.join(dir,"result.json")):
        result=json.loads(io.open(os.path.join(dir,"result.json"),encoding="utf-8").read())
    else:
        result=[]
    print(len(result))
    if os.path.exists(os.path.join(dir,"record.json")):
        record=json.loads(io.open(os.path.join(dir,"record.json"),encoding="utf-8").read())
    else:
        record=[]
    if os.path.exists(os.path.join(dir,"crawlered.json")):
        crawlered=json.loads(io.open(os.path.join(dir,"crawlered.json"),encoding="utf-8").read())
    else:
        crawlered=[]
    if os.path.exists(os.path.join(dir,"downloaded.json")):
        downloaded=json.loads(io.open(os.path.join(dir,"downloaded.json"),encoding="utf-8").read())
    else:
        downloaded=[]

def main():
    global cookies,headers
    init()
    for i in range(1,262):
        get_page(i)
    get_images_by_threadpool()
    # compact()
    # remove()
    # rename()

if __name__=="__main__":
    main()