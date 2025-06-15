#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AML洗钱网络可视化脚本
输入：result/detected_account.csv, result/detected_transaction.csv
输出：result/visualization/循环闭环交易网络.html, result/visualization/星型拆分入账网络.html, result/visualization/跨境多层转账网络.html
"""

import pandas as pd
import networkx as nx
import json
import os
from collections import defaultdict
import math

def load_detection_data():
    """加载检测结果数据"""
    print("加载检测结果数据...")
    
    accounts_df = pd.read_csv('result/detected_account.csv')
    transactions_df = pd.read_csv('result/detected_transaction.csv')
    
    print(f"账户数据: {len(accounts_df)} 条")
    print(f"交易数据: {len(transactions_df)} 条")
    
    return accounts_df, transactions_df

def get_money_launderer_transactions(accounts_df, transactions_df, pattern_type):
    """获取洗钱者相关的所有交易"""
    # 找到该模式的所有账户
    pattern_accounts = accounts_df[
        accounts_df['detected_suspicious_type'] == pattern_type
    ]['account_id'].tolist()
    
    if not pattern_accounts:
        print(f"  {pattern_type}模式没有相关账户")
        return transactions_df[transactions_df['detected_suspicious_type'] == pattern_type].copy()
    
    # 对于循环闭环交易，需要获取所有涉及该模式账户的交易，不仅仅是洗钱者的交易
    if pattern_type == '循环闭环交易':
        # 获取所有涉及该模式账户的交易（包括可疑和非可疑交易）
        all_related_transactions = transactions_df[
            (transactions_df['src_account'].isin(pattern_accounts)) |
            (transactions_df['dst_account'].isin(pattern_accounts))
        ].copy()
        
        # 优先显示可疑交易，但也包含相关的普通交易以显示完整网络
        suspicious_transactions = transactions_df[
            transactions_df['detected_suspicious_type'] == pattern_type
        ].copy()
        
        # 合并可疑交易和相关交易，去重
        combined_transactions = pd.concat([suspicious_transactions, all_related_transactions]).drop_duplicates(subset=['transaction_id'])
        
        print(f"  {pattern_type}模式: 可疑交易 {len(suspicious_transactions)} 笔，相关交易 {len(combined_transactions)} 笔")
        return combined_transactions
    
    else:
        # 对于其他模式，找到洗钱者
        money_launderers = accounts_df[
            (accounts_df['detected_suspicious_type'] == pattern_type) & 
            (accounts_df['detected_suspicious_role'] == '洗钱者')
        ]['account_id'].tolist()
        
        if money_launderers:
            # 获取洗钱者相关的所有交易（作为源账户或目标账户）
            launderer_transactions = transactions_df[
                (transactions_df['src_account'].isin(money_launderers)) |
                (transactions_df['dst_account'].isin(money_launderers))
            ].copy()
        else:
            # 如果没有洗钱者（如跨境多层转账），获取该模式的所有可疑交易
            print(f"  {pattern_type}模式没有洗钱者，获取所有相关可疑交易")
            launderer_transactions = transactions_df[
                transactions_df['detected_suspicious_type'] == pattern_type
            ].copy()
            
            # 如果还是没有交易，获取涉及该模式账户的所有交易
            if len(launderer_transactions) == 0:
                launderer_transactions = transactions_df[
                    (transactions_df['src_account'].isin(pattern_accounts)) |
                    (transactions_df['dst_account'].isin(pattern_accounts))
                ].copy()
        
        return launderer_transactions

def create_network_data(accounts_df, transactions_df, pattern_type):
    """为特定洗钱模式创建网络数据"""
    print(f"创建{pattern_type}网络数据...")
    
    # 获取该模式相关的账户
    pattern_accounts = accounts_df[
        accounts_df['detected_suspicious_type'] == pattern_type
    ].copy()
    
    if len(pattern_accounts) == 0:
        print(f"未找到{pattern_type}相关账户")
        return None, None
    
    # 获取洗钱者相关的所有交易
    all_transactions = get_money_launderer_transactions(accounts_df, transactions_df, pattern_type)
    
    # 获取涉及的所有账户ID
    involved_accounts = set(pattern_accounts['account_id'].tolist())
    involved_accounts.update(all_transactions['src_account'].tolist())
    involved_accounts.update(all_transactions['dst_account'].tolist())
    
    # 获取所有涉及账户的信息
    network_accounts = accounts_df[accounts_df['account_id'].isin(involved_accounts)].copy()
    
    # 创建节点数据
    nodes = []
    for _, account in network_accounts.iterrows():
        is_suspicious = account.get('detected_suspicious', False)
        suspicious_type = account.get('detected_suspicious_type', '')
        role = account.get('detected_suspicious_role', '')
        
        # 确定节点颜色和大小
        if is_suspicious and suspicious_type == pattern_type:
            if role == '洗钱者':
                color = '#ff4444'  # 红色 - 洗钱者
                size = 30
            else:
                color = '#ff8844'  # 橙色 - 协助者
                size = 20
        else:
            color = '#4488ff'  # 蓝色 - 普通账户
            size = 15
        
        nodes.append({
            'id': str(account['account_id']),
            'label': f"{account['owner_name']}\n({account['account_id']})",
            'title': f"账户: {account['account_id']}<br/>所有者: {account['owner_name']}<br/>国家: {account['country']}<br/>角色: {role if role else '普通账户'}",
            'color': color,
            'size': size,
            'font': {'size': 12, 'color': '#000000'},
            'borderWidth': 2,
            'borderColor': '#000000' if is_suspicious and suspicious_type == pattern_type else '#cccccc'
        })
    
    # 创建边数据
    edges = []
    edge_id = 0
    
    for _, transaction in all_transactions.iterrows():
        src_id = str(transaction['src_account'])
        dst_id = str(transaction['dst_account'])
        
        # 检查是否是可疑交易
        is_suspicious_transaction = transaction.get('detected_suspicious', False)
        suspicious_trans_type = transaction.get('detected_suspicious_type', '')
        
        # 确定边的颜色和宽度
        if is_suspicious_transaction and suspicious_trans_type == pattern_type:
            color = '#ff0000'  # 红色 - 可疑交易
            width = 4
            dashes = False
        else:
            color = '#888888'  # 灰色 - 普通交易
            width = 2
            dashes = [5, 5]
        
        # 格式化金额
        amount = transaction['amount']
        amount_str = f"{amount:,.2f}" if amount < 10000 else f"{amount/10000:.1f}万"
        
        edges.append({
            'id': edge_id,
            'from': src_id,
            'to': dst_id,
            'label': f"{amount_str} {transaction['currency']}",
            'title': f"交易ID: {transaction['transaction_id']}<br/>金额: {amount:,.2f} {transaction['currency']}<br/>日期: {transaction['value_date']}<br/>类型: {'可疑交易' if is_suspicious_transaction else '普通交易'}",
            'color': color,
            'width': width,
            'arrows': {'to': {'enabled': True, 'scaleFactor': 1.2}},
            'font': {'size': 10, 'color': '#000000', 'strokeWidth': 2, 'strokeColor': '#ffffff'},
            'dashes': dashes if 'dashes' in locals() and dashes else False
        })
        edge_id += 1
    
    return nodes, edges

def generate_html_template(pattern_type, nodes, edges):
    """生成HTML模板"""
    
    # 计算布局参数
    node_count = len(nodes)
    if pattern_type == '星型拆分入账':
        # 星型布局
        physics_config = {
            'enabled': True,
            'solver': 'hierarchicalRepulsion',
            'hierarchicalRepulsion': {
                'centralGravity': 0.3,
                'springLength': 200,
                'springConstant': 0.01,
                'nodeDistance': 150,
                'damping': 0.09
            },
            'stabilization': {'iterations': 100}
        }
    elif pattern_type == '循环闭环交易':
        # 环形布局
        physics_config = {
            'enabled': True,
            'solver': 'forceAtlas2Based',
            'forceAtlas2Based': {
                'gravitationalConstant': -50,
                'centralGravity': 0.01,
                'springLength': 200,
                'springConstant': 0.08,
                'damping': 0.4,
                'avoidOverlap': 1
            },
            'stabilization': {'iterations': 150}
        }
    else:
        # 层次布局
        physics_config = {
            'enabled': True,
            'solver': 'hierarchicalRepulsion',
            'hierarchicalRepulsion': {
                'centralGravity': 0.1,
                'springLength': 250,
                'springConstant': 0.01,
                'nodeDistance': 200,
                'damping': 0.09
            },
            'stabilization': {'iterations': 200}
        }
    
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{pattern_type}资金链路网络</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            text-align: center;
            margin-bottom: 20px;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            color: #333;
            margin: 0 0 10px 0;
        }}
        .header p {{
            color: #666;
            margin: 5px 0;
        }}
        .legend {{
            background: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .legend h3 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .legend-item {{
            display: inline-block;
            margin: 5px 15px 5px 0;
            align-items: center;
        }}
        .legend-color {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            margin-right: 8px;
            vertical-align: middle;
            border: 2px solid #000;
        }}
        .legend-line {{
            display: inline-block;
            width: 30px;
            height: 4px;
            margin-right: 8px;
            vertical-align: middle;
        }}
        #network {{
            width: 100%;
            height: 700px;
            border: 2px solid #ddd;
            border-radius: 10px;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .controls {{
            background: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-top: 20px;
            text-align: center;
        }}
        .controls button {{
            background: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            margin: 5px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }}
        .controls button:hover {{
            background: #45a049;
        }}
        .stats {{
            background: white;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-top: 20px;
        }}
        .stats h3 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }}
        .stat-item {{
            text-align: center;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
        }}
        .stat-number {{
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
        }}
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{pattern_type}资金链路网络</h1>
        <p>基于GraphFrame检测的洗钱网络可视化</p>
        <p>红色节点：洗钱者 | 橙色节点：协助者 | 蓝色节点：普通账户</p>
    </div>
    
    <div class="legend">
        <h3>图例说明</h3>
        <div class="legend-item">
            <span class="legend-color" style="background-color: #ff4444;"></span>
            <span>洗钱者</span>
        </div>
        <div class="legend-item">
            <span class="legend-color" style="background-color: #ff8844;"></span>
            <span>协助者</span>
        </div>
        <div class="legend-item">
            <span class="legend-color" style="background-color: #4488ff;"></span>
            <span>普通账户</span>
        </div>
        <div class="legend-item">
            <span class="legend-line" style="background-color: #ff0000;"></span>
            <span>可疑交易</span>
        </div>
        <div class="legend-item">
            <span class="legend-line" style="background-color: #888888;"></span>
            <span>普通交易</span>
        </div>
    </div>
    
    <div id="network"></div>
    
    <div class="controls">
        <button onclick="fitNetwork()">适应窗口</button>
        <button onclick="resetView()">重置视图</button>
        <button onclick="togglePhysics()">切换物理引擎</button>
        <button onclick="exportImage()">导出图片</button>
    </div>
    
    <div class="stats">
        <h3>网络统计</h3>
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-number" id="nodeCount">{len(nodes)}</div>
                <div class="stat-label">账户节点</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="edgeCount">{len(edges)}</div>
                <div class="stat-label">交易边</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="suspiciousNodes">{len([n for n in nodes if n['color'] in ['#ff4444', '#ff8844']])}</div>
                <div class="stat-label">可疑账户</div>
            </div>
            <div class="stat-item">
                <div class="stat-number" id="suspiciousEdges">{len([e for e in edges if e['color'] == '#ff0000'])}</div>
                <div class="stat-label">可疑交易</div>
            </div>
        </div>
    </div>

    <script>
        // 网络数据
        const nodes = new vis.DataSet({json.dumps(nodes, ensure_ascii=False, indent=8)});
        const edges = new vis.DataSet({json.dumps(edges, ensure_ascii=False, indent=8)});
        
        // 网络配置
        const options = {{
            physics: {json.dumps(physics_config, indent=12)},
            interaction: {{
                hover: true,
                tooltipDelay: 200,
                hideEdgesOnDrag: false,
                hideNodesOnDrag: false
            }},
            layout: {{
                improvedLayout: true,
                clusterThreshold: 150
            }},
            edges: {{
                smooth: {{
                    enabled: true,
                    type: 'dynamic',
                    roundness: 0.5
                }},
                labelHighlightBold: true
            }},
            nodes: {{
                shape: 'dot',
                labelHighlightBold: true,
                chosen: {{
                    node: function(values, id, selected, hovering) {{
                        values.borderWidth = 4;
                        values.borderColor = '#000000';
                    }}
                }}
            }},
            groups: {{}},
            configure: {{
                enabled: false
            }}
        }};
        
        // 创建网络
        const container = document.getElementById('network');
        const data = {{ nodes: nodes, edges: edges }};
        const network = new vis.Network(container, data, options);
        
        // 网络事件
        network.on('click', function(params) {{
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const node = nodes.get(nodeId);
                console.log('点击节点:', node);
            }}
            if (params.edges.length > 0) {{
                const edgeId = params.edges[0];
                const edge = edges.get(edgeId);
                console.log('点击边:', edge);
            }}
        }});
        
        network.on('hoverNode', function(params) {{
            const nodeId = params.node;
            const connectedEdges = network.getConnectedEdges(nodeId);
            const connectedNodes = network.getConnectedNodes(nodeId);
            
            // 高亮连接的节点和边
            const updateArray = [];
            edges.forEach(function(edge) {{
                if (connectedEdges.includes(edge.id)) {{
                    updateArray.push({{id: edge.id, color: {{color: '#ff0000', highlight: '#ff0000'}}}});
                }}
            }});
            edges.update(updateArray);
        }});
        
        network.on('blurNode', function(params) {{
            // 恢复原始颜色
            edges.forEach(function(edge) {{
                const originalColor = edge.color;
                edges.update({{id: edge.id, color: originalColor}});
            }});
        }});
        
        // 控制函数
        let physicsEnabled = true;
        
        function fitNetwork() {{
            network.fit({{
                animation: {{
                    duration: 1000,
                    easingFunction: 'easeInOutQuad'
                }}
            }});
        }}
        
        function resetView() {{
            network.moveTo({{
                position: {{x: 0, y: 0}},
                scale: 1,
                animation: {{
                    duration: 1000,
                    easingFunction: 'easeInOutQuad'
                }}
            }});
        }}
        
        function togglePhysics() {{
            physicsEnabled = !physicsEnabled;
            network.setOptions({{physics: {{enabled: physicsEnabled}}}});
            event.target.textContent = physicsEnabled ? '关闭物理引擎' : '开启物理引擎';
        }}
        
        function exportImage() {{
            const canvas = network.getCanvas();
            const dataURL = canvas.toDataURL('image/png');
            const link = document.createElement('a');
            link.download = '{pattern_type}_network.png';
            link.href = dataURL;
            link.click();
        }}
        
        // 初始化
        network.once('stabilizationIterationsDone', function() {{
            console.log('网络布局稳定完成');
            fitNetwork();
        }});
        
        // 窗口大小改变时重新适应
        window.addEventListener('resize', function() {{
            network.redraw();
        }});
    </script>
</body>
</html>
"""
    
    return html_content

def create_visualizations(accounts_df, transactions_df):
    """创建所有洗钱模式的可视化"""
    print("创建洗钱网络可视化...")
    
    # 确保输出目录存在
    os.makedirs('result/visualization', exist_ok=True)
    
    # 三种洗钱模式
    patterns = ['循环闭环交易', '星型拆分入账', '跨境多层转账']
    
    created_files = []
    
    for pattern in patterns:
        print(f"\n处理{pattern}模式...")
        
        # 创建网络数据
        nodes, edges = create_network_data(accounts_df, transactions_df, pattern)
        
        if nodes is None or len(nodes) == 0:
            print(f"  {pattern}模式无数据，跳过")
            continue
        
        print(f"  节点数: {len(nodes)}, 边数: {len(edges)}")
        
        # 生成HTML
        html_content = generate_html_template(pattern, nodes, edges)
        
        # 保存文件
        filename = f'result/visualization/{pattern}网络.html'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        created_files.append(filename)
        print(f"  已生成: {filename}")
    
    return created_files

def generate_index_page(created_files):
    """生成索引页面"""
    print("生成索引页面...")
    
    index_html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AML洗钱网络可视化</title>
    <style>
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        .header h1 {
            font-size: 3em;
            margin: 0 0 10px 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 30px;
            margin-top: 40px;
        }
        .card {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            text-align: center;
        }
        .card:hover {
            transform: translateY(-10px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }
        .card h3 {
            color: #333;
            font-size: 1.5em;
            margin: 0 0 15px 0;
        }
        .card p {
            color: #666;
            line-height: 1.6;
            margin-bottom: 20px;
        }
        .card a {
            display: inline-block;
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            text-decoration: none;
            padding: 12px 30px;
            border-radius: 25px;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        .card a:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .icon {
            font-size: 3em;
            margin-bottom: 20px;
        }
        .stats {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 30px;
            margin-top: 40px;
            color: white;
            text-align: center;
        }
        .stats h3 {
            margin: 0 0 20px 0;
            font-size: 1.8em;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        .stat-item {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .stat-label {
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🕸️ AML洗钱网络可视化</h1>
            <p>基于GraphFrame技术的反洗钱模式检测与可视化系统</p>
        </div>
        
        <div class="cards">
"""
    
    # 添加每个网络的卡片
    card_configs = [
        {
            'title': '循环闭环交易网络',
            'icon': '🔄',
            'description': '展示资金在多个账户间形成闭环流转的洗钱模式，通过GraphFrame检测三角形和四边形循环结构。',
            'file': '循环闭环交易网络.html'
        },
        {
            'title': '星型拆分入账网络',
            'icon': '⭐',
            'description': '展示多个账户向中心账户小额转账的洗钱模式，通过分散资金来源规避监管。',
            'file': '星型拆分入账网络.html'
        },
        {
            'title': '跨境多层转账网络',
            'icon': '🌍',
            'description': '展示资金通过多层中转最终流向高危国家的洗钱模式，利用复杂路径掩盖资金来源。',
            'file': '跨境多层转账网络.html'
        }
    ]
    
    for config in card_configs:
        if config['file'] in [os.path.basename(f) for f in created_files]:
            index_html += f"""
            <div class="card">
                <div class="icon">{config['icon']}</div>
                <h3>{config['title']}</h3>
                <p>{config['description']}</p>
                <a href="{config['file']}">查看网络 →</a>
            </div>
"""
    
    # 读取统计数据
    try:
        accounts_df = pd.read_csv('result/detected_account.csv')
        transactions_df = pd.read_csv('result/detected_transaction.csv')
        
        total_accounts = len(accounts_df)
        total_transactions = len(transactions_df)
        suspicious_accounts = accounts_df['detected_suspicious'].sum()
        suspicious_transactions = transactions_df['detected_suspicious'].sum()
    except:
        total_accounts = 0
        total_transactions = 0
        suspicious_accounts = 0
        suspicious_transactions = 0
    
    index_html += f"""
        </div>
        
        <div class="stats">
            <h3>📊 检测统计</h3>
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-number">{total_accounts}</div>
                    <div class="stat-label">总账户数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{total_transactions}</div>
                    <div class="stat-label">总交易数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{suspicious_accounts}</div>
                    <div class="stat-label">可疑账户</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{suspicious_transactions}</div>
                    <div class="stat-label">可疑交易</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
    
    # 保存索引页面
    with open('result/visualization/index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    print("已生成索引页面: result/visualization/index.html")

def main():
    """主函数"""
    print("=== AML洗钱网络可视化开始 ===")
    
    try:
        # 加载数据
        accounts_df, transactions_df = load_detection_data()
        
        # 创建可视化
        created_files = create_visualizations(accounts_df, transactions_df)
        
        # 生成索引页面
        generate_index_page(created_files)
        
        print(f"\n=== 可视化完成 ===")
        print(f"共生成 {len(created_files)} 个网络可视化文件:")
        for file in created_files:
            print(f"  ✅ {file}")
        print(f"  ✅ result/visualization/index.html (索引页面)")
        print(f"\n请打开 result/visualization/index.html 查看可视化结果")
        
    except Exception as e:
        print(f"可视化过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("=== AML洗钱网络可视化完成 ===")

if __name__ == "__main__":
    main() 