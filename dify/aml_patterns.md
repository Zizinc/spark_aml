# 循环闭环交易
- 特征：3个或以上账户在同一天内形成闭环，金额一致
- 示例：A转钱给B，B转钱给C，C转钱给A即为循环闭环交易。其中A的suspicious_role为洗钱者，B和C的suspicious_role为协助者

# 星型拆分入账
- 特征：5个或以上账户在同一天内向同一账户转账，单笔<10000元
- 示例：B转钱给A，C转钱给A，D转钱给A，E转钱给A，F转钱给A。其中A的suspicious_role为洗钱者，B,C,D,E,F的suspicious_role为协助者

# 跨境多层转账
- 特征：存在2笔或以上交易通过3层或以上账户在同一天内流向高风险国家
- 示例：C的账户属于高危国X，一笔A转钱给Z，Z转钱给C，一笔A转钱给Y，Y转钱给C，Y可以是Z，也可以是另一个人，但是A必须是同一个人。其中C的suspicious_role为洗钱者，A，Y，Z的suspicious_role为协助者
