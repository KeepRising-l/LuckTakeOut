/**
 * 订单状态：后端返回的整数枚举是唯一真值（10–60）。
 * 三端共用同一套取值；文案按各端视角呈现，需要时在端内覆盖个别措辞。
 */
export const ORDER_STATUS: Record<number, string> = {
  10: '待支付',
  20: '已支付',
  30: '待接单',
  40: '配送中',
  50: '已完成',
  60: '已取消',
}

/** 取状态文案；override 用于端内覆盖（如商户端把 30 呈现为「已接单，待骑手取餐」） */
export function orderStatusText(status: number | string, override?: Record<number, string>): string {
  const key = Number(status)
  return override?.[key] || ORDER_STATUS[key] || String(status)
}
