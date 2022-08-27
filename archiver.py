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


header = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1',
    'Referer': 'https://www.bilibili.com'
}
s = requests.session()


def download(vid):
    video_name = vid['data']['title']
    print("\n"+video_name)

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
                +'&cid='+str(video)+'&qn=80&otype=json',headers=header).text
        )
        video_url = video_info['data']['durl'][0]['url']
        print("\nP%d 开始下载"%(page+1))

        with closing(s.get(video_url,headers=header,stream=True)) as response:
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
                        print("视频下载进度：%d%% (%d/%d)" % (now_jd, data_count, content_size))
                        prev_jd = now_jd

            print('\n下载成功！开始转换')
            os.system("ffmpeg -hide_banner -loglevel quiet -i "+flv_path+
                      " -c copy "+os.path.join(video_path,'P%d.mp4'%(page+1)))
            print('转换完成，删除源文件')
            os.remove(flv_path)


if __name__ == "__main__":
    with open(os.getenv("GITHUB_EVENT_PATH","event.json")) as f:
        issue = json.load(f)['issue']
    text = issue['body'].replace('\r','').replace('\n\n','\n').strip()
    url = text.split('\n')[1].strip()
    print(url)
##    url = input("""\n请粘贴哔哩哔哩视频链接\n""")
    if 'https://b23.tv' in url:
        loc = s.get(url,allow_redirects=False)
        url = loc.headers['location']
    if 'video/av' in url:
        av = json.loads(s.get(
                'https://api.bilibili.com/x/web-interface/archive/stat?aid='
                +url,headers=header).text)
        url = av['data']['bvid']

    video_id = re.findall("[\w.]*[\w:\-\+\%]",url)[3]
    vid = json.loads(s.get(
            'https://api.bilibili.com/x/web-interface/view?bvid='+video_id,
            headers=header).text)

    download(vid)
