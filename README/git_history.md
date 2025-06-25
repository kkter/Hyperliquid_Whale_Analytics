
- 推送到私人仓库 Onedata:

```

git add .

git commit -m "增加网页自动刷新功能"

git tag -a v1.0.0 -m "初版"

git push origin v1.0.0

git push origin
```
- 推送到公开仓库 Hyperliquid_Whale_Analytics:

git remote add public git@github.com:kkter/Hyperliquid_Whale_Analytics.git # 自定义远程分支的名称为 "public"

git push -u origin master

```
git add .

git commit -m "init"

git tag -a v1.0.1 -m "init"

git push public v1.0.1

git push public

---

1. git commit -m "init"

  初版

2. git commit -m "get_address.py 输出存入数据库，代码改纯英文版"

3. get_address.py 添加定时功能，
   完成 update_positions.py，
   完成前端页面

   git commit -m "前、后端完成"

4. 数据库中“size”全为正值，实际上空头仓位的“siz"是负值。
   结果就是全为“Long”；
   其他小Bug;

   git commit -m "修复小Bug"

5. 2025-06-25
   增加自动刷新网页功能。
   “用JavaScript定时刷新部分内容”
   git commit -m "增加网页自动刷新功能"
   git tag -a v1.0.0 -m "初版"


6. 2025-06-25
   推送到不同仓库
