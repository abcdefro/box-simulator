"""open_box.py의 결과를 화면에 보여줄 표(DataFrame)로 바꿔주는 함수 모음.

streamlit에 의존하지 않아서 단독으로 테스트할 수 있다.
"""
import random
from collections import Counter

import pandas as pd

import open_box as ob


# ── 확률표 정보 ──────────────────────────────────────────────
def tank_levels():
    """{전차 이름: 그 전차가 나오는 상자 단계}"""
    return {tank: lvl for lvl, b in ob.BOXES.items() for _, tank in b["tank"][1]}


def reward_order():
    """확률표에 나오는 순서대로 보상 이름 목록 (표 정렬용)"""
    order = []

    def walk(node):
        if isinstance(node, list):
            for _, child in node:
                walk(child)
        elif node[0] != "BOX" and node[0] not in order:
            order.append(node[0])

    for b in ob.BOXES.values():
        for _, table in b["slots"]:
            walk(table)
    return order


def check_tables():
    """합계가 100%가 아닌 확률표를 찾아 문장 목록으로 돌려준다."""
    problems = []

    def total(table):
        return sum(w for w, _ in table)

    def walk(table, where):
        if abs(total(table) - 100) > 1e-9:
            problems.append(f"{where}: 합계 {total(table):g}%")
        for i, (_, node) in enumerate(table, 1):
            if isinstance(node, list):
                walk(node, f"{where} > {i}번째 항목")

    for b in ob.BOXES.values():
        walk(b["tank"][1], f"{b['name']} 전차")
        for i, (_, table) in enumerate(b["slots"], 1):
            walk(table, f"{b['name']} 보상{i}")
    return problems


# ── 한 번 연 결과 → 표 ───────────────────────────────────────
def chain_frame(start, opened, found, dup_tanks):
    """단계별로 '이 상자가 어디서 왔는지'와 연 개수"""
    dup_by_level = Counter(up for _, up in dup_tanks)
    rows = []
    for lvl in (1, 2, 3):
        from_dup = dup_by_level[lvl]
        rows.append({
            "단계": f"{lvl}단계",
            "처음 보유": start if lvl == 1 else 0,
            "보상으로 나옴": found[lvl] - from_dup,
            "중복 전차 대체": from_dup,
            "연 상자": opened[lvl],
        })
    return pd.DataFrame(rows).set_index("단계")


def tank_frame(new_tanks, dup_tanks):
    levels = tank_levels()
    dup = Counter(t for t, _ in dup_tanks)
    names = list(dict.fromkeys([*new_tanks, *dup]))
    rows = [{
        "전차": t,
        "나온 상자": f"{levels[t]}단계",
        "새로 획득": "O" if t in new_tanks else "",
        "중복(상자로 대체)": dup[t],
    } for t in names]
    return pd.DataFrame(rows, columns=["전차", "나온 상자", "새로 획득", "중복(상자로 대체)"])


def reward_frame(rewards):
    order = {name: i for i, name in enumerate(reward_order())}
    names = sorted(rewards, key=lambda n: order.get(n, len(order)))
    return pd.DataFrame({"보상": names, "수량": [rewards[n] for n in names]})


# ── 여러 번 반복 ─────────────────────────────────────────────
def histogram(values, bins=20):
    """연 상자 수의 분포. 인덱스는 구간 시작값, 값은 횟수."""
    s = pd.Series(values)
    lo, hi = int(s.min()), int(s.max())
    width = max(1, -(-(hi - lo + 1) // bins))        # 올림 나눗셈
    bucket = (s - lo) // width
    counts = bucket.value_counts().reindex(range(int(bucket.max()) + 1), fill_value=0)
    out = pd.DataFrame({"횟수": counts.to_numpy()},
                       index=[lo + b * width for b in counts.index])
    out.index.name = "연 상자 수 (구간 시작)"
    return out, width


def simulate_many(start, owned, runs, seed=None):
    """같은 조건으로 runs번 열어서 통계를 낸다."""
    if seed is not None:
        random.seed(seed)

    levels = tank_levels()
    totals = []
    level_sum = Counter()
    tank_hits = Counter()
    tank_dups = Counter()
    reward_sum = Counter()

    for _ in range(runs):
        opened, _found, rewards, new_tanks, dup_tanks = ob.open_all(start, owned, verbose=False)
        totals.append(sum(opened.values()))
        level_sum.update(opened)
        tank_hits.update(new_tanks)
        tank_dups.update(t for t, _ in dup_tanks)
        reward_sum.update(rewards)

    owned = set(owned)
    hist, width = histogram(totals)
    level_avg = pd.DataFrame(
        {"평균 개봉 수": [level_sum[l] / runs for l in (1, 2, 3)]},
        index=[f"{l}단계" for l in (1, 2, 3)],
    )
    tank_table = pd.DataFrame([{
        "전차": t,
        "나온 상자": f"{lvl}단계",
        "보유": "보유" if t in owned else "",
        "획득 확률(%)": round(tank_hits[t] / runs * 100, 1),
        "평균 중복 횟수": round(tank_dups[t] / runs, 2),
    } for t, lvl in levels.items()])

    order = {name: i for i, name in enumerate(reward_order())}
    names = sorted(reward_sum, key=lambda n: order.get(n, len(order)))
    reward_avg = pd.DataFrame({"보상": names,
                               "평균 수량": [round(reward_sum[n] / runs, 2) for n in names]})

    return {
        "runs": runs,
        "totals": pd.Series(totals),
        "hist": hist,
        "hist_width": width,
        "level_avg": level_avg,
        "tank_table": tank_table,
        "reward_avg": reward_avg,
    }
