---
name: postgraduate-skill
description: 查询考研研招复试分段和院校。用户要按分数、专业、学校、学院、层次（985/211/双非）、地区、省份、城市、A/B 区、学习方式或考试科目筛选学校时使用。
---

# 研招查询

只运行本目录的 `scripts/query.py`。不要打开或解密 `data/retest.json.enc`。

密码不在这个仓库里。用户告诉你之后，写入 `~/.config/environment.d/postgraduate.conf`（若设置了 `XDG_CONFIG_HOME`，则写到那里的 `environment.d/postgraduate.conf`）。一行 `POSTGRADUATE_DATA_KEY=...`，权限 `0600`。不要把密码写进本目录，不要提交，不要每次让用户在 shell 里 export。用户要求更新时必须再输入一次密码，用新密码覆盖这个文件。

## 更新

数据以本仓库的 `data/retest.json.enc` 为准。用户要求更新时，在本目录重新拉取仓库，不要自己抓接口，也不要改密文。

```bash
git pull
```

密码也要一起更新。拉取后向用户要新密码，等用户再次输入，再覆盖 `~/.config/environment.d/postgraduate.conf`。不要沿用旧密码。

## 查询

在本目录执行。条件可以组合，同时满足才留下。stdout 是 JSON。

```bash
python3 scripts/query.py --major 计算机 --tier 985 --score 380 --limit 5
```

- 包含：`--school` `--college` `--major` `--major-code` `--direction` `--subject`（科目代码或名称）
- 精确：`--tier` `--region` `--province` `--city` `--area` `--study-mode` `--year`
- `--score` 落在分段里。结果多一个 `matchedSegment`，按录取比例和录取人数从高到低
- `--min-admit-rate` `--min-admitted` `--min-retest`
- `--limit` 默认 20
- `--count` 只打印条数
- `--fields` 打印参数说明，不解密

没有 `--score` 时，每条包含学校、学院、专业、层次、地区、省份、城市、A/B 区、学习方式、方向、年份、考试科目、全部分段和 `sheet`。文件里的 `subjectNames` 是全国统考代码到名称的对照。
