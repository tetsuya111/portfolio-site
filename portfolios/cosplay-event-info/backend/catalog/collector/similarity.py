"""名前の同一判定に使うレーベンシュタイン距離と類似度（EV-3・CP-3）。"""

import re
import unicodedata

# 名前の表記ゆれとして無視する文字（空白・中黒・記号類）
_IGNORED = re.compile(
    r"[\s・･\-‐−–—_~〜～!！?？.,，、。:：;；'\"’”“「」『』【】()（）\[\]［］/／|｜☆★♪]+"
)


def levenshtein(a: str, b: str) -> int:
    """挿入・削除・置換をそれぞれ1回として数えた編集距離。"""
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(
                min(
                    previous[j] + 1,  # 削除
                    current[j - 1] + 1,  # 挿入
                    previous[j - 1] + (ca != cb),  # 置換
                )
            )
        previous = current
    return previous[-1]


def normalize_name(s: str) -> str:
    """全角・半角、大文字・小文字、空白・記号の違いをなくす。"""
    return _IGNORED.sub("", unicodedata.normalize("NFKC", s).casefold())


def similarity(a: str, b: str) -> float:
    """正規化した名前の類似度（1 − 距離 ÷ 長い方の文字数）。両方空なら 0。"""
    na, nb = normalize_name(a), normalize_name(b)
    longest = max(len(na), len(nb))
    if longest == 0:
        return 0.0
    return 1 - levenshtein(na, nb) / longest
