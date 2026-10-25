"""LLM 客户端（硅基流动 / OpenAI 兼容）。

- 配置了 LLM_API_KEY 时走真实接口；
- 未配置时使用内置的规则化 Mock，用于本地联调与答辩演示兜底。
"""

import json
import re
import urllib.error
import urllib.request

from django.conf import settings


def is_configured():
    return bool(getattr(settings, 'LLM_API_KEY', ''))


def chat_completion(messages, tools=None):
    """调用 Chat Completions，返回 assistant message（dict，可能含 tool_calls）。"""
    if not is_configured():
        return _mock_completion(messages)

    payload = {
        'model': settings.LLM_MODEL,
        'messages': _to_api_messages(messages),
        'temperature': 0.2,
    }
    if tools:
        payload['tools'] = tools
        payload['tool_choice'] = 'auto'

    req = urllib.request.Request(
        settings.LLM_BASE_URL.rstrip('/') + '/chat/completions',
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers={
            'Authorization': 'Bearer ' + settings.LLM_API_KEY,
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:  # noqa: BLE001
        # 欠费/断网/限流/密钥失效时降级到内置规则 Mock，保证演示与联调不中断
        import logging

        detail = ''
        if isinstance(e, urllib.error.HTTPError):
            detail = e.read().decode('utf-8', 'ignore')[:200]
        logging.getLogger(__name__).warning('LLM 调用失败，降级到内置 Mock：%s %s', e, detail)
        return _mock_completion(messages)
    return data['choices'][0]['message']


def _to_api_messages(messages):
    out = []
    for m in messages:
        item = {'role': m['role']}
        if 'content' in m:
            item['content'] = m.get('content')
        if m.get('tool_calls'):
            item['tool_calls'] = m['tool_calls']
        if m.get('tool_call_id'):
            item['tool_call_id'] = m['tool_call_id']
        out.append(item)
    return out


# --------------------------------------------------------------------------
# 内置 Mock：不依赖外部服务，按规则驱动 下单 / 催单 / 评价 三条链路
# --------------------------------------------------------------------------

_seq = {'n': 0}


def _tc(name, args):
    _seq['n'] += 1
    return {
        'role': 'assistant',
        'content': None,
        'tool_calls': [{
            'id': f'call_{_seq["n"]}',
            'type': 'function',
            'function': {'name': name, 'arguments': json.dumps(args, ensure_ascii=False)},
        }],
    }


def _text(content):
    return {'role': 'assistant', 'content': content}


def _tool_results(messages):
    """从对话中还原 {tool_name: parsed_result}。"""
    calls = {}
    results = {}
    for m in messages:
        if m.get('role') == 'assistant' and m.get('tool_calls'):
            for tc in m['tool_calls']:
                calls[tc['id']] = tc['function']['name']
        elif m.get('role') == 'tool':
            name = calls.get(m.get('tool_call_id'))
            if name:
                try:
                    results[name] = json.loads(m.get('content') or '{}')
                except Exception:
                    results[name] = {}
    return results


def _mock_completion(messages):
    user_msgs = [m for m in messages if m.get('role') == 'user']
    last_user = (user_msgs[-1].get('content') or '') if user_msgs else ''
    res = _tool_results(messages)
    called = set(res.keys())

    # --- 能力询问与无意义输入：先介绍能力，不盲目进下单链路 ---
    stripped = re.sub(r'[\s?？!！。，,.~～?]*', '', last_user)
    if not stripped or any(
        k in last_user for k in ('你能做什么', '能做什么', '你会什么', '怎么用', '你是谁', '帮助')
    ):
        return _text(
            '我是 AI 点餐助手，可以帮你：\n'
            '· 对话点餐：说「来一份川香小馆的招牌套餐」\n'
            '· 个性化推荐：说「推荐点什么」或「随便来」\n'
            '· 一键复购：说「再来一单」或「老样子」\n'
            '· 查订单进度：说「我的订单到哪了」\n'
            '· 催单：说「怎么还没到」\n'
            '· 评价：说「给个好评」\n'
            '想吃点什么，直接说～'
        )

    # --- 推荐（先看历史，再给推荐）---
    if any(k in last_user for k in ('推荐', '吃什么', '吃点啥', '随便来', '猜我')):
        if 'get_my_history' not in called:
            return _tc('get_my_history', {})
        if 'recommend_dishes' not in called:
            return _tc('recommend_dishes', {'limit': 4})
        dishes = (res.get('recommend_dishes') or {}).get('list') or []
        if not dishes:
            return _text('还没有足够的历史记录，先看看首页热销吧。')
        lines = [
            f"· {d['name']}（¥{d['price']}，{d['merchantName']}）—— {d['reason']}"
            for d in dishes[:4]
        ]
        return _text('根据你以前的订单，推荐这几样：\n' + '\n'.join(lines) + '\n要直接下单吗？')

    # --- 复购（老样子 / 再来一单）---
    if any(k in last_user for k in ('老样子', '再来一单', '和上次一样', '复购')):
        if 'get_my_history' not in called:
            return _tc('get_my_history', {})
        tops = (res.get('get_my_history') or {}).get('topDishes') or []
        if not tops:
            return _text('还没有历史订单，先下一单试试吧。')
        top = tops[0]
        if 'validate_draft' not in called:
            return _tc('validate_draft', {
                'merchant_id': top['merchantId'],
                'items': [{'product_id': top['productId'], 'quantity': 1}],
            })
        if 'create_draft' not in called:
            v = res.get('validate_draft') or {}
            return _tc('create_draft', {
                'merchant_id': top['merchantId'],
                'items': [{'product_id': i['product_id'], 'quantity': i['quantity']}
                          for i in (v.get('items') or [])],
            })
        draft = res.get('create_draft') or {}
        return _text(
            f"已按你常点的「{top['name']}」生成待确认草稿"
            f"（合计 ¥{draft.get('total', 0)}），确认后即可下单。"
        )

    # --- 催单 ---
    if any(k in last_user for k in ('催', '怎么还没', '多久到')):
        if 'get_order_status' not in called:
            return _tc('get_order_status', {'order_id': 0})
        if 'urge_order' not in called:
            return _tc('urge_order', {'order_id': 0, 'content': '顾客催单，请尽快配送'})
        u = res.get('urge_order') or {}
        return _text(u.get('message') or u.get('error') or '已为您催单。')

    # --- 评价 ---
    if '评价' in last_user or '评分' in last_user:
        if 'submit_review' not in called:
            return _tc('submit_review', {'order_id': 0, 'rating': 5, 'content': '味道不错，配送也快'})
        rv = res.get('submit_review') or {}
        if rv.get('ok'):
            return _text('已提交您的评价，感谢反馈！')
        return _text(rv.get('message') or rv.get('error') or '评价未成功。')

    # --- 下单：槽位收集 ---
    if 'search_merchant' not in called:
        return _tc('search_merchant', {'keyword': _guess_keyword(last_user)})

    if 'search_menu' not in called:
        mlist = (res.get('search_merchant') or {}).get('list') or []
        if not mlist:
            return _text('没有找到匹配的商家，请换一个说法。')
        return _tc('search_menu', {'merchant_id': mlist[0]['id']})

    if 'validate_draft' not in called:
        mlist = (res.get('search_merchant') or {}).get('list') or []
        plist = (res.get('search_menu') or {}).get('list') or []
        if not mlist or not plist:
            return _text('没有找到可下单的菜品，请换一个说法。')
        items = [{'product_id': plist[0]['id'], 'quantity': 1}]
        return _tc('validate_draft', {'merchant_id': mlist[0]['id'], 'items': items})

    if 'create_draft' not in called:
        v = res.get('validate_draft') or {}
        mlist = (res.get('search_merchant') or {}).get('list') or []
        return _tc('create_draft', {
            'merchant_id': mlist[0]['id'],
            'items': [{'product_id': i['product_id'], 'quantity': i['quantity']}
                      for i in (v.get('items') or [])],
        })

    draft = res.get('create_draft') or {}
    return _text(
        f"已为您生成待确认订单草稿（{draft.get('merchantName', '')}，"
        f"合计 ¥{draft.get('total', 0)}）。请顾客确认后即可下单。"
    )


def _guess_keyword(text):
    for kw in ('川香', '快乐奶茶', '奶茶', '炒菜', '咖啡', '面', '寿司', '快餐',
               '小馆', '湘菜', '汉堡', '炸鸡'):
        if kw in text:
            return kw
    return ''
