#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AML模式分析脚本 - 使用Spark GraphFrame进行模式匹配
输入：mock_data/account.csv, mock_data/transaction.csv
输出：result/detected_account.csv, result/detected_transaction.csv
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import pandas as pd
import os

def create_spark_session():
    """创建Spark会话 - Java 8兼容版本"""
    spark = SparkSession.builder \
        .appName("AML Pattern Analysis with GraphFrame") \
        .config("spark.jars.packages", "graphframes:graphframes:0.8.2-spark3.2-s_2.12") \
        .config("spark.executor.memory", "4g") \
        .config("spark.driver.memory", "4g") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark

def load_data(spark):
    """加载数据"""
    print("加载账户和交易数据...")
    
    # 加载账户数据
    accounts_df = spark.read.option("header", "true").option("inferSchema", "true").csv("mock_data/account.csv")
    
    # 加载交易数据
    transactions_df = spark.read.option("header", "true").option("inferSchema", "true").csv("mock_data/transaction.csv")
    
    print(f"账户数据: {accounts_df.count()} 条")
    print(f"交易数据: {transactions_df.count()} 条")
    
    return accounts_df, transactions_df

def create_graph(spark, accounts_df, transactions_df):
    """创建图结构"""
    print("创建图结构...")
    
    # 确保库已正确安装后再导入
    from graphframes import GraphFrame
    
    # 准备顶点数据（账户）
    vertices = accounts_df.select(
        col("account_id").alias("id"),
        col("owner_name"),
        col("country"),
        col("registration_date")
    )
    
    # 准备边数据（交易）- 添加日期信息用于模式匹配
    edges = transactions_df.select(
        col("src_account").alias("src"),
        col("dst_account").alias("dst"),
        col("transaction_id"),
        col("amount"),
        col("value_date"),
        to_date(col("value_date"), "yyyy-MM-dd HH:mm:ss").alias("transaction_date"),
        col("currency")
    )
    
    # 创建图
    graph = GraphFrame(vertices, edges)
    
    print(f"图顶点数: {graph.vertices.count()}")
    print(f"图边数: {graph.edges.count()}")
    
    return graph

def detect_circular_patterns_with_graphframe(spark, graph):
    """使用GraphFrame检测循环闭环交易模式"""
    print("使用GraphFrame检测循环闭环交易模式...")
    
    detected_accounts = []
    detected_transactions = []
    
    # 使用GraphFrame的find方法查找三角形循环模式: (a)-[e1]->(b); (b)-[e2]->(c); (c)-[e3]->(a)
    print("查找三角形循环模式...")
    triangles = graph.find("(a)-[e1]->(b); (b)-[e2]->(c); (c)-[e3]->(a)") \
        .filter("e1.transaction_date = e2.transaction_date AND e2.transaction_date = e3.transaction_date") \
        .filter("e1.amount = e2.amount AND e2.amount = e3.amount") \
        .filter("a.id != b.id AND b.id != c.id AND c.id != a.id")
    
    triangle_results = triangles.collect()
    print(f"找到 {len(triangle_results)} 个三角形循环")
    
    for result in triangle_results:
        # 获取账户和交易信息
        accounts = [result['a']['id'], result['b']['id'], result['c']['id']]
        transactions = [result['e1']['transaction_id'], result['e2']['transaction_id'], result['e3']['transaction_id']]
        
        # 确定洗钱者（第一个发起交易的账户，基于时间戳）
        trans_times = [
            (result['e1']['value_date'], result['a']['id']),
            (result['e2']['value_date'], result['b']['id']),
            (result['e3']['value_date'], result['c']['id'])
        ]
        trans_times.sort(key=lambda x: x[0])
        money_launderer = trans_times[0][1]
        
        # 标记账户
        for account in accounts:
            role = "洗钱者" if account == money_launderer else "协助者"
            detected_accounts.append({
                "account_id": account,
                "detected_suspicious": True,
                "detected_suspicious_type": "循环闭环交易",
                "suspicious_role": role
            })
        
        # 标记交易
        for trans_id in transactions:
            detected_transactions.append({
                "transaction_id": trans_id,
                "detected_suspicious": True,
                "detected_suspicious_type": "循环闭环交易"
            })
    
    # 查找四边形循环模式: (a)-[e1]->(b); (b)-[e2]->(c); (c)-[e3]->(d); (d)-[e4]->(a)
    print("查找四边形循环模式...")
    squares = graph.find("(a)-[e1]->(b); (b)-[e2]->(c); (c)-[e3]->(d); (d)-[e4]->(a)") \
        .filter("e1.transaction_date = e2.transaction_date AND e2.transaction_date = e3.transaction_date AND e3.transaction_date = e4.transaction_date") \
        .filter("e1.amount = e2.amount AND e2.amount = e3.amount AND e3.amount = e4.amount") \
        .filter("a.id != b.id AND b.id != c.id AND c.id != d.id AND d.id != a.id AND a.id != c.id AND b.id != d.id")
    
    square_results = squares.collect()
    print(f"找到 {len(square_results)} 个四边形循环")
    
    for result in square_results:
        # 获取账户和交易信息
        accounts = [result['a']['id'], result['b']['id'], result['c']['id'], result['d']['id']]
        transactions = [result['e1']['transaction_id'], result['e2']['transaction_id'], 
                       result['e3']['transaction_id'], result['e4']['transaction_id']]
        
        # 确定洗钱者
        trans_times = [
            (result['e1']['value_date'], result['a']['id']),
            (result['e2']['value_date'], result['b']['id']),
            (result['e3']['value_date'], result['c']['id']),
            (result['e4']['value_date'], result['d']['id'])
        ]
        trans_times.sort(key=lambda x: x[0])
        money_launderer = trans_times[0][1]
        
        # 标记账户
        for account in accounts:
            role = "洗钱者" if account == money_launderer else "协助者"
            detected_accounts.append({
                "account_id": account,
                "detected_suspicious": True,
                "detected_suspicious_type": "循环闭环交易",
                "suspicious_role": role
            })
        
        # 标记交易
        for trans_id in transactions:
            detected_transactions.append({
                "transaction_id": trans_id,
                "detected_suspicious": True,
                "detected_suspicious_type": "循环闭环交易"
            })
    
    return detected_accounts, detected_transactions

def detect_star_patterns_with_graphframe(spark, graph):
    """使用GraphFrame检测星型拆分入账模式"""
    print("使用GraphFrame检测星型拆分入账模式...")
    
    detected_accounts = []
    detected_transactions = []
    
    # 使用GraphFrame查找星型模式: 多个账户在同一天向同一个账户转账小额资金
    # 查找5个源账户向1个目标账户的模式
    star_pattern = graph.find("(a1)-[e1]->(center); (a2)-[e2]->(center); (a3)-[e3]->(center); (a4)-[e4]->(center); (a5)-[e5]->(center)") \
        .filter("e1.transaction_date = e2.transaction_date AND e2.transaction_date = e3.transaction_date AND e3.transaction_date = e4.transaction_date AND e4.transaction_date = e5.transaction_date") \
        .filter("e1.amount < 10000 AND e2.amount < 10000 AND e3.amount < 10000 AND e4.amount < 10000 AND e5.amount < 10000") \
        .filter("a1.id != a2.id AND a1.id != a3.id AND a1.id != a4.id AND a1.id != a5.id") \
        .filter("a2.id != a3.id AND a2.id != a4.id AND a2.id != a5.id") \
        .filter("a3.id != a4.id AND a3.id != a5.id") \
        .filter("a4.id != a5.id") \
        .filter("a1.id != center.id AND a2.id != center.id AND a3.id != center.id AND a4.id != center.id AND a5.id != center.id")
    
    star_results = star_pattern.collect()
    print(f"找到 {len(star_results)} 个星型拆分模式")
    
    for result in star_results:
        # 中心账户（洗钱者）
        center_account = result['center']['id']
        
        # 源账户（协助者）
        source_accounts = [
            result['a1']['id'], result['a2']['id'], result['a3']['id'], 
            result['a4']['id'], result['a5']['id']
        ]
        
        # 相关交易
        transactions = [
            result['e1']['transaction_id'], result['e2']['transaction_id'], 
            result['e3']['transaction_id'], result['e4']['transaction_id'], 
            result['e5']['transaction_id']
        ]
        
        # 标记中心账户为洗钱者
        detected_accounts.append({
            "account_id": center_account,
            "detected_suspicious": True,
            "detected_suspicious_type": "星型拆分入账",
            "suspicious_role": "洗钱者"
        })
        
        # 标记源账户为协助者
        for src_account in source_accounts:
            detected_accounts.append({
                "account_id": src_account,
                "detected_suspicious": True,
                "detected_suspicious_type": "星型拆分入账",
                "suspicious_role": "协助者"
            })
        
        # 标记相关交易
        for trans_id in transactions:
            detected_transactions.append({
                "transaction_id": trans_id,
                "detected_suspicious": True,
                "detected_suspicious_type": "星型拆分入账"
            })
    
    return detected_accounts, detected_transactions

def detect_cross_border_patterns_with_graphframe(spark, graph):
    """使用GraphFrame检测跨境多层转账模式"""
    print("使用GraphFrame检测跨境多层转账模式...")
    
    detected_accounts = []
    detected_transactions = []
    
    # 定义高危国家
    high_risk_countries = ["高危国1", "高危国2", "高危国3"]
    
    # 查找3层转账到高危国家的模式: (a)-[e1]->(b); (b)-[e2]->(c); (c)-[e3]->(target)
    # 其中target在高危国家
    three_layer_pattern = graph.find("(a)-[e1]->(b); (b)-[e2]->(c); (c)-[e3]->(target)") \
        .filter("e1.transaction_date = e2.transaction_date AND e2.transaction_date = e3.transaction_date") \
        .filter(col("target.country").isin(high_risk_countries)) \
        .filter("a.id != b.id AND b.id != c.id AND c.id != target.id AND a.id != c.id AND a.id != target.id AND b.id != target.id")
    
    three_layer_results = three_layer_pattern.collect()
    print(f"找到 {len(three_layer_results)} 个3层跨境转账模式")
    
    # 按源账户分组，查找有多条路径的情况
    source_paths = {}
    for result in three_layer_results:
        source_account = result['a']['id']
        target_account = result['target']['id']
        path_key = f"{source_account}->{target_account}"
        
        if path_key not in source_paths:
            source_paths[path_key] = []
        
        source_paths[path_key].append({
            'accounts': [result['a']['id'], result['b']['id'], result['c']['id'], result['target']['id']],
            'transactions': [result['e1']['transaction_id'], result['e2']['transaction_id'], result['e3']['transaction_id']]
        })
    
    # 查找4层转账到高危国家的模式: (a)-[e1]->(b); (b)-[e2]->(c); (c)-[e3]->(d); (d)-[e4]->(target)
    four_layer_pattern = graph.find("(a)-[e1]->(b); (b)-[e2]->(c); (c)-[e3]->(d); (d)-[e4]->(target)") \
        .filter("e1.transaction_date = e2.transaction_date AND e2.transaction_date = e3.transaction_date AND e3.transaction_date = e4.transaction_date") \
        .filter(col("target.country").isin(high_risk_countries)) \
        .filter("a.id != b.id AND b.id != c.id AND c.id != d.id AND d.id != target.id") \
        .filter("a.id != c.id AND a.id != d.id AND a.id != target.id") \
        .filter("b.id != d.id AND b.id != target.id") \
        .filter("c.id != target.id")
    
    four_layer_results = four_layer_pattern.collect()
    print(f"找到 {len(four_layer_results)} 个4层跨境转账模式")
    
    for result in four_layer_results:
        source_account = result['a']['id']
        target_account = result['target']['id']
        path_key = f"{source_account}->{target_account}"
        
        if path_key not in source_paths:
            source_paths[path_key] = []
        
        source_paths[path_key].append({
            'accounts': [result['a']['id'], result['b']['id'], result['c']['id'], result['d']['id'], result['target']['id']],
            'transactions': [result['e1']['transaction_id'], result['e2']['transaction_id'], 
                           result['e3']['transaction_id'], result['e4']['transaction_id']]
        })
    
    # 处理检测到的模式
    for path_key, paths in source_paths.items():
        if len(paths) >= 1:  # 只要有多层转账路径就标记为可疑
            all_accounts = set()
            all_transactions = set()
            
            for path_info in paths:
                all_accounts.update(path_info['accounts'])
                all_transactions.update(path_info['transactions'])
            
            # 确定角色
            source_account = path_key.split('->')[0]
            target_account = path_key.split('->')[1]
            
            # 标记账户
            for account in all_accounts:
                if account == target_account:
                    role = "洗钱者"
                else:
                    role = "协助者"
                
                detected_accounts.append({
                    "account_id": account,
                    "detected_suspicious": True,
                    "detected_suspicious_type": "跨境多层转账",
                    "suspicious_role": role
                })
            
            # 标记交易
            for trans_id in all_transactions:
                detected_transactions.append({
                    "transaction_id": trans_id,
                    "detected_suspicious": True,
                    "detected_suspicious_type": "跨境多层转账"
                })
    
    return detected_accounts, detected_transactions

def save_results(spark, accounts_df, transactions_df, detected_accounts_list, detected_transactions_list):
    """保存分析结果"""
    print("保存分析结果...")
    
    # 确保result目录存在
    os.makedirs('result', exist_ok=True)
    
    # 处理检测到的账户 - 去重
    detected_accounts_dict = {}
    for item in detected_accounts_list:
        account_id = item["account_id"]
        if account_id not in detected_accounts_dict:
            detected_accounts_dict[account_id] = item
    
    # 处理检测到的交易 - 去重
    detected_transactions_dict = {}
    for item in detected_transactions_list:
        trans_id = item["transaction_id"]
        if trans_id not in detected_transactions_dict:
            detected_transactions_dict[trans_id] = item
    
    # 转换为Pandas DataFrame并保存账户结果
    accounts_pandas = accounts_df.toPandas()
    accounts_pandas["detected_suspicious"] = False
    accounts_pandas["detected_suspicious_type"] = ""
    accounts_pandas["detected_suspicious_role"] = ""
    
    for account_id, detection in detected_accounts_dict.items():
        mask = accounts_pandas["account_id"] == account_id
        accounts_pandas.loc[mask, "detected_suspicious"] = detection["detected_suspicious"]
        accounts_pandas.loc[mask, "detected_suspicious_type"] = detection["detected_suspicious_type"]
        accounts_pandas.loc[mask, "detected_suspicious_role"] = detection["suspicious_role"]
    
    accounts_pandas.to_csv("result/detected_account.csv", index=False, encoding='utf-8-sig')
    
    # 转换为Pandas DataFrame并保存交易结果
    transactions_pandas = transactions_df.toPandas()
    transactions_pandas["detected_suspicious"] = False
    transactions_pandas["detected_suspicious_type"] = ""
    
    for trans_id, detection in detected_transactions_dict.items():
        mask = transactions_pandas["transaction_id"] == trans_id
        transactions_pandas.loc[mask, "detected_suspicious"] = detection["detected_suspicious"]
        transactions_pandas.loc[mask, "detected_suspicious_type"] = detection["detected_suspicious_type"]
    
    transactions_pandas.to_csv("result/detected_transaction.csv", index=False, encoding='utf-8-sig')
    
    # 输出统计信息
    detected_account_count = len(detected_accounts_dict)
    detected_transaction_count = len(detected_transactions_dict)
    
    print(f"检测完成！")
    print(f"检测到可疑账户: {detected_account_count} 个")
    print(f"检测到可疑交易: {detected_transaction_count} 笔")
    print(f"结果已保存到 result/ 目录")
    
    # 按模式统计
    pattern_stats = {}
    for detection in detected_accounts_dict.values():
        pattern = detection["detected_suspicious_type"]
        if pattern not in pattern_stats:
            pattern_stats[pattern] = 0
        pattern_stats[pattern] += 1
    
    print(f"\n按模式统计:")
    for pattern, count in pattern_stats.items():
        print(f"  {pattern}: {count} 个账户")

def main():
    """主函数"""
    print("=== AML模式分析开始 (使用GraphFrame模式匹配) ===")
    
    # 创建Spark会话
    spark = create_spark_session()
    
    try:
        # 加载数据
        accounts_df, transactions_df = load_data(spark)
        
        # 创建图
        graph = create_graph(spark, accounts_df, transactions_df)
        
        # 检测各种洗钱模式
        all_detected_accounts = []
        all_detected_transactions = []
        
        # 1. 使用GraphFrame检测循环闭环交易
        print("\n--- 使用GraphFrame检测循环闭环交易 ---")
        circular_accounts, circular_transactions = detect_circular_patterns_with_graphframe(spark, graph)
        all_detected_accounts.extend(circular_accounts)
        all_detected_transactions.extend(circular_transactions)
        print(f"循环闭环交易检测完成: {len(circular_accounts)} 个账户, {len(circular_transactions)} 笔交易")
        
        # 2. 使用GraphFrame检测星型拆分入账
        print("\n--- 使用GraphFrame检测星型拆分入账 ---")
        star_accounts, star_transactions = detect_star_patterns_with_graphframe(spark, graph)
        all_detected_accounts.extend(star_accounts)
        all_detected_transactions.extend(star_transactions)
        print(f"星型拆分入账检测完成: {len(star_accounts)} 个账户, {len(star_transactions)} 笔交易")
        
        # 3. 使用GraphFrame检测跨境多层转账
        print("\n--- 使用GraphFrame检测跨境多层转账 ---")
        cross_border_accounts, cross_border_transactions = detect_cross_border_patterns_with_graphframe(spark, graph)
        all_detected_accounts.extend(cross_border_accounts)
        all_detected_transactions.extend(cross_border_transactions)
        print(f"跨境多层转账检测完成: {len(cross_border_accounts)} 个账户, {len(cross_border_transactions)} 笔交易")
        
        # 保存结果
        save_results(spark, accounts_df, transactions_df, all_detected_accounts, all_detected_transactions)
        
    except Exception as e:
        print(f"分析过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # 关闭Spark会话
        spark.stop()
    
    print("=== AML模式分析完成 ===")

if __name__ == "__main__":
    main() 