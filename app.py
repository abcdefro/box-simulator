"""상자깡 시뮬레이터 (Streamlit)

실행:  streamlit run app.py
"""
import random

import streamlit as st

import box_view as bv
import open_box as ob

st.set_page_config(page_title="상자깡 시뮬레이터", page_icon="🎁", layout="wide")

st.title("상자깡 시뮬레이터")
st.caption("1단계 상자를 열면 안에서 나온 상위/하위 상자까지 전부 열어서 "
           "최종 개봉 수와 보상을 계산합니다.")

levels = bv.tank_levels()

# ── 사이드바: 입력 ───────────────────────────────────────────
with st.sidebar:
    st.header("설정")
    start = st.number_input("처음 가진 1단계 상자 수", min_value=1, max_value=100000,
                            value=215, step=1)
    owned = st.multiselect(
        "이미 보유한 전차",
        options=list(levels),
        format_func=lambda t: f"{t} ({levels[t]}단계)",
        help="보유한 전차가 나오면 그 전차 대신 한 단계 위 상자가 나옵니다. "
             "(3단계는 3단계 상자)",
    )
    fix_seed = st.checkbox("시드 고정 (같은 결과 재현)")
    seed = st.number_input("시드", min_value=0, value=7, step=1, disabled=not fix_seed)

    problems = bv.check_tables()
    if problems:
        with st.expander("확률표 점검"):
            st.caption("합이 100%가 아니어도 비율로 환산해서 뽑습니다. "
                       "표를 옮기다 빠진 항목이 없는지 확인해 보세요.")
            for p in problems:
                st.write("- " + p)

start = int(start)
seed_value = int(seed) if fix_seed else None

tab_one, tab_many = st.tabs(["한 번 열기", "여러 번 시뮬레이션"])


# ── 탭 1: 한 번 열기 ─────────────────────────────────────────
def show_single(saved):
    opened, found, rewards, new_tanks, dup_tanks = saved["result"]
    n = saved["start"]
    st.caption(f"처음 1단계 상자 {n:,}개 기준 결과입니다.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("연 상자 총 개수", f"{sum(opened.values()):,}")
    c2.metric("상자에서 나온 상자", f"{sum(found.values()):,}")
    c3.metric("새로 얻은 전차", f"{len(new_tanks):,}")
    c4.metric("중복 → 상위 상자", f"{len(dup_tanks):,}")

    st.subheader("연쇄 개봉 흐름")
    chain = bv.chain_frame(n, opened, found, dup_tanks)
    st.bar_chart(chain[["처음 보유", "보상으로 나옴", "중복 전차 대체"]])
    st.dataframe(chain)

    left, right = st.columns(2)
    with left:
        st.subheader("전차")
        if new_tanks or dup_tanks:
            st.dataframe(bv.tank_frame(new_tanks, dup_tanks))
        else:
            st.info("전차가 나오지 않았습니다.")
    with right:
        st.subheader("보상")
        st.dataframe(bv.reward_frame(rewards))


with tab_one:
    if st.button("상자 열기", type="primary", key="open_once"):
        if seed_value is not None:
            random.seed(seed_value)
        st.session_state["single"] = {
            "start": start,
            "result": ob.open_all(start, owned, verbose=False),
        }
    if "single" in st.session_state:
        show_single(st.session_state["single"])
    else:
        st.info("왼쪽에서 상자 수를 정하고 '상자 열기'를 눌러 주세요.")


# ── 탭 2: 여러 번 시뮬레이션 ─────────────────────────────────
def show_many(saved):
    data = saved["data"]
    runs = saved["runs"]
    totals = data["totals"]
    st.caption(f"처음 1단계 상자 {saved['start']:,}개로 {runs:,}번 반복한 결과입니다.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("평균 연 상자", f"{totals.mean():,.1f}")
    c2.metric("중앙값", f"{totals.median():,.0f}")
    c3.metric("최소", f"{totals.min():,}")
    c4.metric("최대", f"{totals.max():,}")

    st.subheader("연 상자 수 분포")
    st.bar_chart(data["hist"])
    st.caption(f"구간 폭 {data['hist_width']}개씩 묶었습니다.")

    left, right = st.columns(2)
    with left:
        st.subheader("단계별 평균 개봉 수")
        st.bar_chart(data["level_avg"])
        st.subheader("전차별 획득 확률")
        st.dataframe(data["tank_table"], hide_index=True)
    with right:
        st.subheader("평균 보상")
        st.dataframe(data["reward_avg"], hide_index=True)


with tab_many:
    runs = st.number_input("반복 횟수", min_value=10, max_value=2000, value=200, step=10)
    runs = int(runs)
    if start * runs > 2_000_000:
        st.warning("상자 수 × 반복 횟수가 커서 계산이 오래 걸릴 수 있습니다.")
    if st.button("시뮬레이션 실행", type="primary", key="run_many"):
        with st.spinner("계산 중..."):
            st.session_state["many"] = {
                "start": start,
                "runs": runs,
                "data": bv.simulate_many(start, owned, runs, seed_value),
            }
    if "many" in st.session_state:
        show_many(st.session_state["many"])
    else:
        st.info("'시뮬레이션 실행'을 누르면 같은 조건으로 여러 번 열어서 평균과 확률을 보여줍니다.")
