#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AML数据生成脚本
输入：无
输出：生成4个CSV文件到mock_data目录
- account.csv: 所有账户信息
- transaction.csv: 所有交易信息  
- laundering_account.csv: 洗钱账户信息
- laundering_transaction.csv: 洗钱交易信息
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from faker import Faker
import os

# 设置随机种子确保结果可重现
random.seed(42)
np.random.seed(42)

# 初始化Faker，支持中文
fake = Faker(['zh_CN'])

class AMLDataGenerator:
    def __init__(self):
        self.accounts = []
        self.transactions = []
        self.laundering_accounts = []
        self.laundering_transactions = []
        self.account_counter = 10000000  # 8位数字账户ID起始值
        self.transaction_counter = 1
        self.suspicious_groups = {}  # 存储洗钱组别信息
        
    def generate_account_id(self):
        """生成8位数字账户ID"""
        account_id = self.account_counter
        self.account_counter += 1
        return str(account_id)
    
    def generate_transaction_id(self):
        """生成交易ID"""
        transaction_id = f"TXN{self.transaction_counter:06d}"
        self.transaction_counter += 1
        return transaction_id
    
    def generate_random_date(self, start_date, end_date):
        """生成指定范围内的随机日期"""
        time_between = end_date - start_date
        days_between = time_between.days
        random_days = random.randrange(days_between)
        return start_date + timedelta(days=random_days)
    
    def generate_normal_accounts(self, count=70):
        """生成正常账户"""
        countries = ['中国', '美国', '英国', '德国', '法国', '日本', '韩国', '新加坡']
        
        for _ in range(count):
            account = {
                'account_id': self.generate_account_id(),
                'owner_name': fake.name() if random.random() > 0.3 else fake.company(),
                'registration_date': self.generate_random_date(
                    datetime(2020, 1, 1), datetime(2023, 1, 1)
                ).strftime('%Y-%m-%d'),
                'country': random.choice(countries),
                'is_suspicious': False,
                'suspicious_type': '',
                'suspicious_role': ''
            }
            self.accounts.append(account)
    
    def generate_circular_laundering_accounts(self, groups=3):
        """生成循环闭环交易洗钱账户"""
        countries = ['中国', '美国', '英国', '德国', '法国']
        
        for group_id in range(1, groups + 1):
            group_name = f"循环闭环交易_{group_id}"
            group_accounts = []
            
            # 每组3-4个账户
            group_size = random.randint(3, 4)
            
            for i in range(group_size):
                role = '洗钱者' if i == 0 else '协助者'
                account = {
                    'account_id': self.generate_account_id(),
                    'owner_name': fake.name() if random.random() > 0.2 else fake.company(),
                    'registration_date': self.generate_random_date(
                        datetime(2020, 1, 1), datetime(2023, 1, 1)
                    ).strftime('%Y-%m-%d'),
                    'country': random.choice(countries),
                    'is_suspicious': True,
                    'suspicious_type': group_name,
                    'suspicious_role': role
                }
                self.accounts.append(account)
                self.laundering_accounts.append(account)
                group_accounts.append(account)
            
            self.suspicious_groups[group_name] = group_accounts
    
    def generate_star_laundering_accounts(self, groups=3):
        """生成星型拆分入账洗钱账户"""
        countries = ['中国', '美国', '英国', '德国', '法国']
        
        for group_id in range(1, groups + 1):
            group_name = f"星型拆分入账_{group_id}"
            group_accounts = []
            
            # 1个中心账户（洗钱者）+ 5-7个外围账户（协助者）
            center_account = {
                'account_id': self.generate_account_id(),
                'owner_name': fake.name() if random.random() > 0.3 else fake.company(),
                'registration_date': self.generate_random_date(
                    datetime(2020, 1, 1), datetime(2023, 1, 1)
                ).strftime('%Y-%m-%d'),
                'country': random.choice(countries),
                'is_suspicious': True,
                'suspicious_type': group_name,
                'suspicious_role': '洗钱者'
            }
            self.accounts.append(center_account)
            self.laundering_accounts.append(center_account)
            group_accounts.append(center_account)
            
            # 外围账户
            peripheral_count = random.randint(5, 7)
            for _ in range(peripheral_count):
                account = {
                    'account_id': self.generate_account_id(),
                    'owner_name': fake.name() if random.random() > 0.2 else fake.company(),
                    'registration_date': self.generate_random_date(
                        datetime(2020, 1, 1), datetime(2023, 1, 1)
                    ).strftime('%Y-%m-%d'),
                    'country': random.choice(countries),
                    'is_suspicious': True,
                    'suspicious_type': group_name,
                    'suspicious_role': '协助者'
                }
                self.accounts.append(account)
                self.laundering_accounts.append(account)
                group_accounts.append(account)
            
            self.suspicious_groups[group_name] = group_accounts
    
    def generate_cross_border_laundering_accounts(self, groups=3):
        """生成跨境多层转账洗钱账户"""
        high_risk_countries = ['高危国1', '高危国2', '高危国3']
        normal_countries = ['中国', '美国', '英国', '德国']
        
        for group_id in range(1, groups + 1):
            group_name = f"跨境多层转账_{group_id}"
            group_accounts = []
            
            # 1个高危国家账户（洗钱者）
            target_account = {
                'account_id': self.generate_account_id(),
                'owner_name': fake.name() if random.random() > 0.4 else fake.company(),
                'registration_date': self.generate_random_date(
                    datetime(2020, 1, 1), datetime(2023, 1, 1)
                ).strftime('%Y-%m-%d'),
                'country': random.choice(high_risk_countries),
                'is_suspicious': True,
                'suspicious_type': group_name,
                'suspicious_role': '洗钱者'
            }
            self.accounts.append(target_account)
            self.laundering_accounts.append(target_account)
            group_accounts.append(target_account)
            
            # 1个源头账户（协助者）
            source_account = {
                'account_id': self.generate_account_id(),
                'owner_name': fake.name() if random.random() > 0.3 else fake.company(),
                'registration_date': self.generate_random_date(
                    datetime(2020, 1, 1), datetime(2023, 1, 1)
                ).strftime('%Y-%m-%d'),
                'country': random.choice(normal_countries),
                'is_suspicious': True,
                'suspicious_type': group_name,
                'suspicious_role': '协助者'
            }
            self.accounts.append(source_account)
            self.laundering_accounts.append(source_account)
            group_accounts.append(source_account)
            
            # 2-4个中间层账户（协助者）
            intermediate_count = random.randint(2, 4)
            for _ in range(intermediate_count):
                account = {
                    'account_id': self.generate_account_id(),
                    'owner_name': fake.name() if random.random() > 0.2 else fake.company(),
                    'registration_date': self.generate_random_date(
                        datetime(2020, 1, 1), datetime(2023, 1, 1)
                    ).strftime('%Y-%m-%d'),
                    'country': random.choice(normal_countries),
                    'is_suspicious': True,
                    'suspicious_type': group_name,
                    'suspicious_role': '协助者'
                }
                self.accounts.append(account)
                self.laundering_accounts.append(account)
                group_accounts.append(account)
            
            self.suspicious_groups[group_name] = group_accounts
    
    def generate_normal_transactions(self, count=700):
        """生成正常交易"""
        normal_accounts = [acc for acc in self.accounts if not acc['is_suspicious']]
        
        for _ in range(count):
            src_account = random.choice(normal_accounts)
            dst_account = random.choice(normal_accounts)
            
            # 确保不是自己转给自己
            while dst_account['account_id'] == src_account['account_id']:
                dst_account = random.choice(normal_accounts)
            
            # 正常交易金额范围更大，避免与洗钱交易混淆
            amount = round(random.uniform(50, 50000), 2)
            
            transaction_date = self.generate_random_date(
                datetime(2023, 1, 1), datetime(2023, 12, 31)
            )
            
            transaction = {
                'transaction_id': self.generate_transaction_id(),
                'src_account': src_account['account_id'],
                'src_account_country': src_account['country'],
                'dst_account': dst_account['account_id'],
                'dst_account_country': dst_account['country'],
                'amount': amount,
                'currency': 'CNY',
                'value_date': transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                'is_suspicious': False,
                'suspicious_type': ''
            }
            self.transactions.append(transaction)
    
    def generate_circular_transactions(self):
        """生成循环闭环交易"""
        for group_name, accounts in self.suspicious_groups.items():
            if not group_name.startswith('循环闭环交易'):
                continue
                
            # 选择同一天进行交易
            transaction_date = self.generate_random_date(
                datetime(2023, 1, 1), datetime(2023, 12, 31)
            )
            
            # 固定金额进行循环转账
            amount = round(random.uniform(10000, 100000), 2)
            
            # 创建循环：A->B->C->A
            for i in range(len(accounts)):
                src_account = accounts[i]
                dst_account = accounts[(i + 1) % len(accounts)]
                
                transaction = {
                    'transaction_id': self.generate_transaction_id(),
                    'src_account': src_account['account_id'],
                    'src_account_country': src_account['country'],
                    'dst_account': dst_account['account_id'],
                    'dst_account_country': dst_account['country'],
                    'amount': amount,
                    'currency': 'CNY',
                    'value_date': transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_suspicious': True,
                    'suspicious_type': group_name
                }
                self.transactions.append(transaction)
                self.laundering_transactions.append(transaction)
    
    def generate_star_transactions(self):
        """生成星型拆分入账交易"""
        for group_name, accounts in self.suspicious_groups.items():
            if not group_name.startswith('星型拆分入账'):
                continue
                
            # 选择同一天进行交易
            transaction_date = self.generate_random_date(
                datetime(2023, 1, 1), datetime(2023, 12, 31)
            )
            
            # 中心账户是第一个（洗钱者）
            center_account = accounts[0]
            peripheral_accounts = accounts[1:]
            
            # 每个外围账户向中心账户转账，单笔<10000元
            for peripheral_account in peripheral_accounts:
                amount = round(random.uniform(1000, 9999), 2)
                
                transaction = {
                    'transaction_id': self.generate_transaction_id(),
                    'src_account': peripheral_account['account_id'],
                    'src_account_country': peripheral_account['country'],
                    'dst_account': center_account['account_id'],
                    'dst_account_country': center_account['country'],
                    'amount': amount,
                    'currency': 'CNY',
                    'value_date': transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_suspicious': True,
                    'suspicious_type': group_name
                }
                self.transactions.append(transaction)
                self.laundering_transactions.append(transaction)
    
    def generate_cross_border_transactions(self):
        """生成跨境多层转账交易"""
        for group_name, accounts in self.suspicious_groups.items():
            if not group_name.startswith('跨境多层转账'):
                continue
                
            # 选择同一天进行交易
            transaction_date = self.generate_random_date(
                datetime(2023, 1, 1), datetime(2023, 12, 31)
            )
            
            # 找到洗钱者（高危国家账户）和源头账户
            target_account = None
            source_account = None
            intermediate_accounts = []
            
            for account in accounts:
                if account['suspicious_role'] == '洗钱者':
                    target_account = account
                elif account['country'] in ['中国', '美国', '英国', '德国'] and source_account is None:
                    source_account = account
                else:
                    intermediate_accounts.append(account)
            
            # 生成2条多层转账路径
            paths = [
                [source_account] + random.sample(intermediate_accounts, min(2, len(intermediate_accounts))) + [target_account],
                [source_account] + random.sample(intermediate_accounts, min(2, len(intermediate_accounts))) + [target_account]
            ]
            
            for path in paths:
                amount = round(random.uniform(20000, 200000), 2)
                
                # 沿路径生成交易
                for i in range(len(path) - 1):
                    src_acc = path[i]
                    dst_acc = path[i + 1]
                    
                    transaction = {
                        'transaction_id': self.generate_transaction_id(),
                        'src_account': src_acc['account_id'],
                        'src_account_country': src_acc['country'],
                        'dst_account': dst_acc['account_id'],
                        'dst_account_country': dst_acc['country'],
                        'amount': amount,
                        'currency': 'CNY',
                        'value_date': transaction_date.strftime('%Y-%m-%d %H:%M:%S'),
                        'is_suspicious': True,
                        'suspicious_type': group_name
                    }
                    self.transactions.append(transaction)
                    self.laundering_transactions.append(transaction)
    
    def save_data(self):
        """保存数据到CSV文件"""
        # 确保mock_data目录存在
        os.makedirs('mock_data', exist_ok=True)
        
        # 保存所有账户
        accounts_df = pd.DataFrame(self.accounts)
        accounts_df.to_csv('mock_data/account.csv', index=False, encoding='utf-8-sig')
        
        # 保存所有交易
        transactions_df = pd.DataFrame(self.transactions)
        transactions_df.to_csv('mock_data/transaction.csv', index=False, encoding='utf-8-sig')
        
        # 保存洗钱账户（按suspicious_type排序）
        laundering_accounts_df = pd.DataFrame(self.laundering_accounts)
        laundering_accounts_df = laundering_accounts_df.sort_values('suspicious_type')
        laundering_accounts_df.to_csv('mock_data/laundering_account.csv', index=False, encoding='utf-8-sig')
        
        # 保存洗钱交易（按suspicious_type排序）
        laundering_transactions_df = pd.DataFrame(self.laundering_transactions)
        laundering_transactions_df = laundering_transactions_df.sort_values('suspicious_type')
        laundering_transactions_df.to_csv('mock_data/laundering_transaction.csv', index=False, encoding='utf-8-sig')
        
        print(f"数据生成完成！")
        print(f"总账户数: {len(self.accounts)}")
        print(f"总交易数: {len(self.transactions)}")
        print(f"洗钱账户数: {len(self.laundering_accounts)}")
        print(f"洗钱交易数: {len(self.laundering_transactions)}")
        print(f"文件已保存到 mock_data/ 目录")

def main():
    """主函数"""
    generator = AMLDataGenerator()
    
    print("开始生成AML模拟数据...")
    
    # 生成账户
    print("生成正常账户...")
    generator.generate_normal_accounts(70)
    
    print("生成循环闭环交易洗钱账户...")
    generator.generate_circular_laundering_accounts(3)
    
    print("生成星型拆分入账洗钱账户...")
    generator.generate_star_laundering_accounts(3)
    
    print("生成跨境多层转账洗钱账户...")
    generator.generate_cross_border_laundering_accounts(3)
    
    # 生成交易
    print("生成正常交易...")
    generator.generate_normal_transactions(700)
    
    print("生成循环闭环交易...")
    generator.generate_circular_transactions()
    
    print("生成星型拆分入账交易...")
    generator.generate_star_transactions()
    
    print("生成跨境多层转账交易...")
    generator.generate_cross_border_transactions()
    
    # 保存数据
    print("保存数据...")
    generator.save_data()

if __name__ == "__main__":
    main() 