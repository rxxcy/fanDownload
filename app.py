# -*- coding:utf-8 -*-
#  anime1 番剧下载器

import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote
import re
import os

def main():
    key = input('关键字：')
    while key == '':
        key = input('请输入关键字!!!')
        # key = '無職轉生'
    anime = handleSearch(key)
    cmd = None
    while not cmd:
        cmd = handleSelectDownload(key, anime)
    pass

def handleSelectDownload(key, anime):
    print(f'「\033[35m{key}\033[0m」的搜尋結果')
    for index, item in enumerate(anime):
        print(f'\033[31m{index}\033[0m. {item["title"]}')
    index = input('输入索引(默认 all)：')
    if index == '' or index == 'all':
        print('\033[41m下载全部\033[0m')
        for item in anime:
            handleGetDownloadUrl(item)
        print('\033[41m全部下载完成\033[0m')
    else:
        index = int(index)
        if index > len(anime) or index < 0:
            print('\033[41m煞笔\033[0m')
            return None
        else:
            print('\033[41m下载单集\033[0m')
            handleGetDownloadUrl(anime[index])
            return None
    return True

def handleSearch(key=None):
    print('正在搜索...')
    url = 'https://anime1.me/?s='
    res = requests.get(f"{url}{key}")
    html = res.text
    soup = BeautifulSoup(html, 'html.parser')
    anime = []
    temp = handGetAnimeList(key, soup)
    page = soup.find(attrs={'class': 'nav-previous'})
    if page is None :
        temp = temp[0: -2]
    anime.extend(temp)
    while page:
        href = page.find('a').attrs['href']
        res = requests.get(href)
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
        print(f'关于 「\033[35m{key}\033[0m」 未找到任何内容 0x0')
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
        print(f'关于 「\033[35m{key}\033[0m」 未找到任何内容 0x1')
        exit(0)
    return animeList

def handleGetPlayUrl(item):
    res = requests.get(item['url'])
    html = res.text
    soup = BeautifulSoup(html, 'html.parser')
    video = soup.find('button', attrs={'class': 'loadvideo'}).attrs['data-src']
    if video is None:
        print(f' {item.title} 未查询到下载地址')
        return False
    return video

def handleGetDownloadUrl(item):
    print(f'获取 \033[35m{item["title"]}\033[0m 真实下载地址')
    video = handleGetPlayUrl(item)
    if not video:
        return video
    getDownloadUrl(video, item['title'])
    return True

def getDownloadUrl(url, title):
    html = requests.get(url).text
    data = re.findall(r'x\.send\(\'d=(.+)\'\)', html)
    if len(data) <= 0:
        print('未找到')
        return None
    api = 'https://v.anime1.me/api'
    data = unquote(data[0], 'utf-8')
    res = requests.post(api, data={'d': data})
    headers = res.headers
    res = res.json()['l']
    cookie = headers['Set-Cookie']
    handleDownload(f'https:{res}', title, cookie)


def handleDownload(src, title,cookie):
    print('下载中...')
    temp = re.sub(r'\[\d+\]', '', title).strip()
    path = f'video/{temp}'
    if not os.path.exists(path):
        os.mkdir(path)
    bin = requests.get(url=src, stream=True, headers={
        "cookie": cookie,
        "referer": "https://v.anime1.me/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36"
    })
    with open(f'{path}/{title}.mp4', 'wb') as f:
        f.write(bin.content)
    print(f'{title} 下载完成')

if __name__ == '__main__':
    main()
