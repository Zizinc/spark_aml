#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AML检测结果验证脚本
输入：result/detected_account.csv, result/detected_transaction.csv
输出：result/verification_report.md
"""

import pandas as pd
import numpy as np
from collections import defaultdict
import os

def load_detection_results():
    """加载检测结果数据"""
    print("加载检测结果数据...")
    
    # 加载账户检测结果
    accounts_df = pd.read_csv('result/detected_account.csv')
    
    # 加载交易检测结果
    transactions_df = pd.read_csv('result/detected_transaction.csv')
    
    print(f"账户数据: {len(accounts_df)} 条")
    print(f"交易数据: {len(transactions_df)} 条")
    
    return accounts_df, transactions_df

def calculate_confusion_matrix(true_labels, predicted_labels):
    """计算混淆矩阵"""
    tp = sum((t == True and p == True) for t, p in zip(true_labels, predicted_labels))
    tn = sum((t == False and p == False) for t, p in zip(true_labels, predicted_labels))
    fp = sum((t == False and p == True) for t, p in zip(true_labels, predicted_labels))
    fn = sum((t == True and p == False) for t, p in zip(true_labels, predicted_labels))
    
    return tp, tn, fp, fn

def calculate_metrics(tp, tn, fp, fn):
    """计算评估指标"""
    # 精确率 (Precision)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    
    # 召回率 (Recall)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    
    # F1分数
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    # 准确率 (Accuracy)
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0
    
    return precision, recall, f1_score, accuracy

def analyze_account_detection(accounts_df):
    """分析账户检测结果"""
    print("分析账户检测结果...")
    
    results = {}
    
    # 整体检测结果
    true_suspicious = accounts_df['is_suspicious'].fillna(False)
    detected_suspicious = accounts_df['detected_suspicious'].fillna(False)
    
    tp, tn, fp, fn = calculate_confusion_matrix(true_suspicious, detected_suspicious)
    precision, recall, f1_score, accuracy = calculate_metrics(tp, tn, fp, fn)
    
    results['overall'] = {
        'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn,
        'precision': precision, 'recall': recall, 'f1_score': f1_score, 'accuracy': accuracy
    }
    
    # 按洗钱类型分析
    suspicious_accounts = accounts_df[accounts_df['is_suspicious'] == True].copy()
    
    # 获取所有真实的洗钱类型
    true_types = set()
    for suspicious_type in suspicious_accounts['suspicious_type'].dropna():
        if '_' in suspicious_type:
            base_type = suspicious_type.split('_')[0]
            true_types.add(base_type)
        else:
            true_types.add(suspicious_type)
    
    # 映射检测类型到真实类型
    type_mapping = {
        '循环闭环交易': '循环闭环交易',
        '星型拆分入账': '星型拆分入账', 
        '跨境多层转账': '跨境多层转账'
    }
    
    for true_type in true_types:
        detected_type = type_mapping.get(true_type, true_type)
        
        # 计算该类型的检测结果
        true_labels = []
        predicted_labels = []
        
        for _, row in accounts_df.iterrows():
            # 真实标签
            is_true_type = False
            if pd.notna(row['suspicious_type']) and true_type in row['suspicious_type']:
                is_true_type = True
            
            # 预测标签
            is_detected_type = False
            if pd.notna(row['detected_suspicious_type']) and detected_type in row['detected_suspicious_type']:
                is_detected_type = True
            
            true_labels.append(is_true_type)
            predicted_labels.append(is_detected_type)
        
        tp, tn, fp, fn = calculate_confusion_matrix(true_labels, predicted_labels)
        precision, recall, f1_score, accuracy = calculate_metrics(tp, tn, fp, fn)
        
        results[true_type] = {
            'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn,
            'precision': precision, 'recall': recall, 'f1_score': f1_score, 'accuracy': accuracy
        }
    
    return results

def analyze_transaction_detection(transactions_df):
    """分析交易检测结果"""
    print("分析交易检测结果...")
    
    results = {}
    
    # 整体检测结果
    true_suspicious = transactions_df['is_suspicious'].fillna(False)
    detected_suspicious = transactions_df['detected_suspicious'].fillna(False)
    
    tp, tn, fp, fn = calculate_confusion_matrix(true_suspicious, detected_suspicious)
    precision, recall, f1_score, accuracy = calculate_metrics(tp, tn, fp, fn)
    
    results['overall'] = {
        'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn,
        'precision': precision, 'recall': recall, 'f1_score': f1_score, 'accuracy': accuracy
    }
    
    # 按洗钱类型分析
    suspicious_transactions = transactions_df[transactions_df['is_suspicious'] == True].copy()
    
    # 获取所有真实的洗钱类型
    true_types = set()
    for suspicious_type in suspicious_transactions['suspicious_type'].dropna():
        if '_' in suspicious_type:
            base_type = suspicious_type.split('_')[0]
            true_types.add(base_type)
        else:
            true_types.add(suspicious_type)
    
    # 映射检测类型到真实类型
    type_mapping = {
        '循环闭环交易': '循环闭环交易',
        '星型拆分入账': '星型拆分入账',
        '跨境多层转账': '跨境多层转账'
    }
    
    for true_type in true_types:
        detected_type = type_mapping.get(true_type, true_type)
        
        # 计算该类型的检测结果
        true_labels = []
        predicted_labels = []
        
        for _, row in transactions_df.iterrows():
            # 真实标签
            is_true_type = False
            if pd.notna(row['suspicious_type']) and true_type in row['suspicious_type']:
                is_true_type = True
            
            # 预测标签
            is_detected_type = False
            if pd.notna(row['detected_suspicious_type']) and detected_type in row['detected_suspicious_type']:
                is_detected_type = True
            
            true_labels.append(is_true_type)
            predicted_labels.append(is_detected_type)
        
        tp, tn, fp, fn = calculate_confusion_matrix(true_labels, predicted_labels)
        precision, recall, f1_score, accuracy = calculate_metrics(tp, tn, fp, fn)
        
        results[true_type] = {
            'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn,
            'precision': precision, 'recall': recall, 'f1_score': f1_score, 'accuracy': accuracy
        }
    
    return results

def generate_markdown_report(account_results, transaction_results, accounts_df, transactions_df):
    """生成Markdown格式的验证报告"""
    print("生成验证报告...")
    
    report = []
    report.append("# AML检测结果验证报告")
    report.append("")
    report.append("## 概述")
    report.append("")
    report.append(f"- **账户总数**: {len(accounts_df)}")
    report.append(f"- **交易总数**: {len(transactions_df)}")
    report.append(f"- **真实可疑账户数**: {accounts_df['is_suspicious'].sum()}")
    report.append(f"- **检测到可疑账户数**: {accounts_df['detected_suspicious'].sum()}")
    report.append(f"- **真实可疑交易数**: {transactions_df['is_suspicious'].sum()}")
    report.append(f"- **检测到可疑交易数**: {transactions_df['detected_suspicious'].sum()}")
    report.append("")
    
    # 账户检测结果
    report.append("## 账户检测结果分析")
    report.append("")
    
    # 整体结果
    overall = account_results['overall']
    report.append("### 整体检测性能")
    report.append("")
    report.append("| 指标 | 值 |")
    report.append("|------|-----|")
    report.append(f"| True Positive (TP) | {overall['tp']} |")
    report.append(f"| True Negative (TN) | {overall['tn']} |")
    report.append(f"| False Positive (FP) | {overall['fp']} |")
    report.append(f"| False Negative (FN) | {overall['fn']} |")
    report.append(f"| 精确率 (Precision) | {overall['precision']:.4f} |")
    report.append(f"| 召回率 (Recall) | {overall['recall']:.4f} |")
    report.append(f"| F1分数 | {overall['f1_score']:.4f} |")
    report.append(f"| 准确率 (Accuracy) | {overall['accuracy']:.4f} |")
    report.append("")
    
    # 按类型分析
    report.append("### 按洗钱类型分析")
    report.append("")
    report.append("| 洗钱类型 | TP | TN | FP | FN | 精确率 | 召回率 | F1分数 | 准确率 |")
    report.append("|----------|----|----|----|----|--------|--------|--------|--------|")
    
    for type_name, metrics in account_results.items():
        if type_name != 'overall':
            report.append(f"| {type_name} | {metrics['tp']} | {metrics['tn']} | {metrics['fp']} | {metrics['fn']} | {metrics['precision']:.4f} | {metrics['recall']:.4f} | {metrics['f1_score']:.4f} | {metrics['accuracy']:.4f} |")
    
    report.append("")
    
    # 交易检测结果
    report.append("## 交易检测结果分析")
    report.append("")
    
    # 整体结果
    overall = transaction_results['overall']
    report.append("### 整体检测性能")
    report.append("")
    report.append("| 指标 | 值 |")
    report.append("|------|-----|")
    report.append(f"| True Positive (TP) | {overall['tp']} |")
    report.append(f"| True Negative (TN) | {overall['tn']} |")
    report.append(f"| False Positive (FP) | {overall['fp']} |")
    report.append(f"| False Negative (FN) | {overall['fn']} |")
    report.append(f"| 精确率 (Precision) | {overall['precision']:.4f} |")
    report.append(f"| 召回率 (Recall) | {overall['recall']:.4f} |")
    report.append(f"| F1分数 | {overall['f1_score']:.4f} |")
    report.append(f"| 准确率 (Accuracy) | {overall['accuracy']:.4f} |")
    report.append("")
    
    # 按类型分析
    report.append("### 按洗钱类型分析")
    report.append("")
    report.append("| 洗钱类型 | TP | TN | FP | FN | 精确率 | 召回率 | F1分数 | 准确率 |")
    report.append("|----------|----|----|----|----|--------|--------|--------|--------|")
    
    for type_name, metrics in transaction_results.items():
        if type_name != 'overall':
            report.append(f"| {type_name} | {metrics['tp']} | {metrics['tn']} | {metrics['fp']} | {metrics['fn']} | {metrics['precision']:.4f} | {metrics['recall']:.4f} | {metrics['f1_score']:.4f} | {metrics['accuracy']:.4f} |")
    
    report.append("")
    
    # 详细分析
    report.append("## 详细分析")
    report.append("")
    
    # 账户角色分析
    report.append("### 账户角色检测分析")
    report.append("")
    
    # 统计角色检测准确性
    suspicious_accounts = accounts_df[accounts_df['is_suspicious'] == True].copy()
    role_correct = 0
    role_total = 0
    
    for _, row in suspicious_accounts.iterrows():
        if pd.notna(row['suspicious_role']) and pd.notna(row['detected_suspicious_role']):
            role_total += 1
            if row['suspicious_role'] == row['detected_suspicious_role']:
                role_correct += 1
    
    role_accuracy = role_correct / role_total if role_total > 0 else 0
    report.append(f"- **角色检测准确率**: {role_accuracy:.4f} ({role_correct}/{role_total})")
    report.append("")
    
    # 误检分析
    report.append("### 误检分析")
    report.append("")
    
    # False Positive分析
    fp_accounts = accounts_df[(accounts_df['is_suspicious'] == False) & (accounts_df['detected_suspicious'] == True)]
    report.append(f"- **误报账户数**: {len(fp_accounts)}")
    
    if len(fp_accounts) > 0:
        fp_types = fp_accounts['detected_suspicious_type'].value_counts()
        report.append("- **误报类型分布**:")
        for type_name, count in fp_types.items():
            report.append(f"  - {type_name}: {count}个")
    
    report.append("")
    
    # False Negative分析
    fn_accounts = accounts_df[(accounts_df['is_suspicious'] == True) & (accounts_df['detected_suspicious'] == False)]
    report.append(f"- **漏检账户数**: {len(fn_accounts)}")
    
    if len(fn_accounts) > 0:
        fn_types = fn_accounts['suspicious_type'].value_counts()
        report.append("- **漏检类型分布**:")
        for type_name, count in fn_types.items():
            report.append(f"  - {type_name}: {count}个")
    
    report.append("")
    
    # 结论
    report.append("## 结论")
    report.append("")
    
    overall_account_precision = account_results['overall']['precision']
    overall_account_recall = account_results['overall']['recall']
    overall_transaction_precision = transaction_results['overall']['precision']
    overall_transaction_recall = transaction_results['overall']['recall']
    
    report.append(f"1. **整体性能**: 账户检测精确率为{overall_account_precision:.4f}，召回率为{overall_account_recall:.4f}；交易检测精确率为{overall_transaction_precision:.4f}，召回率为{overall_transaction_recall:.4f}")
    report.append("")
    
    # 找出表现最好和最差的类型
    best_type = max(account_results.items(), key=lambda x: x[1]['f1_score'] if x[0] != 'overall' else 0)
    worst_type = min(account_results.items(), key=lambda x: x[1]['f1_score'] if x[0] != 'overall' else 1)
    
    if best_type[0] != 'overall':
        report.append(f"2. **最佳检测类型**: {best_type[0]}，F1分数为{best_type[1]['f1_score']:.4f}")
    
    if worst_type[0] != 'overall':
        report.append(f"3. **待改进类型**: {worst_type[0]}，F1分数为{worst_type[1]['f1_score']:.4f}")
    
    report.append("")
    report.append("4. **建议**: 基于以上分析结果，建议针对表现较差的洗钱类型优化检测算法，提高整体检测效果。")
    
    return "\n".join(report)

def save_report(report_content):
    """保存报告到文件"""
    # 确保result目录存在
    os.makedirs('result', exist_ok=True)
    
    # 保存报告
    with open('result/verification_report.md', 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print("验证报告已保存到 result/verification_report.md")

def main():
    """主函数"""
    print("=== AML检测结果验证开始 ===")
    
    try:
        # 加载数据
        accounts_df, transactions_df = load_detection_results()
        
        # 分析账户检测结果
        account_results = analyze_account_detection(accounts_df)
        
        # 分析交易检测结果
        transaction_results = analyze_transaction_detection(transactions_df)
        
        # 生成报告
        report_content = generate_markdown_report(account_results, transaction_results, accounts_df, transactions_df)
        
        # 保存报告
        save_report(report_content)
        
        # 输出关键指标
        print("\n=== 关键指标摘要 ===")
        print(f"账户检测 - 精确率: {account_results['overall']['precision']:.4f}, 召回率: {account_results['overall']['recall']:.4f}")
        print(f"交易检测 - 精确率: {transaction_results['overall']['precision']:.4f}, 召回率: {transaction_results['overall']['recall']:.4f}")
        
    except Exception as e:
        print(f"验证过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("=== AML检测结果验证完成 ===")

if __name__ == "__main__":
    main() 