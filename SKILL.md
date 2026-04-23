---
name: scm_order_query
description: 查询服装订单的生产进度信息，支持生产单号、客户姓名、流水号三种查询方式
metadata:
  {
    "openclaw": {
      "emoji": "📦",
      "os": ["darwin", "linux", "win32"],
      "requires": {
        "bins": ["python3"],
        "anyBins": ["python"]
      }
    }
  }
---

# SCM订单查询

查询服装订单的生产进度信息。

## 使用场景

✅ **USE when:**
- 用户需要查询服装订单的生产进度
- 用户提供生产单号、客户姓名或流水号

❌ **DON'T use when:**
- 用户没有提供任何查询条件
- 查询条件格式不正确

## 快速开始

```bash
# 生产单号查询
python scm_query_api.py 订单 *202607578

# 客户姓名查询
python scm_query_api.py 客户 刘浩（员工） 订单

# 流水号查询
python scm_query_api.py 流水号 11374
```

## 触发关键词

- 订单 *202608066
- *202608066 进度
- 客户 刘浩（员工） 订单
- 刘浩的订单
- 流水号 11374
- 查流水号 11374 订单

## 参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| input_text | string | 查询文本，支持生产单号、客户姓名、流水号三种格式 |

## 工具调用

```json
{
  "name": "scm_order_query",
  "plugin": "python",
  "command": ["python", "scm_query_api.py", "{{input_text}}"]
}
```

## 输出示例

```
订单进度：客户 肖欢奇（员工）
----------------------------------------
【订单】25GN061260086
【明细1】流水号:13718 | 版型:1KN030 | 面料:43482/669
    颜色:绿色 | 尺码:50/R | 数量:1
    📏 量体信息: 胸围:93 | 臀围:92 | 腰围:85
    🔄 进度: 发料:未完成 | 前道:未完成 | 中道:未完成 | 后道:未完成 | 入库:未完成 | 出库:未完成
```

## 依赖安装

```bash
pip install requests
```

## 相关文件

- `scm_query_api.py` - 核心查询脚本
- `tool_config.json` - OpenClaw工具配置
