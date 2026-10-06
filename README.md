# Jotto 乔托

文字推理小游戏：电脑藏一个 5 字母英文单词，你轮流猜；
每次猜测后告诉你「有多少个字母对上」（位置不重要，只计字母数量）；
拿到 5 分 = 猜中。

纯 Python 标准库，无第三方依赖。

## 玩法

```bash
python3 -m jotto                 # 人机对战（需要终端）
python3 -m jotto --auto --games 10 --seed 42   # AI 自动演示 10 局
python3 -m jotto --auto --games 5 --verbose    # 看 AI 每一步的思考
```

人机对战时直接输入 5 字母单词猜，输入 `q` 退出。

## 规则（简化版）

- 内置 549 个 5 字母英文单词候选。
- 分数 = 猜测词与秘密词共有字母数（位置无关，按字母多重集取交）。
- AI 用**约束消除法**：每轮保留所有与历史分数一致的候选词，
  再用简单的 minimax 贪心选一个让最坏情况分区最小的猜测。

## 真实验证记录

- `python3 -m py_compile jotto.py __main__.py`：通过。
- 单元测试（全部真实执行）：计分（`apple`/`papal`=4、`abcde`/`edcba`=5）、
  猜中判胜、词库外猜测/秘密词抛 `IllegalMove`、约束消除后秘密词恒在候选内、
  AI 对 `apple` 及词库首/中/尾词均在 30 猜内猜中 —— 全部通过。
- `python3 -m jotto --auto --games 10 --seed 42`：**10 局全猜中，平均 4.1 猜/局**
  （count 5 猜、angle 4 猜、meter 2 猜、laser 5 猜、honey 4 猜、
  dream 4 猜、close 3 猜、chest 2 猜、spice 6 猜、awake 6 猜）。
- 非终端运行交互模式：中文提示并以 exit 2 退出。
- 无 TODO/FIXME 占位符。

## 已知局限（诚实版）

- 词库只有 549 个常见 5 字母词，词汇量小；经典 Jotto 要求字母不重复，
  本实现允许重复字母（如 apple），计分按多重集交集处理。
- AI 是单层贪心 minimax，不做深层信息论搜索；
  词库小所以实测平均 4 猜左右就能猜中，换大词库会明显变弱。
- 纯文本界面，无图形/存档/悔棋/网络对战；Python 3.10+。

## 文件

- `jotto.py` — 全部实现（约 200 行）
- `__main__.py` — `python -m jotto` 入口
- `README.md` — 本说明
- `LICENSE` — MIT（Copyright (c) 2026 ljiang9）

MIT License，Copyright (c) 2026 ljiang9。
