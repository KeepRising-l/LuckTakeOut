"""抓取自由许可的菜品/门店图片，用于演示数据。

数据源（均为自由许可或明确允许再利用）：
  1. Wikimedia Commons —— 按关键词检索，过滤 JPEG/PNG，记录许可信息
  2. TheMealDB —— Commons 无结果时的兜底（开发用免费 API）

用法：
    cd takeout && .venv/Scripts/python.exe scripts/fetch_food_images.py

产物：
    media/products/<shop>/<name>.<ext>   图片文件（已存在则跳过）
    media/products/sources.json          来源与许可清单
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA_DIR = os.path.join(BASE_DIR, 'media', 'products')
SOURCES_FILE = os.path.join(MEDIA_DIR, 'sources.json')
UA = 'LuckTakeOut-Demo/1.0 (educational course project; contact: local)'
TIMEOUT = 25

# 菜品图排除词：命中这些词的通常是门面/菜单/环境照，不适合当菜品图
SHOP_WORDS = ('bakery', 'shop', 'store', 'restaurant', 'interior', 'counter',
              'sign', 'menu', 'cafe', 'storefront', 'front')

# 检索容易跑偏的条目：直接锁定 Commons 上的具体文件
PINNED = {
    'sichuan/chili_pork': 'File:Hunan cuisine, fried pork with pepper.jpg',
    'sichuan/shuizhu_pork': 'File:Shuizhu Roupian at Daqian Restaurant, Dachenglu (20260126131330).jpg',
    'milktea/bubble_tea': 'File:Classic bubble tea.jpg',
    'noodle/beef_noodle': 'File:Beef noodle soup at Western Mahua, Sanlihe (20220224174228).jpg',
    'noodle/lanzhou_noodle': 'File:Beef noodle soup(Lanzhou).jpg',
    'fastfood/cola': 'File:Tumbler of cola with ice.jpg',
    'sushi/california_roll': 'File:California Rolls.JPG',
    'sushi/miso_soup': 'File:A bowl of miso soup.jpg',
}

# shop -> {logo: 查询词, items: {文件名: 查询词}}
MANIFEST = {
    'sichuan': {
        'logo': 'sichuan restaurant',
        'items': {
            'mapo_tofu': 'mapo tofu',
            'shuizhu_pork': 'sichuan boiled pork',
            'kung_pao': 'kung pao chicken',
            'duojiao_fish': 'steamed fish head chili',
            'chili_pork': 'stir fried pork chili',
        },
    },
    'coffee': {
        'logo': 'coffee shop interior',
        'items': {
            'latte': 'latte art coffee cup',
            'americano': 'americano coffee',
            'cappuccino': 'cappuccino coffee',
            'croissant': 'croissants pastry',
            'tiramisu': 'tiramisu dessert',
        },
    },
    'milktea': {
        'logo': 'bubble tea shop',
        'items': {
            'bubble_tea': 'bubble tea',
            'mango_sago': 'mango sago dessert',
            'lemon_tea': 'iced lemon tea',
            'matcha_latte': 'matcha latte',
            'cheese_foam_tea': 'milk tea cup',
        },
    },
    'noodle': {
        'logo': 'noodle restaurant',
        'items': {
            'beef_noodle': 'beef noodle soup',
            'lanzhou_noodle': 'lanzhou beef noodles',
            'zhajiang_noodle': 'zhajiangmian noodles',
            'wonton_noodle': 'wonton noodle soup',
            'spicy_noodle': 'spicy noodles sichuan',
        },
    },
    'fastfood': {
        'logo': 'fast food restaurant counter',
        'items': {
            'chicken_burger': 'chicken burger',
            'fries': 'french fries',
            'fried_chicken': 'fried chicken',
            'cola': 'cola glass drink',
            'popcorn_chicken': 'popcorn chicken',
        },
    },
    'sushi': {
        'logo': 'sushi restaurant interior',
        'items': {
            'salmon_sushi': 'salmon sushi',
            'california_roll': 'california maki sushi',
            'unagi_don': 'unagi don eel rice',
            'sashimi': 'sashimi platter',
            'miso_soup': 'miso soup',
        },
    },
}


def http_get(url, accept=None, retries=2):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    if accept:
        req.add_header('Accept', accept)
    last_exc = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read(), resp.headers.get('Content-Type', '')
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code in (429, 503) and attempt < retries:
                wait = 6 * (attempt + 1)
                print(f'    ~ 限流 {exc.code}，{wait}s 后重试')
                time.sleep(wait)
                continue
            raise
        except Exception as exc:  # 网络抖动同样重试
            last_exc = exc
            if attempt < retries:
                time.sleep(3)
                continue
            raise
    raise last_exc


def search_commons(query, limit=10, require=None, exclude=None):
    """返回 [{url, mime, page, license, artist}]；失败（限流等）返回空，交给兜底源"""
    params = {
        'action': 'query',
        'generator': 'search',
        'gsrsearch': f'filetype:bitmap {query}',
        'gsrnamespace': '6',
        'gsrlimit': str(limit),
        'prop': 'imageinfo',
        'iiprop': 'url|mime|extmetadata',
        'iiurlwidth': '900',
        'format': 'json',
    }
    url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params)
    try:
        raw, _ = http_get(url, 'application/json')
    except Exception as exc:
        print(f'    ~ Commons 检索失败（{exc}），改用兜底源')
        return []
    data = json.loads(raw.decode('utf-8'))
    pages = (data.get('query') or {}).get('pages') or {}
    results = []
    for page in pages.values():
        title = (page.get('title') or '').lower()
        # 标题必须包含关键词，避免检索串味（如 croissant 搜到加油站）
        if require and require.lower() not in title:
            continue
        if exclude and any(w in title for w in exclude):
            continue
        info = (page.get('imageinfo') or [{}])[0]
        mime = info.get('mime') or ''
        if mime not in ('image/jpeg', 'image/png'):
            continue
        if (info.get('thumbwidth') or 0) < 600:
            continue
        meta = info.get('extmetadata') or {}
        results.append({
            'url': info.get('thumburl') or info.get('url'),
            'mime': mime,
            'page': info.get('descriptionurl') or '',
            'license': (meta.get('LicenseShortName') or {}).get('value') or 'unknown',
            'artist': (meta.get('Artist') or {}).get('value') or '',
        })
    # 搜索相关性由 generator 排序保证，直接取第一个可用结果
    return results


def search_themealdb(query):
    url = 'https://www.themealdb.com/api/json/v1/1/search.php?s=' + urllib.parse.quote(query)
    try:
        raw, _ = http_get(url, 'application/json')
        data = json.loads(raw.decode('utf-8'))
        meals = data.get('meals') or []
        if not meals:
            return []
        meal = meals[0]
        return [{
            'url': meal.get('strMealThumb'),
            'mime': 'image/jpeg',
            'page': f"https://www.themealdb.com/meal/{meal.get('idMeal')}",
            'license': 'TheMealDB free API (demo use)',
            'artist': meal.get('strMeal') or '',
        }]
    except Exception:
        return []


def sniff_ext(payload, content_type):
    if payload[:3] == b'\xff\xd8\xff':
        return '.jpg'
    if payload[:8] == b'\x89PNG\r\n\x1a\n':
        return '.png'
    if 'jpeg' in content_type:
        return '.jpg'
    if 'png' in content_type:
        return '.png'
    return None


def fetch_by_title(title, dest_noext):
    """按 Commons 文件名精确取图"""
    params = {
        'action': 'query',
        'titles': title,
        'prop': 'imageinfo',
        'iiprop': 'url|mime|extmetadata',
        'iiurlwidth': '900',
        'format': 'json',
    }
    url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params)
    try:
        raw, _ = http_get(url, 'application/json')
        data = json.loads(raw.decode('utf-8'))
        pages = (data.get('query') or {}).get('pages') or {}
        page = next(iter(pages.values()), {})
        info = (page.get('imageinfo') or [{}])[0]
        if not info.get('url'):
            return None
        meta = info.get('extmetadata') or {}
        payload, ctype = http_get(info.get('thumburl') or info['url'])
        ext = sniff_ext(payload, ctype)
        if not ext or len(payload) < 15 * 1024:
            return None
        path = dest_noext + ext
        with open(path, 'wb') as fh:
            fh.write(payload)
        return {
            'file': os.path.relpath(path, BASE_DIR).replace('\\', '/'),
            'query': title,
            'source': info.get('descriptionurl') or '',
            'license': (meta.get('LicenseShortName') or {}).get('value') or 'unknown',
            'artist': ((meta.get('Artist') or {}).get('value') or '')[:120],
            'bytes': len(payload),
        }
    except Exception as exc:
        print(f'    ~ 指定文件获取失败（{exc}）')
        return None


def fetch_one(query, dest_noext, dish=True):
    """按查询词取一张图，成功返回来源 dict，失败返回 None

    dish=True 时排除门面/菜单类照片（菜品图），门店图传 False。
    """
    require = query.split()[0] if query else None
    exclude = SHOP_WORDS if dish else None
    candidates = search_commons(query, require=require, exclude=exclude) or search_themealdb(query)
    for cand in candidates:
        if not cand.get('url'):
            continue
        try:
            payload, ctype = http_get(cand['url'])
        except Exception as exc:
            print(f'    ! 下载失败 {cand["url"][:80]}: {exc}')
            continue
        ext = sniff_ext(payload, ctype)
        if not ext or len(payload) < 15 * 1024:
            continue
        path = dest_noext + ext
        with open(path, 'wb') as fh:
            fh.write(payload)
        return {
            'file': os.path.relpath(path, BASE_DIR).replace('\\', '/'),
            'query': query,
            'source': cand['page'],
            'license': cand['license'],
            'artist': cand['artist'][:120],
            'bytes': len(payload),
        }
    return None


def main():
    os.makedirs(MEDIA_DIR, exist_ok=True)
    sources = {}
    if os.path.exists(SOURCES_FILE):
        with open(SOURCES_FILE, encoding='utf-8') as fh:
            sources = json.load(fh)

    total = ok = 0
    for shop, spec in MANIFEST.items():
        shop_dir = os.path.join(MEDIA_DIR, shop)
        os.makedirs(shop_dir, exist_ok=True)
        tasks = [('logo', spec['logo'])] + list(spec['items'].items())
        print(f'== {shop} ==')
        for name, query in tasks:
            total += 1
            existing = [p for p in (os.path.join(shop_dir, name + e) for e in ('.jpg', '.png'))
                        if os.path.exists(p)]
            if existing:
                ok += 1
                print(f'  = {name}: 已存在，跳过')
                continue
            print(f'  > {name}: 搜索 "{query}"')
            pinned = PINNED.get(f'{shop}/{name}')
            record = None
            if pinned:
                record = fetch_by_title(pinned, os.path.join(shop_dir, name))
            if not record:
                record = fetch_one(query, os.path.join(shop_dir, name), dish=(name != 'logo'))
            if record:
                ok += 1
                key = f'{shop}/{name}'
                sources[key] = record
                print(f'    ✓ {record["file"]} ({record["bytes"] // 1024}KB, {record["license"]})')
            else:
                print(f'    ✗ 未找到可用图片，保留占位')
            time.sleep(1.5)  # 礼貌间隔，避免触发图库限流

    with open(SOURCES_FILE, 'w', encoding='utf-8') as fh:
        json.dump(sources, fh, ensure_ascii=False, indent=2)
    print(f'\n完成：{ok}/{total} 张图片就绪，来源清单已写入 {SOURCES_FILE}')
    return 0 if ok == total else 1


if __name__ == '__main__':
    sys.exit(main())
