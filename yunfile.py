import re
import requests
import pytesseract
import time
import cgi
import os
import logging
from PIL import Image
from bs4 import BeautifulSoup

from pyquery import PyQuery as pq
#日志配置
logging.basicConfig(level=logging.DEBUG,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                datefmt='%a, %d %b %Y %H:%M:%S',
                filename='yunfile_download.log',
                filemode='w')

headers = {"User-Agent": #,
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
           "Accept-Language": "zh-CN,zh;q=0.9",
           }

header_bisi ={
    "Cookie":#				添加cookie
    "User-Agent": #			添加user-agent
}

num = 1

# 二值化,即超过下面这个值的像素点二值为黑否则为白
threshold = 100
table = []
for i in range(256):
    if i < threshold:
        table.append(0)
    else:
        table.append(1)

    # 由于都是数字
# 对于识别成字母的 采用该表进行修正
rep = {'O': '0',
       'I': '1',
       'L': '1',
       'Z': '2',
       'S': '8',
       '$': '6'
       }


def get_info(url):
    html = requests.get(url, headers=headers, verify=False)
    print(html.text)

def get_verify_code(url):                   #url为初进网盘地址
    image_name = 'picture.jpg'

    try:
        r = session.get(url, headers = headers)

        with open(image_name, 'wb') as file:
            file.write(r.content)

        #打开图片
        image = Image.open('picture.jpg')

        #转化到灰度图
        imgry = image.convert('L')

        #保存图像
        imgry.save('g'+image_name)

        #二值化，采用阈值分割法，threshold为分割点
        out = imgry.point(table, '1')
        out.save('b'+image_name)

        #识别
        text = pytesseract.image_to_string(out)

        #对识别后的验证码人为处理
        text = text.strip()
        text = text.upper();
        for r in rep:
            text = text.replace(r, rep[r])
        #将非数字的字符进行替换
        text = re.sub("[^0-9]", "", text)

        if(len(text)!= 4):                  #if num is not equal 4, then it must be wrong and get verify code again
            text = get_verify_code(url)
        print(text)
        return text
    except BaseException as ex:
        logging.debug("get error,try again")
        tmp_text = get_verify_code(url)
        return tmp_text

def build_info(data):
    try:
        info = {}
        d = pq(data)
        action = d("form").filter(".tform")
        d = pq(action)
        for doc in d("input"):
            x = pq(doc)
            key = x.attr("name")
            if key:
                value = x.attr("value")
                info[key] = value

        # 下面两个变量在js脚本里藏着
        print(info)
        info['vid'] = re.search(r'var vericode = "(\w+)"', data).group(1)       #group(1)返回正则中第一个括号匹配部分
        info['fileId'] = re.search(r'fileId.value = "(\w+)";', data).group(1)
        print("vid="+info['vid'])
        print("fileId=" + info['fileId'])
        url_1 = re.search(r'saveCdnUrl="(\S+)";', data).group(1)

        url_2 = re.search(r'= saveCdnUrl\+"(\S+)";', data).group(1)         #这里的正则中+号用\注释才表示是个字符
        print("url_1="+url_1)
        print("url_2=" + url_2)

        finall_url = url_1 +url_2

        logging.warning(finall_url)

        r = session.post(finall_url , data= info, stream = True ,headers =headers )     #stream为true不会立刻下载，使用iter_content遍历内容或访问属性时才开始下载

        logging.info("post请求返回")
        print(r.headers)
        global num

        a , v =cgi.parse_header(r.headers['Content-Disposition'])       #cgi模块用来解析返回的post头部
        print(a)
        print(v)
        file_name = v["filename"]
        print(file_name)

        #file_name = str(num)

        logging.warning(file_name)
        path = r"wo\\"+ file_name
        def verfy_exist_name(path):
            if os.path.exists(path):                    #if exits ,then return
                print("filename already exist ")
                logging.info("filename already exist ")
                return 0
            else:
                return 1
        while not(verfy_exist_name(path)):
            num = num +1
            path = "wo\\" + str(num) +".zip"
        f = open(path, "wb")
        for chunk in r.iter_content(1024):
            if chunk:
                f.write(chunk)
        num += 1
        logging.info(file_name+"下载完成")

    except BaseException as ex :
        print("some Exception occur {0},parse picture again".format(ex))
        logging.warning("Exception is {0}".format(ex))
        return None

    print("返回1")
    return 1


def get_new_url(verify_code, url ,origin_url):

    header_temp = headers
    header_temp["Referer"] = origin_url

    #组装最后的url
    a = url[0:str(url).rfind(r".") ]        #左闭右开的截断
    new_url = url[0:str(url).rfind(r".")] + ( "/" +str(verify_code) ) +url[str(url).rfind(r"."):]
    print(new_url)
    time.sleep(30)                          #这个很重要，应该是网站服务器那边会判断时间
    try:
        response = session.get(new_url, headers = header_temp)
    except BaseException as ex:
        logging.debug("get error,try again")
        get_new_url(verify_code, url , origin_url)

    '''print(response.status_code)  # 打印状态码
    print(response.url)  # 打印请求url
    print(response.headers)  # 打印头信息
    print(response.cookies)  # 打印cookie信息
    print(response.text)  # 以文本形式打印网页源码
    print(response.content)  # 以字节流形式打印
    '''

    ret = build_info(response.text)
    return ret

def parse_raw_bisi(url):

    list = []
    r = session.get(url, headers = header_bisi)

    d = pq(r.text)
    d = d("div").filter("#postlist")
    d = d("div")

    for tr in d.items():
        tr = tr("td").filter(".t_f")
        tr = tr("a")
        for doc in tr.items():
            ret = doc.attr("href")
            if ret.find("hkbbcc") != -1:
                continue
            if ret.find("forum.php?mod=attachment") != -1:
                continue
            print(ret)
            list.append(ret)

    if list != None:
        return list

def factory(list , beg_num):
    i = 0
    for item in list:

        if i < beg_num - 1:
            i = i + 1
            continue

        #time.sleep(60)
        global session
        session = requests.Session()

        r = session.get(item, headers=headers, allow_redirects=False)
        if r.status_code == 302:
            #获取验证码网站
            real_url = r.headers["Location"]
            forward_url = real_url[0:real_url.find("/", 10)]
            verfy_code_url = forward_url + "/verifyimg/getPcv.html"
            while (1):
                ret = session.get(real_url, headers=headers, allow_redirects=False)     # 获取数字整齐的网站url

                verfy_num = get_verify_code(verfy_code_url)

                if ret.status_code == 200:
                    url_last = re.search(r'var url = "(\S+)"', ret.text).group(1)
                    download_url = forward_url+ url_last
                    l = get_new_url(verfy_num , download_url ,real_url)
                    if l == None:
                        continue
                    else:
                        break

if __name__ == "__main__":
    start = time.time()
    global session
    session = requests.Session()  # 可以记录所有请求的cookie

    list = parse_raw_bisi("http://hkbbcc.xyz/")		#添加爬取的url

    beg_num = 0
    factory(list , beg_num)



