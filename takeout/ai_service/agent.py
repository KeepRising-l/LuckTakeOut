"""对话代理：驱动 LLM 与工具的多轮循环。"""

import json

from .llm import chat_completion
from .models import ChatMessage
from .tools import TOOL_SCHEMAS, execute_tool

SYSTEM_PROMPT = (
    "你是外卖平台的客服助手，帮助顾客完成三件事：下单、催单、评价。\n"
    "规则：\n"
    "1. 只能通过工具获取和提交信息，绝不能凭空编造价格、库存、订单状态。\n"
    "2. 下单时必须依次调用 search_merchant、search_menu、get_item_specs、validate_draft、create_draft，"
    "最终生成的是「待确认草稿单」，不是正式订单；正式下单由顾客确认后由系统完成。\n"
    "3. 金额、库存、商户归属一律以后端校验结果为准。\n"
    "4. 地址：若顾客未提供收货地址，直接使用顾客的默认收货地址（create_draft 省略 address_id 即可），"
    "不要向顾客索要地址编号。\n"
    "5. 收齐足够信息后应直接调用 create_draft 生成草稿，而不是反复确认。\n"
    "6. 催单/评价：若顾客未提供订单号，直接使用其最近一笔订单（order_id 传 0），"
    "不要向顾客索要订单号。\n"
    "7. 回复简洁友好，使用中文。"
)

MAX_STEPS = 8


def _build_messages(session):
    messages = [{'role': 'system', 'content': SYSTEM_PROMPT}]
    history = (
        session.messages.filter(role__in=['user', 'assistant'])
        .exclude(content='').order_by('id')[:20]
    )
    for m in history:
        messages.append({'role': m.role, 'content': m.content})
    return messages


def run_agent(session, user_message):
    """执行一轮用户消息：可能触发多次工具调用，最终返回助手文本回复。"""
    ChatMessage.objects.create(session=session, role='user', content=user_message)
    messages = _build_messages(session)

    for _ in range(MAX_STEPS):
        msg = chat_completion(messages, tools=TOOL_SCHEMAS)
        tool_calls = msg.get('tool_calls')

        if tool_calls:
            messages.append(msg)
            for tc in tool_calls:
                name = tc['function']['name']
                try:
                    args = json.loads(tc['function'].get('arguments') or '{}')
                except Exception:
                    args = {}
                result = execute_tool(name, args, session)
                content = json.dumps(result, ensure_ascii=False)
                messages.append({'role': 'tool', 'tool_call_id': tc['id'], 'content': content})
                ChatMessage.objects.create(
                    session=session, role='tool', tool_name=name, content=content,
                )
            continue

        reply = msg.get('content') or ''
        ChatMessage.objects.create(session=session, role='assistant', content=reply)
        return reply

    fallback = '（对话步骤过多，请重新描述需求）'
    ChatMessage.objects.create(session=session, role='assistant', content=fallback)
    return fallback
