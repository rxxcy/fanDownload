# -*- coding:utf-8 -*-
#  anime1 番剧下载器

import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote
import re
import os
import time


def main():
    key = input('关键字：')
    while key == '':
        key = input('请输入关键字!!!')
        # key = '鬼滅之刃 刀匠村篇'
    anime = handleSearch(key)
    cmd = None
    while not cmd:
        cmd = handleSelectDownload(key, anime)
    pass


def handleSelectDownload(key, anime):
    print(f'「{key}」的搜尋結果')
    for index, item in enumerate(anime):
        print(f'{index}. {item["title"]}')
    index = input('输入索引(默认 all)：')
    if index == '' or index == 'all':
        print('下载全部')
        for item in anime:
            handleGetDownloadUrl(item)
        print('全部下载完成')
    else:
        index = int(index)
        if index > len(anime) or index < 0:
            print('煞笔')
            return None
        else:
            print('下载单集')
            handleGetDownloadUrl(anime[index])
            return None
    return True


def handleSearch(key=None):
    print('正在搜索...')
    url = 'https://anime1.me/?s='
    res = requests.get(url=f"{url}{key}", proxies=proxies)
    html = res.text
    soup = BeautifulSoup(html, 'html.parser')
    anime = []
    temp = handGetAnimeList(key, soup)
    page = soup.find(attrs={'class': 'nav-previous'})
    if page is None:
        temp = temp[0: -2]
    anime.extend(temp)
    while page:
        href = page.find('a').attrs['href']
        res = requests.get(url=href, proxies=proxies)
        html = res.text
        soup = BeautifulSoup(html, 'html.parser')
        temp = handGetAnimeList(key, soup)
        page = soup.find(attrs={'class': 'nav-previous'})
        if page is None:
            temp = temp[0: -3]
            # anime.extend(temp)
        anime.extend(temp)
    return anime


def handGetAnimeList(key, soup):
    lists = soup.find(id='content').find_all('article')
    if lists is None:
        print(f'关于 「{key}」 未找到任何内容 0x0')
        exit(0)
    animeList = []
    for item in lists:
        header = item.find('header')
        h2 = header.find('h2')
        a = h2.find('a')
        if a.text is not None and a.attrs['href'] is not None:
            temp = {
                'title': a.text,
                'url': a.attrs['href']
            }
            animeList.append(temp)

    length = len(animeList)
    if length <= 0:
        print(f'关于 「{key}」 未找到任何内容 0x1')
        exit(0)
    return animeList


def handleGetPlayUrl(item):
    res = requests.get(url=item['url'], proxies=proxies)
    html = res.text
    soup = BeautifulSoup(html, 'html.parser')
    video = soup.find('video', attrs={'data-apireq': True}).attrs['data-apireq']
    if video is None:
        print(f' {item.title} 未查询到下载地址')
        return False
    return unquote(video)


def handleGetDownloadUrl(item):
    print(f'获取 {item["title"]} 真实下载地址')
    video = handleGetPlayUrl(item)
    if not video:
        return video
    getDownloadUrl(video, item['title'])
    return True


def getDownloadUrl(params, title):
    api = 'https://v.anime1.me/api'
    res = requests.post(api, data={'d': params}, proxies=proxies)
    headers = res.headers
    temp = res.json()['s'][0]['src']
    cookie = headers['Set-Cookie']
    handleDownload(f'https:{temp}', title, cookie)


def handleDownload(src, title, cookie):
    if not os.path.exists('video'):
        os.mkdir('video')
    print('下载中...')
    temp = re.sub(r'\[\d+\]', '', title).strip()
    path = f'video/{temp}'
    if not os.path.exists(path):
        os.mkdir(path)
    resp = requests.get(url=src, stream=True, headers={
        "cookie": cookie,
        "referer": "https://v.anime1.me/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/95.0.4638.69 Safari/537.36"
    }, proxies=proxies)

    total_length = resp.headers.get('content-length')
    file_path = f'{path}/{temp}.mp4'

    if total_length is None:  # 没有内容长度信息，无法显示进度
        with open(file_path, 'wb') as f:
            f.write(resp.content)
    else:
        # 初始化下载进度和文件总大小
        dl = 0
        total_length = int(total_length)
        start = time.time()  # 开始下载的时间
        with open(file_path, 'wb') as f:
            for data in resp.iter_content(chunk_size=4096):
                now = time.time()  # 当前时间
                dl += len(data)
                f.write(data)
                done = int(50 * dl / total_length)
                percent_done = int(100 * dl / total_length)
                downloaded = dl / 1024 / 1024
                total = total_length / 1024 / 1024
                speed = downloaded / (now - start)
                print(
                    f"\r[{'#' * done}{' ' * (50 - done)}] {percent_done}% ({downloaded:.2f}Mb/{total:.2f}Mb) {speed:.2f}Mb/s",
                    end='')
    print(f'{title} 下载完成')


proxies = {'http': 'http://127.0.0.1:11223', 'https': 'http://127.0.0.1:11223'}

if __name__ == '__main__':
    main()
