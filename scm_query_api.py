#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCM 统一查询系统 - API版本
使用API接口查询订单进度，比浏览器自动化更稳定高效
正确流程：
1. 订单分页API → 获取 orderNo、orderId、orderNumbers
2. 订单明细API → 用 orderId 获取订单详细信息
3. 生产进度API → 获取订单生产进度信息

注意：对于生产单号查询，需要先通过生产进度API获取订单号，再查询订单分页列表
"""

import re
import json
import sys
import argparse
import requests

# 查询配置
QUERY_CONFIG = {
    # API配置
    "api_url": "http://api.ceyadi.cn/v1/order/getProProgressList",
    "info_url": "http://api.ceyadi.cn/v1/order/info",
    "items_url": "http://api.ceyadi.cn/v1/orderItems/list",
    "page_url": "http://api.ceyadi.cn/v1/order/page",
    "login_url": "http://api.ceyadi.cn/v1/oauth/getToken",
    
    # 认证配置
    "access_key_id": "NeIFPBmDEbfs2Brp",
    "access_key_secret": "ec976ad7959b2245b7d3e002002e22b2",
    
    # 缓存的token
    "cached_token": None,
    
    # 查询类型配置
    "query_types": {
        "order": {
            "name": "生产单号查询",
            "patterns": [
                r"^订单\s+(\*?\d{8,9})$",
                r"^查订单\s+(\*?\d{8,9})$",
                r"^(\*?\d{8,9})\s+进度$",
                r"^生产进度\s+(\*?\d{8,9})$",
                r"^订单进度\s+(\*?\d{8,9})$",
                r"^订单\s+([A-Za-z0-9]{10,15})$",
                r"^查订单\s+([A-Za-z0-9]{10,15})$"
            ]
        },
        "customer": {
            "name": "客户姓名查询",
            "patterns": [
                r"^查客户\s+(\S+)\s+订单$",
                r"^客户\s+(\S+)\s+订单$",
                r"^搜索客户\s+(\S+)\s+订单$",
                r"^(\S+)\s+的订单$"
            ]
        },
        "serial": {
            "name": "流水号查询",
            "patterns": [
                r"^查流水号\s+(\d+)\s+订单$",
                r"^流水号\s+(\d+)\s+订单$",
                r"^流水号\s+(\d+)\s+进度$",
                r"^(\d+)\s+流水号信息$",
                r"^查流水号\s+(\d+)\s+(\d{4}-\d{2}-\d{2})\s+订单$",
                r"^流水号\s+(\d+)\s+(\d{4}-\d{2}-\d{2})\s+订单$",
                r"^查流水号\s+(\d+)\s+(\d{4}-\d{2}-\d{2}).*$",
                r"^流水号\s+(\d+)\s+(\d{4}-\d{2}-\d{2}).*$",
                r"^查流水号\s+(\d+).*$",
                r"^流水号\s+(\d+).*$"
            ]
        }
    }
}

def parse_query(input_text):
    """
    判断查询类型并提取参数
    """
    for query_type, config in QUERY_CONFIG["query_types"].items():
        for pattern in config["patterns"]:
            match = re.match(pattern, input_text)
            if match:
                params = list(match.groups())
                
                # 处理流水号查询中的日期格式转换（年月日 -> 标准格式）
                if query_type == "serial" and len(params) > 2:
                    if len(params) == 4:
                        serial_no = params[0]
                        year = params[1]
                        month = params[2].zfill(2)
                        day = params[3].zfill(2)
                        order_date = f"{year}-{month}-{day}"
                        params = [serial_no, order_date]
                
                return {
                    "type": query_type,
                    "params": params,
                    "name": config["name"],
                    "match": match.group(0)
                }
    return None

def get_token():
    """
    获取登录token
    """
    if QUERY_CONFIG.get("cached_token"):
        return QUERY_CONFIG["cached_token"]
    
    login_url = QUERY_CONFIG["login_url"]
    access_key_id = QUERY_CONFIG["access_key_id"]
    access_key_secret = QUERY_CONFIG["access_key_secret"]
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    data = {
        "accessKeyId": access_key_id,
        "accessKeySecret": access_key_secret
    }
    
    try:
        response = requests.post(login_url, headers=headers, data=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("code") == 1000:
                token = result.get("data", {}).get("token")
                if token:
                    QUERY_CONFIG["cached_token"] = token
                    return token
        
        print(f"登录失败: {result.get('message', '未知错误')}")
        return None
    except Exception as e:
        print(f"登录请求异常: {e}")
        import traceback
        traceback.print_exc()
        return None

def query_order_info(order_id=None):
    """
    使用API查询订单详情，获取量体信息、面料信息和订单备注
    必须使用订单ID(id)来查询，否则返回空数据或测试数据
    order_id: 订单主表ID（从订单分页API获取的id字段）
    """
    info_url = QUERY_CONFIG["info_url"]
    token = get_token()
    
    if not token:
        return None
    
    if not order_id:
        return None
    
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # 必须使用id参数，否则返回空数据或固定测试数据
    request_data = {"id": order_id}
    
    try:
        response = requests.post(info_url, headers=headers, json=request_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("code") == 1000:
                data = result.get("data", {})
                # 验证是否返回了真实数据（不是固定测试数据）
                # 注意：data.get("id")可能是整数，order_id可能是字符串，需要转换类型比较
                data_id = data.get("id")
                if str(data_id) == str(order_id):
                    return data
                # 如果返回的id与传入的order_id不一致，说明返回的是测试数据
                elif data_id == 237 and data.get("khName") == "11":
                    # 这是测试数据，不使用
                    return None
            return None
        return None
    except Exception as e:
        return None

def query_order_items(order_id):
    """
    使用API查询订单明细列表，获取面料货号等详细信息
    需要传入订单ID（orderId）才能查询到数据
    """
    items_url = QUERY_CONFIG["items_url"]
    token = get_token()
    
    if not token:
        return None
    
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    request_data = {"orderId": order_id}
    
    try:
        response = requests.post(items_url, headers=headers, json=request_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("code") == 1000:
                return result.get("data", [])
        return None
    except Exception as e:
        return None

def query_order_page(params):
    """
    使用订单分页API查询订单列表
    支持按客户姓名、订单号等条件查询
    params: dict, 包含查询条件，如 {"khName": "客户名"} 或 {"orderNo": "订单号"}
            支持分页参数: {"page": 页码}
    """
    page_url = QUERY_CONFIG["page_url"]
    token = get_token()
    
    if not token:
        return None
    
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    request_data = {
        "page": params.get("page", 1),
        "size": 1000
    }
    
    # 添加查询条件
    if "khName" in params:
        request_data["khName"] = params["khName"]
    if "orderNo" in params:
        request_data["orderNo"] = params["orderNo"]
    
    try:
        response = requests.post(page_url, headers=headers, json=request_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("code") == 1000:
                data = result.get("data", {})
                return data.get("list", [])
        return None
    except Exception as e:
        return None

def query_progress_by_order_numbers(order_numbers):
    """
    使用生产进度API查询订单进度
    order_numbers: 订单号列表
    """
    api_url = QUERY_CONFIG["api_url"]
    token = get_token()
    
    if not token:
        print("无法获取token，查询失败")
        return None
    
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    request_data = {"orderNumbers": order_numbers}
    
    try:
        response = requests.post(api_url, headers=headers, json=request_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("code") == 1000:
                return result.get("data", [])
            else:
                print(f"生产进度查询失败: {result.get('message')}")
                return None
        else:
            print(f"生产进度查询请求失败，状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"生产进度查询请求异常: {e}")
        return None

def query_progress_by_params(**kwargs):
    """
    使用生产进度API查询订单进度（支持更多查询参数）
    支持参数:
        scene: 场景名称，如 "proProgressList"
        serialNo: 流水号
        keyWord: 模糊查询关键词
        orderNumbers: 订单号列表
    """
    api_url = QUERY_CONFIG["api_url"]
    token = get_token()
    
    if not token:
        print("无法获取token，查询失败")
        return None
    
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    request_data = kwargs
    
    try:
        response = requests.post(api_url, headers=headers, json=request_data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("code") == 1000:
                return result.get("data", [])
            else:
                print(f"生产进度查询失败: {result.get('message')}")
                return None
        else:
            print(f"生产进度查询请求失败，状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"生产进度查询请求异常: {e}")
        return None

def execute_query_new(input_text):
    """
    新的主查询函数，按照正确的API调用顺序：
    
    对于生产单号查询：
    1. 生产进度API → 获取订单号 orderNo
    2. 订单分页API → 用 orderNo 获取 orderId
    3. 订单明细API → 用 orderId 获取订单详细信息
    4. 生产进度API → 获取订单生产进度信息（已在步骤1获取）
    
    对于客户姓名查询：
    1. 订单分页API → 获取 orderNo、orderId
    2. 订单明细API → 用 orderId 获取订单详细信息
    3. 生产进度API → 获取订单生产进度信息
    
    对于流水号查询：
    1. 订单详情API → 获取订单号 orderNo
    2. 订单分页API → 用 orderNo 获取 orderId
    3. 订单明细API → 用 orderId 获取订单详细信息
    4. 生产进度API → 获取订单生产进度信息
    """
    print(f"\n{'='*60}")
    print(f"📋 原始查询: {input_text}")
    print(f"{'='*60}\n")
    
    query_info = parse_query(input_text)
    
    if not query_info:
        return "❌ 无法识别的查询格式。请使用以下格式之一：\n" \
               "1. 生产单号查询：订单 *202601442 或 查订单 *202601442\n" \
               "2. 客户姓名查询：查客户 陈兵 订单 或 客户 陈兵 订单\n" \
               "3. 流水号查询：查流水号 16458 订单 或 流水号 16458 订单"
    
    print(f"✅ 查询类型: {query_info['name']}")
    print(f"📋 查询参数: {query_info['params']}")
    print(f"\n{'='*60}\n")
    
    order_no = ""
    order_id = ""
    prod_no = query_info["params"][0] if query_info["type"] == "order" else ""
    progress_data = None
    items_info = None
    
    if query_info["type"] == "order":
        # 生产单号查询：步骤1 - 首先通过生产进度API获取订单号
        print(f"🔍 步骤1: 通过生产进度API获取订单号...")
        input_prod_no = query_info["params"][0]  # 保留星号
        
        # 首先通过生产进度API获取订单号
        progress_data = query_progress_by_order_numbers([input_prod_no])
        
        if progress_data and len(progress_data) > 0:
            order_data = progress_data[0]
            prod_no = order_data.get("orderNumber", "")
            print(f"   ✓ 获取到生产单号: {prod_no}")
            
            # 步骤2: 通过流水号匹配订单
            print(f"\n🔍 步骤2: 通过流水号匹配订单...")
            
            # 从生产进度数据中提取所有流水号
            product_numbers = set()
            for progress_item in progress_data[0].get("list", []):
                for detail in progress_item:
                    product_numbers.add(str(detail.get("productNumber", "")))
            
            print(f"   需要匹配的流水号: {', '.join(product_numbers)}")
            
            # 遍历所有订单页面查找匹配流水号的订单
            page = 1
            found_order = None
            
            while page <= 20:
                orders_page = query_order_page({"page": page})
                if not orders_page or len(orders_page) == 0:
                    break
                
                for order in orders_page:
                    # 获取订单的明细来检查流水号
                    order_id_temp = order.get("id", "")
                    items_temp = query_order_items(order_id_temp)
                    if items_temp:
                        for item in items_temp:
                            # 检查流水号是否匹配（使用serialNo字段）
                            serial_no = str(item.get("serialNo", ""))
                            ks_code = str(item.get("ksCode", ""))
                            
                            if serial_no in product_numbers or ks_code in product_numbers:
                                found_order = order
                                print(f"   ✓ 在第 {page} 页找到匹配订单")
                                break
                        if found_order:
                            break
                
                if found_order:
                    break
                page += 1
            
            orders_page = [found_order] if found_order else None
            
            if orders_page and len(orders_page) > 0:
                first_order = orders_page[0]
                order_id = first_order.get("id", "")
                order_no = first_order.get("orderNo", "")
                print(f"   ✓ 订单ID: {order_id}")
                print(f"   ✓ 订单号: {order_no}")
            else:
                print(f"   ✗ 未找到订单信息")
                return "未找到匹配的订单信息"
        else:
            print(f"   ✗ 未找到生产进度信息")
            return "未找到匹配的订单信息"
        
        # 步骤2: 查询订单明细列表（使用orderId）
        print(f"\n🔍 步骤2: 查询订单明细列表...")
        if order_id:
            items_info = query_order_items(order_id)
        
        if items_info and len(items_info) > 0:
            print(f"   ✓ 获取到 {len(items_info)} 条明细")
        else:
            print(f"   ✗ 未获取到订单明细")
        
        # 步骤3: 查询生产进度
        print(f"\n🔍 步骤3: 查询生产进度...")
        if order_no:
            progress_data = query_progress_by_order_numbers([order_no])
            if not progress_data or len(progress_data) == 0:
                # 如果订单号查询失败，尝试用原始生产单号查询
                progress_data = query_progress_by_order_numbers([input_prod_no])
        
        if progress_data and len(progress_data) > 0:
            print(f"   ✓ 获取到生产进度")
        else:
            print(f"   ✗ 未获取到生产进度")
    
    elif query_info["type"] == "customer":
        # 客户姓名查询：先使用生产进度API的keyWord查询，再查询订单分页列表
        print(f"🔍 步骤1: 使用生产进度API查找客户...")
        customer_name = query_info["params"][0]
        
        # 步骤1: 先用生产进度API的keyWord参数查询
        progress_data = query_progress_by_params(scene="proProgressList", keyWord=customer_name)
        
        order_id = None
        order_no = None
        prod_no = None
        found_items = None
        
        if progress_data and len(progress_data) > 0:
            print(f"   ✓ 在生产进度API中找到匹配")
            
            # 从生产进度数据中获取流水号
            serial_numbers = []
            for order_data in progress_data:
                prod_no = order_data.get("orderNumber", "")
                for item_group in order_data.get("list", []):
                    for detail in item_group:
                        serial_no = detail.get("productNumber", "")
                        if serial_no and serial_no not in serial_numbers:
                            serial_numbers.append(serial_no)
            
            print(f"   找到的流水号: {', '.join(serial_numbers)}")
            
            # 步骤2: 通过流水号查找订单
            print(f"\n🔍 步骤2: 通过流水号查找订单...")
            for serial_no in serial_numbers:
                # 查询所有订单，通过流水号匹配
                found_order = None
                for page in range(1, 21):
                    orders_page = query_order_page({"page": page})
                    if not orders_page:
                        break
                    
                    for order in orders_page:
                        order_id_temp = order.get("id", "")
                        items_temp = query_order_items(order_id_temp)
                        if items_temp:
                            for item in items_temp:
                                item_serial = str(item.get("serialNo", ""))
                                item_product = str(item.get("productNumber", ""))
                                if item_serial == serial_no or item_product == serial_no:
                                    found_order = order
                                    found_items = items_temp
                                    print(f"   ✓ 通过流水号 {serial_no} 找到订单")
                                    break
                            if found_order:
                                break
                    if found_order:
                        break
                
                if found_order:
                    order_id = found_order.get("id", "")
                    order_no = found_order.get("orderNo", "")
                    break
        else:
            print(f"   ⚠ 生产进度API未找到，尝试订单分页列表...")
            # 如果生产进度API没找到，继续用原来的方式查询
            page = 1
            found_order = None
            
            while page <= 20:
                print(f"   正在查询第 {page} 页...")
                orders_page = query_order_page({"page": page})
                
                if orders_page is None:
                    print(f"   ⚠ 第 {page} 页查询失败")
                elif len(orders_page) == 0:
                    print(f"   ⚠ 第 {page} 页无数据")
                    if page == 1:
                        break
                else:
                    kh_names = [order.get("khName", "") for order in orders_page]
                    print(f"   本页客户: {', '.join([name for name in kh_names if name])}")
                    
                    matched_orders = [
                        order for order in orders_page 
                        if order.get("khName") and (customer_name == order.get("khName") or customer_name in order.get("khName"))
                    ]
                    
                    if matched_orders:
                        found_order = matched_orders[0]
                        break
                
                page += 1
            
            if found_order:
                order_id = found_order.get("id", "")
                order_no = found_order.get("orderNo", "")
        
        if not order_id:
            return "未找到匹配的订单信息"
        
        print(f"   ✓ 订单ID: {order_id}")
        print(f"   ✓ 订单号: {order_no}")
        
        # 步骤2: 查询订单明细列表（使用orderId）
        print(f"\n🔍 步骤2: 查询订单明细列表...")
        if not found_items:  # 如果还没有获取到items
            items_info = query_order_items(order_id) if order_id else None
        else:
            items_info = found_items
        
        if items_info and len(items_info) > 0:
            print(f"   ✓ 获取到 {len(items_info)} 条明细")
        else:
            print(f"   ✗ 未获取到订单明细")
        
        # 步骤3: 查询订单详情获取生产单号
        print(f"\n🔍 步骤3: 查询订单详情获取生产单号...")
        order_info = query_order_info(order_id) if order_id else None
        if order_info:
            prod_no = order_info.get("prodNo", "")
            if prod_no:
                print(f"   ✓ 获取到生产单号: {prod_no}")
        
        # 步骤4: 查询生产进度
        print(f"\n🔍 步骤4: 查询生产进度...")
        if not progress_data:  # 如果还没有获取到progress_data
            if prod_no:
                progress_data = query_progress_by_order_numbers([prod_no])
            if (not progress_data or len(progress_data) == 0) and order_no:
                progress_data = query_progress_by_order_numbers([order_no])
        
        if progress_data and len(progress_data) > 0:
            print(f"   ✓ 获取到生产进度")
        else:
            print(f"   ✗ 未获取到生产进度")
    
    elif query_info["type"] == "serial":
        # 流水号查询：步骤1 - 查询订单分页列表，先检查serialNoList字段
        print(f"🔍 步骤1: 查询订单分页列表查找流水号...")
        serial_no = query_info["params"][0]
        
        # 查询订单分页列表
        orders_page = query_order_page({})
        
        if not orders_page or len(orders_page) == 0:
            return "未找到匹配的订单信息"
        
        # 遍历订单列表，查找匹配的流水号
        found_order = None
        found_items = None
        
        for order in orders_page:
            order_id = order.get("id", "")
            order_no = order.get("orderNo", "")
            
            # 优先检查serialNoList字段（逗号分隔的流水号列表）
            serial_no_list = order.get("serialNoList", "")
            if serial_no_list:
                serial_numbers = [s.strip() for s in serial_no_list.split(",")]
                if str(serial_no) in serial_numbers:
                    # 在serialNoList中找到匹配的流水号
                    print(f"   ✓ 在serialNoList中找到匹配")
                    found_order = order
                    # 查询订单明细获取详细信息
                    items_info = query_order_items(order_id)
                    if items_info and len(items_info) > 0:
                        matched_items = [
                            item for item in items_info 
                            if str(item.get("serialNo", "")) == str(serial_no) or 
                               str(item.get("productNumber", "")) == str(serial_no) or
                               str(item.get("ksCode", "")) == str(serial_no)
                        ]
                        found_items = matched_items if matched_items else items_info
                    break
            
            # 如果serialNoList为空或未找到匹配，查询订单明细
            items_info = query_order_items(order_id)
            
            if items_info and len(items_info) > 0:
                # 检查是否有匹配的流水号
                matched_items = [
                    item for item in items_info 
                    if str(item.get("serialNo", "")) == str(serial_no) or 
                       str(item.get("productNumber", "")) == str(serial_no) or
                       str(item.get("ksCode", "")) == str(serial_no)
                ]
                
                if matched_items:
                    found_order = order
                    found_items = matched_items
                    break
        
        if not found_order:
            return f"未找到流水号 {serial_no} 对应的订单信息"
        
        order_id = found_order.get("id", "")
        order_no = found_order.get("orderNo", "")
        items_info = found_items
        
        print(f"   ✓ 找到匹配的订单")
        print(f"   ✓ 订单ID: {order_id}")
        print(f"   ✓ 订单号: {order_no}")
        print(f"   ✓ 获取到 {len(items_info)} 条匹配的明细")
        
        # 步骤2: 查询订单详情获取生产单号
        print(f"\n🔍 步骤2: 查询订单详情获取生产单号...")
        order_info = query_order_info(order_id) if order_id else None
        if order_info:
            prod_no = order_info.get("prodNo", "")
            if prod_no:
                print(f"   ✓ 获取到生产单号: {prod_no}")
        
        # 步骤3: 查询生产进度
        print(f"\n🔍 步骤3: 查询生产进度...")
        progress_data = None
        
        if prod_no:
            progress_data = query_progress_by_order_numbers([prod_no])
        if not progress_data or len(progress_data) == 0:
            # 如果生产单号查询失败，尝试用订单号查询
            if order_no:
                progress_data = query_progress_by_order_numbers([order_no])
                if not progress_data or len(progress_data) == 0:
                    progress_data = query_progress_by_order_numbers([f"*{order_no}"])
        
        # 如果还是失败，尝试用流水号作为生产单号查询
        if not progress_data or len(progress_data) == 0:
            progress_data = query_progress_by_order_numbers([f"*{serial_no}"])
        
        if progress_data and len(progress_data) > 0:
            print(f"   ✓ 获取到生产进度")
        else:
            print(f"   ✗ 未获取到生产进度")
    
    # 格式化输出结果
    return format_result_new(query_info, order_no, prod_no, items_info, progress_data)

def format_result_new(query_info, order_no, prod_no, items_info, progress_data):
    """
    格式化查询结果
    """
    output = []
    
    if query_info["type"] == "serial":
        output.append(f"订单进度：流水号 {query_info['params'][0]}")
    elif query_info["type"] == "order":
        output.append(f"订单进度：{prod_no}")
    elif query_info["type"] == "customer":
        output.append(f"订单进度：客户 {query_info['params'][0]}")
    
    output.append("-" * 40)
    output.append(f"【订单】{order_no}")
    
    # 构建进度信息映射（使用索引和流水号）
    progress_map = {}
    progress_list = []  # 用于按索引匹配
    if progress_data and len(progress_data) > 0:
        for order_data in progress_data:
            process_list = order_data.get("list", [])
            for idx, item_group in enumerate(process_list, 1):
                product_number = ""
                process_dates = {}
                for process in item_group:
                    process_name = process.get("processName", "")
                    real_finish_date = process.get("realFinishDate", "")
                    if real_finish_date:
                        process_dates[process_name] = real_finish_date.split(" ")[0]
                    if not product_number:
                        product_number = process.get("productNumber", "")
                # 同时保存到索引和流水号映射
                progress_map[product_number] = process_dates
                progress_map[str(idx)] = process_dates
                progress_list.append(process_dates)
    
    # 显示订单明细
    if items_info and len(items_info) > 0:
        for item_idx, item in enumerate(items_info, 1):
            # 尝试多种可能的流水号字段名
            product_number = item.get("serialNo", "") or item.get("productNumber", "") or item.get("ksCode", "") or f"明细{item_idx}"
            pattern_code = item.get("patternCode", "")
            fabric_no = item.get("fabric", "未获取")
            
            output.append(f"【明细{item_idx}】流水号:{product_number} | 版型:{pattern_code} | 面料:{fabric_no}")
            
            detail_lines = []
            color_name = item.get("colorName", "")
            color_code = item.get("colorCode", "")
            if color_name or color_code:
                color_text = color_name if color_name else color_code
                detail_lines.append(f"颜色:{color_text}")
            
            size = item.get("size", "")
            drop = item.get("drop", "")
            if size or drop:
                size_text = f"{size}"
                if drop:
                    size_text += f"/{drop}"
                detail_lines.append(f"尺码:{size_text}")
            
            quantity = item.get("quantity", 0)
            if quantity > 0:
                detail_lines.append(f"数量:{quantity}")
            
            fabric_supply = item.get("fabricSupply", "")
            fabric_style = item.get("fabricStyle", "")
            fabric_mark = item.get("fabricMark", "")
            if fabric_supply:
                detail_lines.append(f"面料供应:{fabric_supply}")
            if fabric_style:
                detail_lines.append(f"面料风格:{fabric_style}")
            if fabric_mark:
                detail_lines.append(f"面料品牌:{fabric_mark}")
            
            if detail_lines:
                output.append(f"    {' | '.join(detail_lines)}")
            
            # 量体信息
            net_size = item.get("netSize", {})
            if net_size and isinstance(net_size, dict):
                size_lines = []
                size_map = {
                    "fullBust": "胸围",
                    "fullWaistWidth": "腰围",
                    "fullHipWidth": "臀围",
                    "shoulderWidth": "肩宽",
                    "sleeveLength": "袖长",
                    "frontLength": "衣长",
                    "upperleg": "大腿围",
                    "wholewave": "横档",
                    "foodwith": "脚口",
                    "longPants": "裤长"
                }
                for key, value in net_size.items():
                    if value and key in size_map:
                        size_lines.append(f"{size_map[key]}:{value}")
                if size_lines:
                    output.append(f"    📏 量体信息: {' | '.join(size_lines)}")
            
            # 进度信息
            # 优先使用索引匹配，因为订单明细和生产进度的顺序应该一致
            process_dates = {}
            if progress_list and item_idx <= len(progress_list):
                process_dates = progress_list[item_idx - 1]
            # 如果索引匹配失败，尝试使用流水号匹配
            if not process_dates:
                process_dates = progress_map.get(product_number, {})
                if not process_dates and str(item_idx) in progress_map:
                    process_dates = progress_map.get(str(item_idx), {})
            
            progress_lines = []
            for process in ["发料", "前道", "中道", "后道", "入库", "出库"]:
                date = process_dates.get(process, "")
                if date:
                    progress_lines.append(f"{process}:{date}")
                else:
                    progress_lines.append(f"{process}:未完成")
            
            output.append(f"    🔄 进度: {' | '.join(progress_lines)}")
            output.append("")
    
    return "\n".join(output)

def execute_query(input_text):
    """
    主查询函数（兼容旧接口）
    """
    return execute_query_new(input_text)

# ==================== OpenClaw 适配 ====================
def handle_tool(input_text: str = None) -> str:
    """
    OpenClaw 工具入口函数
    
    Args:
        input_text: 查询文本，支持三种格式：
            - 生产单号查询: "订单 *202608066" 或 "*202608066 进度"
            - 客户姓名查询: "客户 刘浩（员工） 订单" 或 "刘浩的订单"
            - 流水号查询: "流水号 11374" 或 "查流水号 11374 订单"
    
    Returns:
        str: 查询结果文本
    """
    if not input_text:
        return "请提供查询内容，例如：\n- 订单 *202608066\n- 客户 刘浩（员工） 订单\n- 流水号 11374"
    
    try:
        result = execute_query_new(input_text)
        return result
    except Exception as e:
        return f"查询失败: {str(e)}"

# ==================== 旧版命令行入口 ====================
def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='SCM 统一查询系统 - API版本')
    parser.add_argument('query', nargs='*', help='查询内容')
    
    args = parser.parse_args()
    
    if args.query:
        query_text = ' '.join(args.query)
        result = execute_query(query_text)
        print(result)
    else:
        print("请输入查询内容（输入 'quit' 退出）：")
        while True:
            try:
                user_input = input("> ").strip()
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                if user_input:
                    result = execute_query(user_input)
                    print(result)
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\n已退出")
                break

if __name__ == "__main__":
    main()
