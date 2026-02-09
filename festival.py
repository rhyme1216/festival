"""
春节请假策略小工具

根据同事最新的休假统计，自动给出员工 A 在
春节前后连续 3 天年假的最优放假方案。

约束（按题意写死在逻辑里）：
- 法定假期：2-15 ~ 2-23
- 节前必须连续工作 6 天（其中 2-14 为周六上班）
- 节后必须连续工作 5 天（其中 2-28 为周六上班）
- 员工 A 只有 3 天年假，且这 3 天必须和法定假期首尾连续：
  只能从 {12,13,14} 向前接，和从 {25,26,27} 向后接。
  所以 4 类合法方案：
    - 全在节前：12,13,14
    - 2 前 1 后：13,14,25
    - 1 前 2 后：14,25,26
    - 全在节后：25,26,27

脚本逻辑：
1. 交互式输入每个候选日期“同事请假比例”（可写 0.48 或 25/52）。
2. 对 4 类方案计算综合得分：
   - 连续工作越长，惩罚越大；
   - 你在 p 很低的日子休假（多数人上班），惩罚越大；
3. 输出得分最高的方案。
"""


def w(n: int) -> float:
    """连续上班惩罚函数：从第 6 天起指数增加。"""
    return 1.3 ** max(n - 5, 0)


def work(vacation_days):
    """根据题目给出的排班，计算连续上班块长度列表。

    简化模型：
    - 节前原本连续上班：2-09 ~ 2-14，共 6 天；
    - 节后原本连续上班：2-25 ~ 2-29，共 5 天；
    - 2-15 ~ 2-24 为法定假期；
    - 你的 3 天年假只能放在 {12,13,14,25,26,27} 中，
      会把对应的工作日变成休息日，从而缩短或打断连续工作段。
    """
    base_work_days = set(range(9, 15)) | set(range(25, 29))  # 9-14, 24-28
    actual_work_days = sorted(base_work_days - set(vacation_days))

    if not actual_work_days:
        return []

    blocks = []
    start = actual_work_days[0]
    prev = start
    for day in actual_work_days[1:]:
        if day == prev + 1:
            prev = day
        else:
            blocks.append(prev - start + 1)
            start = prev = day
    blocks.append(prev - start + 1)
    return blocks


def score(vacation_days, p_dict, alpha: float = 1.0, beta: float = 1.0):
        """对一组 3 天年假方案打分：
        - fatigue: 连续上班疲劳成本（越大越累）
        - disturb: 休假被打扰成本（休假当天仍在上班的同事比例之和）

        α、β 为权重：
            total_cost = α * fatigue + β * disturb
            score      = 1 / total_cost

        α 越大，说明你越在意“不要太累”；
        β 越大，说明你越在意“休假时不要被打扰”。
        """

        fatigue = sum(w(n) for n in work(vacation_days))
        disturb = sum(1 - p_dict[day] for day in vacation_days)

        total_cost = alpha * fatigue + beta * disturb
        return 1.0 / total_cost


def generate_plans():
    """生成所有合法的 3 天年假方案（按题目约束写死）：
    - pre_days: [12, 13, 14]（节前可以请假的天）
    - post_days: [25, 26, 27]（节后可以请假的天）
    3 天必须与法定假首尾连续，因此：
      k_pre 天必须是 pre_days 的最后 k_pre 天（紧挨 15 号），
      k_post 天必须是 post_days 的前 k_post 天（紧挨 24 号）。
    """

    pre_days = [12, 13, 14]
    post_days = [24, 25, 26]
    total_vac = 3

    plans = []
    for k_pre in range(0, total_vac + 1):
        k_post = total_vac - k_pre
        if k_pre > len(pre_days) or k_post > len(post_days):
            continue
        pre_part = pre_days[-k_pre:] if k_pre > 0 else []
        post_part = post_days[:k_post] if k_post > 0 else []
        plans.append(pre_part + post_part)
    return plans


def parse_probability(text: str) -> float:
    """支持 0.48 或 25/52 两种输入格式。"""

    text = text.strip()
    if not text:
        raise ValueError("空输入")
    if "/" in text:
        a, b = text.split("/", 1)
        return float(a) / float(b)
    return float(text)


def ask_probabilities(candidate_days, default_probs=None):
    """交互式输入候选日期的同事请假比例。

    - candidate_days: [12,13,14,25,26,27]
    - default_probs: 可选默认值 dict(day -> p)
    """

    p = {}
    for day in candidate_days:
        default = None
        if default_probs and day in default_probs:
            default = default_probs[day]

        while True:
            if default is not None:
                prompt = (
                    f"请输入 2-{day:02d} 同事请假比例（小数或 a/b），回车使用默认 {default:.4f}： "
                )
            else:
                prompt = (
                    f"请输入 2-{day:02d} 同事请假比例（小数或 a/b，回车默认 0）： "
                )

            s = input(prompt).strip()
            if not s:
                p[day] = default if default is not None else 0.0
                break
            try:
                value = parse_probability(s)
                if not (0.0 <= value <= 1.0):
                    print("请输入 0~1 之间的小数，或合法的 a/b 比例。")
                    continue
                p[day] = value
                break
            except Exception:
                print("输入格式错误，请重新输入。示例：0.48 或 25/52")

    return p


def main():
    # 默认值来自你当前的调研数据，可随时调整：
    default_counts = {
        12: (6, 31),
        13: (18, 31),
        14: (26, 31),
        # 24 在法定假期中，不是 A 的可选年假日，这里不使用
        24: (18, 31),
        25: (14, 31),
        26: (1, 31),
        # 没有统计到的数据默认 0，用户可以自行输入
    }
    default_probs = {d: a / b for d, (a, b) in default_counts.items()}

    candidate_days = [12, 13, 14, 24, 25, 26]

    print("=== 春节请假策略计算小工具 ===")
    print("说明：输入每个日期同事的休假比例，支持 0.48 或 25/52 形式。")
    print("若直接回车，将使用脚本内的默认值（如有），或默认 0。")
    print()

    P = ask_probabilities(candidate_days, default_probs)

    # 让用户调节疲劳权重 α 和被打扰权重 β
    def ask_weight(name, default):
        while True:
            s = input(f"请输入权重 {name}（回车默认 {default}）： ").strip()
            if not s:
                return default
            try:
                v = float(s)
                if v <= 0:
                    print("权重必须为正数，请重新输入。")
                    continue
                return v
            except Exception:
                print("输入格式错误，请输入数字，例如 1 或 2.5。")

    print()
    print("现在设置权重：")
    print("α：控制对\"连续工作疲劳\"的敏感度，越大越不想太累。")
    print("β：控制对\"休假被打扰\"的敏感度，越大越想休假更清净。")

    alpha = ask_weight("α", 1.0)
    beta = ask_weight("β", 1.0)

    plans = generate_plans()
    scored = [(plan, score(plan, P, alpha, beta)) for plan in plans]
    scored.sort(key=lambda x: x[1], reverse=True)

    best_plan, best_score = scored[0]

    def fmt_plan(plan):
        return [f"2-{d:02d}" for d in plan]

    print()
    print("所有合法方案按得分从高到低：")
    for plan, s in scored:
        print(f"方案 {fmt_plan(plan)} -> Score = {s:.6f}")

    print()
    print("推荐最优 3 天年假：", fmt_plan(best_plan))
    print(f"综合得分（越高越好）：{best_score:.6f}")


if __name__ == "__main__":
    main()