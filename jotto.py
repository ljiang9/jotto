#!/usr/bin/env python3
"""Jotto (乔托) — 文字推理小游戏.

玩法: 电脑藏一个 5 字母英文单词, 你轮流猜.
每次猜测后告诉你「有多少个字母对上」(位置不重要, 只计字母数量).
先猜中秘密单词的一方赢. AI 用约束消除法玩.

规则(简化版):
- 单词库: 内置 5 字母英文单词, 字母不重复(经典 Jotto 规则).
- 分数 = 猜测词与秘密词共有字母数(位置无关).
- 分数 5 = 猜中.
"""
from __future__ import annotations

import argparse
import copy
import random
import sys

# 内置 5 字母单词库. 约 500 词(去重后).
_RAW = (
    "about above abuse actor acute admit adopt adult after again agent agree ahead alarm "
    "album alert alike alive allow alone along aloud alter angel anger angle ankle apart "
    "apple argue arise armor awake bacon badge baker basic beach beard begin belly bench"
    "berry birth black blade blame blank blast blend bless blind block blood bloom board"
    "bonus boost booth bound brain brand brave bread break brick bride brief bring broad"
    "broke brown brush build bunch buyer cabin cable candy carry catch cause chain chair"
    "charm chart chase cheap check cheese chest chief child choir chose civil claim"
    "class clean clear clerk click cliff climb clock close cloth cloud coach coast"
    "color comet comma coral could count court cover crack craft crash crazy cream"
    "crime cross crowd crown curve cycle daily dance death delay depth diary dirty"
    "dodge doing doubt dough draft drain drama dream dress drink drive drove drunk"
    "eager early earth eight elbow elder elect elite empty enemy enjoy enter entry"
    "equal error essay event every exact exist extra faint faith false fancy fault"
    "favor feast fence fever field fifth fifty fight final first flame flash fleet"
    "flesh float floor flour fluid focus force forth forty forum found frame fresh"
    "friend front frost fruit funny giant given glass globe going grace grade grain"
    "grand grant grape grass great green greet grief group guard guess guest guide"
    "happy heart heavy hello honey honor horse hotel house human hurry ideal image"
    "index inner input issue ivory joint judge juice knife knock known label large"
    "laser later laugh layer learn least leave legal lemon level light limit liver"
    "lobby local logic loose lucky lunch magic major maker march match maybe mayor"
    "medal media mercy merit metal meter micro might minor minus minus model money"
    "month moral motor mount mouse mouth movie music nasty never night noble noise"
    "north notch novel nurse occur ocean offer often older olive onion opera order"
    "other ought outer owner paint panel paper party patch pause peace penny phase"
    "phone photo piano piece pilot pitch place plain plane plant plate point pound"
    "power press price pride prime print prize proof proud prove queen quick quiet"
    "quite radio raise range rapid ratio reach ready realm rebel refer renew reply"
    "rider right river roast robot rocky roman rough round route royal rural salad"
    "scale scene score sense serve seven shade shake shall shape share sharp sheep"
    "sheet shelf shell shift shine shirt shock shoot shore short shout shown sight"
    "since sixth sixty skill skirt sleep slice slide slope small smart smell smile"
    "smoke snake solar solid solve sorry sound south space spare speak speed spell"
    "spend spice split spoke sport staff stage stair stand start state steam steel"
    "steep stick still stock stone stood store storm story strip stuck study stuff"
    "style sugar suite sunny super sweet table taken taste teach teeth thank their"
    "theme there these thick thing think third those three threw throw thumb tight"
    "tired title today token tooth topic total touch tough tower town trace track"
    "trade trail train treat trend trial tribe trick truck truly trust truth twice"
    "twist uncle under union unite until upper upset urban usual valid value video"
    "visit vital voice voter waste watch water weave wheel where which while white"
    "whole whose woman women world worry worth would wound write wrong wrote yield"
    "young youth"
).split()

# 源码里多行字符串相邻行若漏写空格会导致两个 5 字母词粘连(如 "boardbonus"),
# 这里做一次健壮处理: 长度为 5 倍数的粘连 token 按 5 字母切分;
# 非 5 倍数的真词(如 6 字母的 cheese/friend、4 字母的 town)直接丢弃.
_WORDS = []
for _tok in _RAW:
    if len(_tok) == 5:
        _WORDS.append(_tok)
    elif len(_tok) > 5 and len(_tok) % 5 == 0:
        for _i in range(0, len(_tok), 5):
            _WORDS.append(_tok[_i:_i + 5])
WORDS = tuple(dict.fromkeys(w for w in _WORDS if len(w) == 5))
del _RAW, _WORDS, _tok, _i

WORD_LEN = 5


def score(guess: str, secret: str) -> int:
    """计分: 共有字母数(按字母多重集取交, 位置无关)."""
    g, s = guess.lower(), secret.lower()
    total = 0
    used = list(s)
    for ch in g:
        if ch in used:
            used.remove(ch)
            total += 1
    return total


class IllegalMove(Exception):
    pass


class Jotto:
    def __init__(self, secret: str, word_list: list[str] | None = None,
                 rng: random.Random | None = None):
        self.words = list(dict.fromkeys(word_list or WORDS))
        for w in self.words:
            if len(w) != WORD_LEN or not w.isalpha():
                raise ValueError(f"坏词: {w!r}")
        if secret not in self.words:
            raise IllegalMove("秘密词不在词库中")
        self.secret = secret
        self.rng = rng or random.Random()
        self.guesses: list[tuple[str, int]] = []  # (guess, score)
        self.won = False

    def guess(self, word: str) -> int:
        """猜一次, 返回分数. 5 = 猜中."""
        word = word.strip().lower()
        if word not in self.words:
            raise IllegalMove("猜测词不在词库中")
        sc = score(word, self.secret)
        self.guesses.append((word, sc))
        if sc == WORD_LEN:
            self.won = True
        return sc

    def candidates(self) -> list[str]:
        """约束消除: 保留所有与历史猜测分数一致的候选词."""
        out = []
        for w in self.words:
            ok = True
            for g, s in self.guesses:
                if score(g, w) != s:
                    ok = False
                    break
            if ok:
                out.append(w)
        return out


def ai_choose(cands: list[str], all_words: list[str]) -> str:
    """贪心最小化最坏情况: 枚举每个可能的猜测词, 选让候选集
    按分数分区后最大分区最小的一个(简单 minimax)."""
    if len(cands) <= 2:
        return cands[0]
    best, best_key = None, None
    # 为速度: 候选词本身 + 采样少量外词
    pool = cands if len(cands) <= 60 else random.sample(cands, 60)
    for guess in pool:
        buckets: dict[int, int] = {}
        for c in cands:
            s = score(guess, c)
            buckets[s] = buckets.get(s, 0) + 1
        worst = max(buckets.values())
        key = (worst, guess not in cands)  # 候选内优先
        if best_key is None or key < best_key:
            best_key, best = key, guess
    return best


def play_auto(secret: str, max_guesses: int = 30, verbose: bool = False,
              rng: random.Random | None = None) -> tuple[bool, int]:
    rng = rng or random.Random()
    game = Jotto(secret, rng=rng)
    for i in range(1, max_guesses + 1):
        cands = game.candidates()
        if not cands:
            return False, i - 1
        guess = ai_choose(cands, WORDS)
        sc = game.guess(guess)
        if verbose:
            print(f"  第{i}猜: {guess} -> {sc} 分 (候选{cands and len(cands)})")
        if sc == WORD_LEN:
            return True, i
    return False, max_guesses


def interactive(rng: random.Random) -> None:
    if not sys.stdin.isatty():
        print("交互模式需要终端. 试试 --auto 自动演示.", file=sys.stderr)
        sys.exit(2)
    secret = rng.choice(WORDS)
    game = Jotto(secret, rng=rng)
    print(f"Jotto! 我藏了一个 5 字母单词(共 {len(WORDS)} 个候选).")
    print("每次猜我会告诉你共有几个字母对上(位置无关). 输入 q 退出.")
    while not game.won:
        word = input("你的猜测: ").strip().lower()
        if word in ("q", "quit"):
            print(f"秘密词是: {secret}")
            return
        try:
            sc = game.guess(word)
        except IllegalMove as e:
            print(f"  无效: {e}")
            continue
        if game.won:
            print(f"猜中! {secret}, 用了 {len(game.guesses)} 次.")
        else:
            print(f"  {word} -> {sc} 分")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Jotto 文字推理游戏")
    p.add_argument("--auto", action="store_true", help="AI 自动演示")
    p.add_argument("--games", type=int, default=10, help="自动演示局数")
    p.add_argument("--seed", type=int, default=None, help="随机种子")
    p.add_argument("--verbose", action="store_true", help="打印每步")
    args = p.parse_args(argv)
    rng = random.Random(args.seed)

    if args.auto:
        solved = 0
        total_guesses = 0
        for i in range(1, args.games + 1):
            secret = rng.choice(WORDS)
            won, n = play_auto(secret, verbose=args.verbose, rng=rng)
            solved += won
            total_guesses += n
            if args.verbose or args.games <= 20:
                print(f"第{i}/{args.games}局: {'猜中' if won else '失败'} "
                      f"({secret}, {n}猜)")
        print(f"共 {args.games} 局: 猜中 {solved}, "
              f"平均 {total_guesses / args.games:.1f} 猜/局")
    else:
        interactive(rng)


if __name__ == "__main__":
    main()
