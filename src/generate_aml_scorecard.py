#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AML风险评分系统
输入：result/detected_account.csv, result/detected_transaction.csv
输出：result/high_risk_accounts.csv, result/risk_alert_report.md
"""

import pandas as pd
import numpy as np
from collections import defaultdict
import os
from datetime import datetime

def load_data():
    """加载检测结果数据"""
    print("加载检测结果数据...")
    
    # 加载账户检测结果
    accounts_df = pd.read_csv('result/detected_account.csv')
    
    # 加载交易检测结果
    transactions_df = pd.read_csv('result/detected_transaction.csv')
    
    print(f"账户数据: {len(accounts_df)} 条")
    print(f"交易数据: {len(transactions_df)} 条")
    
    return accounts_df, transactions_df

def calculate_risk_score(accounts_df, transactions_df):
    """计算账户风险评分"""
    print("计算账户风险评分...")
    
    # 定义高危国家
    high_risk_countries = ["高危国1", "高危国2", "高危国3"]
    
    # 初始化评分结果
    risk_scores = []
    
    for _, account in accounts_df.iterrows():
        account_id = account['account_id']
        account_country = account['country']
        
        # 初始化评分和评分详情
        total_score = 0
        score_details = []
        
        # 规则1: 如果账户属于高危国家，加40分
        if account_country in high_risk_countries:
            total_score += 40
            score_details.append(f"高危国家账户: +40分")
        
        # 获取该账户相关的所有交易
        account_transactions = transactions_df[
            (transactions_df['src_account'] == account_id) | 
            (transactions_df['dst_account'] == account_id)
        ].copy()
        
        # 规则2: 如果账户不属于高危国家但是有交易涉及另一个账户是高危国家的，每有一条加10分，最高40分
        if account_country not in high_risk_countries:
            high_risk_trans_count = 0
            for _, trans in account_transactions.iterrows():
                other_country = None
                if trans['src_account'] == account_id:
                    # 当前账户是发送方，检查接收方国家
                    other_account = accounts_df[accounts_df['account_id'] == trans['dst_account']]
                    if not other_account.empty:
                        other_country = other_account.iloc[0]['country']
                else:
                    # 当前账户是接收方，检查发送方国家
                    other_account = accounts_df[accounts_df['account_id'] == trans['src_account']]
                    if not other_account.empty:
                        other_country = other_account.iloc[0]['country']
                
                if other_country in high_risk_countries:
                    high_risk_trans_count += 1
            
            high_risk_score = min(high_risk_trans_count * 10, 40)
            if high_risk_score > 0:
                total_score += high_risk_score
                score_details.append(f"涉及高危国家交易 {high_risk_trans_count} 笔: +{high_risk_score}分")
        
        # 规则3: 多国交易评分
        # 统计与不同国家的交易金额
        country_amounts = defaultdict(float)
        for _, trans in account_transactions.iterrows():
            other_country = None
            if trans['src_account'] == account_id:
                other_account = accounts_df[accounts_df['account_id'] == trans['dst_account']]
                if not other_account.empty:
                    other_country = other_account.iloc[0]['country']
            else:
                other_account = accounts_df[accounts_df['account_id'] == trans['src_account']]
                if not other_account.empty:
                    other_country = other_account.iloc[0]['country']
            
            if other_country and other_country != account_country:
                country_amounts[other_country] += trans['amount']
        
        # 计算符合条件的国家数量
        countries_over_50k = sum(1 for amount in country_amounts.values() if amount > 50000)
        countries_over_100k = sum(1 for amount in country_amounts.values() if amount > 100000)
        
        if countries_over_100k > 6:
            total_score += 40
            score_details.append(f"与{countries_over_100k}个国家交易超过10万: +40分")
        elif countries_over_50k > 4:
            total_score += 20
            score_details.append(f"与{countries_over_50k}个国家交易超过5万: +20分")
        
        # 规则4: 单日高频交易评分
        # 按日期分组统计交易
        account_transactions['value_date'] = pd.to_datetime(account_transactions['value_date'])
        daily_stats = account_transactions.groupby(account_transactions['value_date'].dt.date).agg({
            'transaction_id': 'count',
            'amount': 'sum'
        }).reset_index()
        daily_stats.columns = ['date', 'trans_count', 'total_amount']
        
        # 检查单日交易条件
        high_freq_days = daily_stats[
            ((daily_stats['trans_count'] > 20) & (daily_stats['total_amount'] > 100000)) |
            ((daily_stats['trans_count'] > 10) & (daily_stats['total_amount'] > 50000))
        ]
        
        if not high_freq_days.empty:
            max_day = high_freq_days.loc[high_freq_days['total_amount'].idxmax()]
            if max_day['trans_count'] > 20 and max_day['total_amount'] > 100000:
                total_score += 30
                score_details.append(f"单日交易{max_day['trans_count']}笔金额{max_day['total_amount']:,.0f}: +30分")
            elif max_day['trans_count'] > 10 and max_day['total_amount'] > 50000:
                total_score += 15
                score_details.append(f"单日交易{max_day['trans_count']}笔金额{max_day['total_amount']:,.0f}: +15分")
        
        # 规则5: 洗钱检测结果评分
        if account.get('detected_suspicious', False):
            role = account.get('detected_suspicious_role', '')
            suspicious_type = account.get('detected_suspicious_type', '')
            
            if role == '洗钱者':
                total_score += 100
                score_details.append(f"检测为洗钱者({suspicious_type}): +100分")
            elif role == '协助者':
                total_score += 50
                score_details.append(f"检测为协助者({suspicious_type}): +50分")
        
        # 保存评分结果
        risk_scores.append({
            'account_id': account_id,
            'owner_name': account['owner_name'],
            'country': account_country,
            'total_score': total_score,
            'score_details': '; '.join(score_details) if score_details else '无风险因子',
            'detected_suspicious': account.get('detected_suspicious', False),
            'detected_suspicious_type': account.get('detected_suspicious_type', ''),
            'detected_suspicious_role': account.get('detected_suspicious_role', ''),
            'registration_date': account['registration_date']
        })
    
    return pd.DataFrame(risk_scores)

def get_account_counterparties(account_id, transactions_df, accounts_df):
    """获取账户的交易对手方信息"""
    counterparties = []
    
    # 获取该账户的所有交易
    account_transactions = transactions_df[
        (transactions_df['src_account'] == account_id) | 
        (transactions_df['dst_account'] == account_id)
    ]
    
    for _, trans in account_transactions.iterrows():
        if trans['src_account'] == account_id:
            # 当前账户是发送方
            counterparty_id = trans['dst_account']
            direction = "转出至"
        else:
            # 当前账户是接收方
            counterparty_id = trans['src_account']
            direction = "接收自"
        
        # 获取对手方信息
        counterparty_info = accounts_df[accounts_df['account_id'] == counterparty_id]
        if not counterparty_info.empty:
            counterparty = counterparty_info.iloc[0]
            counterparties.append({
                'direction': direction,
                'account_id': counterparty_id,
                'owner_name': counterparty['owner_name'],
                'country': counterparty['country'],
                'amount': trans['amount'],
                'currency': trans['currency'],
                'date': trans['value_date'],
                'is_suspicious': trans.get('detected_suspicious', False),
                'suspicious_type': trans.get('detected_suspicious_type', '')
            })
    
    return counterparties

def generate_high_risk_csv(risk_scores_df):
    """生成高风险账户CSV文件"""
    print("生成高风险账户CSV文件...")
    
    # 筛选评分超过80的账户
    high_risk_accounts = risk_scores_df[risk_scores_df['total_score'] > 80].copy()
    
    # 按分数从大到小排序
    high_risk_accounts = high_risk_accounts.sort_values('total_score', ascending=False)
    
    # 确保result目录存在
    os.makedirs('result', exist_ok=True)
    
    # 保存CSV文件
    high_risk_accounts.to_csv('result/high_risk_accounts.csv', index=False, encoding='utf-8-sig')
    
    print(f"高风险账户CSV文件已保存: {len(high_risk_accounts)} 个账户")
    return high_risk_accounts

def generate_alert_report(high_risk_accounts, transactions_df, accounts_df):
    """生成预警报告"""
    print("生成预警报告...")
    
    report = []
    report.append("# AML风险预警报告")
    report.append("")
    report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**预警账户数量**: {len(high_risk_accounts)}")
    report.append("")
    report.append("## 预警说明")
    report.append("")
    report.append("根据以下评分规则对账户进行风险评估：")
    report.append("- 高危国家账户：+40分")
    report.append("- 涉及高危国家交易：每笔+10分（最高40分）")
    report.append("- 多国交易：与4+国家交易超5万+20分，与6+国家交易超10万+40分")
    report.append("- 高频交易：单日10+笔超5万+15分，单日20+笔超10万+30分")
    report.append("- 洗钱检测：洗钱者+100分，协助者+50分")
    report.append("")
    report.append("**预警阈值**: 80分以上")
    report.append("")
    
    # 按分数分组统计
    score_ranges = [
        (100, float('inf'), "高风险"),
        (80, 99, "中风险")
    ]
    
    report.append("## 风险等级分布")
    report.append("")
    report.append("| 风险等级 | 分数范围 | 账户数量 |")
    report.append("|----------|----------|----------|")
    
    for min_score, max_score, level in score_ranges:
        if max_score == float('inf'):
            count = len(high_risk_accounts[high_risk_accounts['total_score'] >= min_score])
            range_str = f"{min_score}分以上"
        else:
            count = len(high_risk_accounts[
                (high_risk_accounts['total_score'] >= min_score) & 
                (high_risk_accounts['total_score'] <= max_score)
            ])
            range_str = f"{min_score}-{max_score}分"
        
        report.append(f"| {level} | {range_str} | {count} |")
    
    report.append("")
    
    # 详细预警信息
    report.append("## 详细预警信息")
    report.append("")
    
    for idx, (_, account) in enumerate(high_risk_accounts.iterrows(), 1):
        account_id = account['account_id']
        
        # 确定风险等级
        score = account['total_score']
        risk_level = "中风险"
        for min_score, max_score, level in score_ranges:
            if max_score == float('inf'):
                if score >= min_score:
                    risk_level = level
                    break
            else:
                if min_score <= score <= max_score:
                    risk_level = level
                    break
        
        report.append(f"### {idx}. 账户 {account_id} - {account['owner_name']} ({risk_level})")
        report.append("")
        report.append(f"**风险评分**: {score}分")
        report.append(f"**账户信息**: {account['owner_name']} | {account['country']} | 注册日期: {account['registration_date']}")
        
        if account['detected_suspicious']:
            report.append(f"**检测结果**: {account['detected_suspicious_type']} - {account['detected_suspicious_role']}")
        
        report.append("")
        report.append("**评分构成**:")
        score_items = account['score_details'].split('; ')
        for item in score_items:
            if item.strip():
                report.append(f"- {item}")
        
        report.append("")
        
        # 获取交易对手方信息
        counterparties = get_account_counterparties(account_id, transactions_df, accounts_df)
        
        if counterparties:
            report.append("**主要交易对手方**:")
            report.append("")
            
            # 按金额排序，显示前10个
            counterparties_sorted = sorted(counterparties, key=lambda x: x['amount'], reverse=True)[:10]
            
            report.append("| 方向 | 对手方 | 国家 | 金额 | 日期 | 可疑标记 |")
            report.append("|------|--------|------|------|------|----------|")
            
            for cp in counterparties_sorted:
                suspicious_mark = "🚨" if cp['is_suspicious'] else ""
                report.append(f"| {cp['direction']} | {cp['owner_name']} ({cp['account_id']}) | {cp['country']} | {cp['amount']:,.0f} {cp['currency']} | {cp['date'][:10]} | {suspicious_mark} |")
            
            if len(counterparties) > 10:
                report.append(f"*（显示前10个，共{len(counterparties)}个交易对手方）*")
        
        report.append("")
        report.append("---")
        report.append("")
    
    # 保存报告
    report_content = "\n".join(report)
    with open('result/risk_alert_report.md', 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print("预警报告已保存到 result/risk_alert_report.md")

def main():
    """主函数"""
    print("=== AML风险评分系统开始 ===")
    
    try:
        # 加载数据
        accounts_df, transactions_df = load_data()
        
        # 计算风险评分
        risk_scores_df = calculate_risk_score(accounts_df, transactions_df)
        
        # 生成高风险账户CSV
        high_risk_accounts = generate_high_risk_csv(risk_scores_df)
        
        # 生成预警报告
        generate_alert_report(high_risk_accounts, transactions_df, accounts_df)
        
        # 输出统计信息
        print(f"\n=== 评分统计 ===")
        print(f"总账户数: {len(risk_scores_df)}")
        print(f"高风险账户数 (>80分): {len(high_risk_accounts)}")
        print(f"最高分: {risk_scores_df['total_score'].max()}")
        print(f"平均分: {risk_scores_df['total_score'].mean():.2f}")
        
        # 按分数段统计
        score_ranges = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100), (100, float('inf'))]
        for min_score, max_score in score_ranges:
            if max_score == float('inf'):
                count = len(risk_scores_df[risk_scores_df['total_score'] >= min_score])
                print(f"{min_score}分以上: {count} 个账户")
            else:
                count = len(risk_scores_df[
                    (risk_scores_df['total_score'] >= min_score) & 
                    (risk_scores_df['total_score'] < max_score)
                ])
                print(f"{min_score}-{max_score}分: {count} 个账户")
        
    except Exception as e:
        print(f"评分过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("=== AML风险评分系统完成 ===")

if __name__ == "__main__":
    main() 