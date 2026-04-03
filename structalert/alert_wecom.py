import requests
import json
from loguru import logger
from datetime import datetime

# 企业微信Webhook基础URL
WECHAT_WEBHOOK_BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key="

class WeComAlert:
    def __init__(self, webhook_key: str):
        """
        初始化企业微信告警客户端
        :param webhook_key: 企业微信机器人的key
        """
        if not webhook_key:
            logger.warning("企业微信Webhook Key为空，告警功能将不可用")
            self.webhook_url = None
        else:
            self.webhook_url = f"{WECHAT_WEBHOOK_BASE_URL}{webhook_key}"

    def send_template_card(self, date_str: str, diff_list: list, total_count: int, stats=None):
        """
        发送企业微信模版卡片消息
        :param date_str: 比对日期字符串 (YYYY-MM-DD)
        :param diff_list: 存在差异的对象字典列表 [{"object_name": "x", "object_type": "TABLE", "diff_msg": "..."}]
        :param total_count: 差异对象总数
        :param stats: 统计信息字典
        """
        if not self.webhook_url:
            logger.warning("未配置企业微信 Webhook URL，跳过发送报警。")
            return False

        if not diff_list:
            logger.info("没有差异对象，无需发送企业微信报警。")
            return True

        # 直接使用 markdown 格式发送，因为更适合展示差异详情
        return self.send_markdown(date_str, diff_list, total_count, stats)

    def send_markdown(self, date_str: str, diff_list: list, total_count: int, stats=None):
        """发送 Markdown 格式消息（通常比卡片更适合展示列表细节）"""
        if not self.webhook_url:
            return False

        content = f"### <font color='warning'>🔴 数据库结构变更预警</font>\n"
        content += f"> **比对日期:** {date_str}\n"
        content += f"> **差异总数:** <font color='comment'>{total_count} 个</font>\n\n"

        # 添加详细统计信息
        if stats:
            content += "#### 📊 统计信息:\n"
            type_names = {
                'TABLE': '表',
                'VIEW': '视图',
                'PROCEDURE': '过程',
                'FUNCTION': '函数'
            }
            for obj_type, type_name in type_names.items():
                if obj_type in stats and stats[obj_type]['total'] > 0:
                    total = stats[obj_type]['total']
                    diff = stats[obj_type]['diff']
                    content += f"> **{type_name}**: 总计 {total} 个，差异 {diff} 个\n"
            content += "\n"

        content += "#### 差异详情速览:\n"
        for i, diff in enumerate(diff_list):
            if i >= 10:
                content += f"> ...及其他 {total_count - 10} 个对象，详见日志表。\n"
                break
            # 截断 diff_msg 防止过长
            msg = diff.get('diff_msg', '-')
            if len(msg) > 50:
                msg = msg[:47] + "..."
            content += f"> `{diff['object_type']}` **{diff['object_name']}** : <font color='comment'>{msg}</font>\n"

        content += "\n👉 *请相关人员及时登录数据库（cfg_compare_objects所在的库），查看 `cfg_compare_diff` 表获取详细 DDL 修复脚本并执行同步。*"

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }

        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            res_data = resp.json()
            if res_data.get("errcode") == 0:
                logger.info(f"企业微信预警发送成功，共 {total_count} 条差异。")
                return True
            else:
                logger.error(f"企业微信预警发送失败: {res_data}")
                return False
        except Exception as e:
            logger.error(f"企业微信预警请求异常: {e}")
            return False
