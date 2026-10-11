"""LLM 客户端（硅基流动 / OpenAI 兼容）。

- 配置了 LLM_API_KEY 时走真实接口；
- 未配置时使用内置的规则化 Mock，用于本地联调与答辩演示兜底。
"""

import json
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
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', 'ignore')
        raise RuntimeError(f'LLM 调用失败: HTTP {e.code} {detail}')
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
    for kw in ('川香', '快乐奶茶', '奶茶', '川菜', '快餐', '小馆'):
        if kw in text:
            return kw
    return ''
