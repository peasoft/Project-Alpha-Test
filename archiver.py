#/usr/bin/python3
# Fork from https://github.com/5ime/bilidown
# Mod by peasoft
import re
import requests
import json
from contextlib import closing
import os
import shutil
import sys
import random
import time


header = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1',
    'Referer': 'https://www.bilibili.com'
}
s = requests.session()


def get_proxies():
    res = requests.get("https://free.kuaidaili.com/free/inha/")
    text = res.text
    text = text.split("<tbody>")[1].split("</tbody>")[0]

    text = text.split('\n')
    ips = []
    ports = []
    for l in text:
        if "IP" in l:
            ips.append(l.lstrip().lstrip('<td data-title="IP">').rstrip('</td>'))
        elif "PORT" in l:
            ports.append(l.lstrip().lstrip('<td data-title="PORT">').rstrip('</td>'))

    proxies = []
    for ip, port in zip(ips, ports):
        proxies.append(ip+':'+port)
        try:
            res = requests.get("https://www.bilibili.com/",headers=header,proxies={'http':proxies[-1],'https':proxies[-1]})
        except:
            del proxies[-1]
        else:
            if res.status_code != 200:
                del proxies[-1]
        time.sleep(1)

    if len(proxies) == 0:
        raise Exception("no proxy")
    return proxies

def download(vid):
    video_name = vid['data']['title']
    print("\n"+video_name,flush=True)

    video_path = os.path.join('%s_%d'%(vid['data']['owner']['name'],
            vid['data']['owner']['mid']),video_id+'_'+video_name)

    if os.path.exists(video_path):
        shutil.rmtree(video_path)
    os.makedirs(video_path)

    with open(os.path.join(video_path,"desc.txt"),'w') as f:
        f.write(vid['data']['desc'])

    with open(os.path.join(video_path,"cover.jpg"),'wb') as f:
        f.write(s.get(vid['data']['pic']).content)

    for page in range(vid['data']['videos']):
        video = vid['data']['pages'][page]['cid']
        video_info = json.loads(s.get(
                'https://api.bilibili.com/x/player/playurl?bvid='+video_id
                +'&cid='+str(video)+'&qn=80&otype=json',headers=header,proxies=proxies).text
        )
##        print(video_info)
        video_url = video_info['data']['durl'][0]['url']
        print("\nP%d 开始下载"%(page+1),flush=True)

        with closing(s.get(video_url,headers=header,stream=True,proxies=proxies)) as response:
            chunk_size = 1024*16  # 单次请求最大值
            content_size = int(response.headers['content-length'])  # 内容体总大小
            data_count = 0
            prev_jd = -1
            flv_path = os.path.join(video_path,'P%d.flv'%(page+1))
            with open(flv_path,'wb') as file:
                for data in response.iter_content(chunk_size=chunk_size):
                    file.write(data)
                    data_count = data_count + len(data)
                    now_jd = int((data_count / content_size) * 100)
                    if now_jd % 10 == 0 and now_jd != prev_jd:
                        print("视频下载进度：%d%% (%d/%d)" % (now_jd, data_count, content_size),flush=True)
                        prev_jd = now_jd

            print('\n下载成功！开始转换',flush=True)
            os.system("ffmpeg -hide_banner -loglevel quiet -i "+flv_path+
                      " -c copy "+os.path.join(video_path,'P%d.mp4'%(page+1)))
            print('转换完成，删除源文件',flush=True)
            os.remove(flv_path)


if __name__ == "__main__":
    event_file = os.getenv("GITHUB_EVENT_PATH")
    if event_file:
        with open(event_file) as f:
            issue = json.load(f)['issue']
        text = issue['body'].replace('\r','').replace('\n\n','\n').strip()
        url = text.split('\n')[1].strip()
        print("寻找代理",flush=True)
        proxy = get_proxies()[0]
        proxies = {
            'http': proxy,
            'https': proxy
        }
    else:
        proxies = {}
        url = input("""\n请粘贴哔哩哔哩视频链接\n""")
    if 'https://b23.tv' in url:
        loc = s.get(url,allow_redirects=False)
        url = loc.headers['location']
    if 'video/av' in url:
        av = json.loads(s.get(
                'https://api.bilibili.com/x/web-interface/archive/stat?aid='
                +url,headers=header,proxies=proxies).text)
        url = av['data']['bvid']

    video_id = re.findall("[\w.]*[\w:\-\+\%]",url)[3]
    vid = json.loads(s.get(
            'https://api.bilibili.com/x/web-interface/view?bvid='+video_id,
            headers=header,proxies=proxies).text)

    download(vid)
