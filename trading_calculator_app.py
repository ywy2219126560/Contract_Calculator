import streamlit as st

st.set_page_config(
    page_title="加密货币交易计算器",
    page_icon="📈",
    layout="wide"
)

# ===== 初始化 =====
def init():
    defaults = {
        "open_price": None,
        "initial_margin": None,
        "maintenance_margin_percent": 0.4,
        "leverage": None,
        "liquidation_price": None,
        "take_profit_price": None,
        "position_type": 1,
        "mode": "用强平算杠杆"
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init()

col_left, _, col_right = st.columns([1, 0.05, 1])

# ================= 输入 =================
with col_left:
    with st.container(border=True):
        st.subheader("⚙️ 参数设置")

        position_type = st.radio(
            "交易方向",
            [1, 2],
            format_func=lambda x: "做多" if x == 1 else "做空",
            key="position_type",
            horizontal=True
        )

        mm_percent = st.slider(
            "维持保证金率 (%)",
            0.1, 10.0,
            step=0.1,
            format="%.1f",
            value=0.4
        )
        mmr = mm_percent / 100

        open_price = st.number_input("开仓价格", value=None, step=10.0, format="%.2f")
        initial_margin = st.number_input("初始保证金", value=None, step=1.0, format="%.2f")
        take_profit_price = st.number_input("止盈价格", value=None, step=10.0, format="%.2f")

        liquidation_price_input = st.number_input(
            "强平价格",
            value=None,
            step=10.0,
            format="%.2f",
            disabled=(st.session_state.mode == "用杠杆算强平")
        )

        mode = st.radio(
            "计算方式",
            ["用强平算杠杆", "用杠杆算强平"],
            key="mode"
        )

        leverage_input = st.slider(
            "杠杆",
            1, 150,
            step=1,
            value=10,
            disabled=(mode == "用强平算杠杆")
        )

# ================= 计算 =================
error_msg = None
leverage = 0
liquidation_price = 0

if open_price and initial_margin and take_profit_price:

    if mode == "用杠杆算强平":
        leverage = leverage_input
        if position_type == 1 and leverage != 0:
            liquidation_price = open_price * (1 - 1/leverage) / (1 - mmr)
        elif position_type == 2 and leverage != 0:
            liquidation_price = open_price * (1 + 1/leverage) / (1 + mmr)
    else:
        liquidation_price = liquidation_price_input
        if position_type == 1 and liquidation_price and liquidation_price < open_price:
            denom = open_price - liquidation_price * (1 - mmr)
            leverage = open_price / denom if denom != 0 else 0
        elif position_type == 2 and liquidation_price and liquidation_price > open_price:
            denom = liquidation_price * (1 + mmr) - open_price
            leverage = open_price / denom if denom != 0 else 0
        else:
            leverage = 0

# ===== 参数校验 =====
valid = True
if open_price and liquidation_price and take_profit_price:
    if position_type == 1:
        if not (liquidation_price < open_price < take_profit_price):
            error_msg = "❌ 做多时必须满足：强平价 < 开仓价 < 止盈价"
            valid = False
    else:
        if not (take_profit_price < open_price < liquidation_price):
            error_msg = "❌ 做空时必须满足：止盈价 < 开仓价 < 强平价"
            valid = False
else:
    valid = False

# ===== 安全格式化函数 =====
def safe_number(val, suffix=""):
    if val is None or val != val or val in [float('inf'), float('-inf')]:
        return "-"
    return f"{val:.2f}{suffix}"

def safe_rr(profit, loss):
    try:
        if loss == 0:
            return "-"
        rr = profit / loss
        return f"{rr:.2f}:1"
    except:
        return "-"

# ================= 输出 =================
with col_right:
    # ===== 上：风险评估 =====
    with st.container(border=True):
        st.subheader("⚠️ 风险评估")
        if valid:
            loss = open_price - liquidation_price if position_type == 1 else liquidation_price - open_price
            profit = take_profit_price - open_price if position_type == 1 else open_price - take_profit_price

            # 杠杆风险提示
            if leverage > 50:
                st.error(f"🔴 杠杆风险：{safe_number(leverage,'x')}（极高风险）")
            elif leverage > 20:
                st.warning(f"🟡 杠杆风险：{safe_number(leverage,'x')}（中等风险）")
            else:
                st.success(f"🟢 杠杆风险：{safe_number(leverage,'x')}（相对安全）")

            # 盈亏比提示
            rr_text = safe_rr(profit, loss)
            if rr_text == "-":
                st.warning("⚠️ 盈亏比无法计算")
            else:
                rr_val = profit / loss
                if rr_val < 1:
                    st.error(f"🔴 盈亏比：{rr_text}（不划算）")
                elif rr_val < 2:
                    st.warning(f"🟡 盈亏比：{rr_text}（一般）")
                else:
                    st.success(f"🟢 盈亏比：{rr_text}（优秀）")

    # ===== 下：计算结果 =====
    with st.container(border=True):
        st.subheader("📊 计算结果")
        if valid:
            total = initial_margin * leverage
            qty = total / open_price if open_price != 0 else 0
            change = (liquidation_price - open_price) / open_price * 100 if open_price != 0 else 0
            profit_percent = (take_profit_price - open_price) / open_price * 100 if position_type == 1 else (open_price - take_profit_price) / open_price * 100

            # 第1行
            r1c1, r1c2, r1c3 = st.columns(3)
            with r1c1:
                st.metric("方向", "做多" if position_type == 1 else "做空")
            with r1c2:
                st.metric("杠杆", safe_number(leverage,"x"))
            with r1c3:
                st.metric("仓位价值", safe_number(total))

            # 第2行
            r2c1, r2c2, r2c3 = st.columns(3)
            with r2c1:
                st.metric("盈亏比", safe_rr(profit, loss),
                          delta=f"+{safe_number(profit)} / -{safe_number(loss)}")
            with r2c2:
                st.metric("爆仓幅度", safe_number(change,"%"))
            with r2c3:
                st.metric("止盈收益率", safe_number(profit_percent,"%"))

            # 第3行
            r3c1, r3c2, r3c3 = st.columns(3)
            with r3c1:
                st.metric("币数量", safe_number(qty))
            with r3c2:
                st.metric("强平价格", safe_number(liquidation_price))
            with r3c3:
                st.empty()
        else:
            st.info("请先输入有效参数以计算结果。")
