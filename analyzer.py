import io
import statistics
from datetime import datetime
from typing import List, Dict

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

MOOD_EMOJI = {1: "😞", 2: "😐", 3: "🙂", 4: "😊", 5: "🤩"}
MOOD_LABEL = {1: "Ужасно", 2: "Плохо", 3: "Нормально", 4: "Хорошо", 5: "Отлично"}

def format_stats_text(entries: List[Dict], period_label: str) -> str:
    if not entries:
        return f"📭 Нет данных {period_label}.\n\nНачни с команды /add или кнопки «➕ Записать день»."

    moods = [e["mood"] for e in entries if e["mood"] is not None]
    works = [e["work_hours"] for e in entries if e["work_hours"] is not None]
    sleeps = [e["sleep_hours"] for e in entries if e["sleep_hours"] is not None]
    avg_mood  = statistics.mean(moods)  if moods  else 0
    avg_work  = statistics.mean(works)  if works  else 0
    avg_sleep = statistics.mean(sleeps) if sleeps else 0
    best_entry  = max(entries, key=lambda e: e["mood"] or 0)
    worst_entry = min(entries, key=lambda e: e["mood"] or 5)
    mood_icon = MOOD_EMOJI.get(round(avg_mood), "🙂")
    lines = [
        f"📊 *Статистика {period_label}* ({len(entries)} дн.)\n",
        f"*Настроение:*",
        f"  Среднее: {mood_icon} {avg_mood:.1f}/5",
        f"  Лучший день: {best_entry['entry_date']} — {MOOD_EMOJI.get(best_entry['mood'], '')} {best_entry['mood']}",
        f"  Худший день: {worst_entry['entry_date']} — {MOOD_EMOJI.get(worst_entry['mood'], '')} {worst_entry['mood']}",
        "",
        f"*Работа/учёба:*",
        f"  В среднем: {avg_work:.1f} ч/день",
        f"  Всего: {sum(works):.1f} ч",
        "",
        f"*Сон:*",
        f"  В среднем: {avg_sleep:.1f} ч/день",
    ]

    if avg_sleep < 6:
        lines.append("  ⚠️ Ты мало спишь! Попробуй добавить хотя бы час.")
    elif avg_sleep > 9:
        lines.append("  💤 Много спишь — возможно, стоит скорректировать режим.")
    else:
        lines.append("  ✅ Сон в норме — отлично!")

    return "\n".join(lines)


def format_insights_text(insights: Dict) -> str:
    lines = ["🔍  *Мои инсайты*\n"]

    if insights["sleep_mood"]:
        lines.append("🛌  *Сон и настроение:*")
        for row in insights["sleep_mood"]:
            bar = "█" * int(row["avg_mood"] * 2)
            lines.append(f"  {row['sleep_cat']}: {bar} {row['avg_mood']}/5 ({row['cnt']} дн.)")
        lines.append("")

    if insights["work_mood"]:
        lines.append("💼  *Работа/учёба и настроение:*")
        for row in insights["work_mood"]:
            bar = "█" * int(row["avg_mood"] * 2)
            lines.append(f"  {row['work_cat']}: {bar} {row['avg_mood']}/5 ({row['cnt']} дн.)")
        lines.append("")

    if insights["weekday_mood"]:
        best  = insights["weekday_mood"][0]
        worst = insights["weekday_mood"][-1]
        lines.append("📅 *Дни недели:*")
        lines.append(f"  🏆 Лучший: {best['weekday']} — {best['avg_mood']}/5")
        lines.append(f"  😔 Худший: {worst['weekday']} — {worst['avg_mood']}/5")
        lines.append("")

    if len(lines) <= 2:
        return "📭 Недостаточно данных для инсайтов. Добавь хотя бы 5–7 записей!"

    lines.append("_Чем больше записей — тем точнее выводы!_")
    return "\n".join(lines)

def format_history_text(entries: List[Dict]) -> str:
    if not entries:
        return "📭 История пуста. Начни добавлять записи!"

    lines = ["📋 *История записей* (последние 14 дней)\n"]
    for e in entries[:14]:
        mood_icon = MOOD_EMOJI.get(e["mood"], "—")
        comment = f"\n    💬 _{e['comment']}_" if e.get("comment") else ""
        lines.append(
            f"📅 *{e['entry_date']}*\n"
            f"  Настроение: {mood_icon} {e['mood']}/5 | "
            f"Работа: {e['work_hours']}ч | Сон: {e['sleep_hours']}ч{comment}"
        )
    return "\n\n".join(lines)

def build_chart(entries: List[Dict]) -> bytes | None:
    if not MATPLOTLIB_AVAILABLE or len(entries) < 2:
        return None

    entries_sorted = sorted(entries, key=lambda e: e["entry_date"])
    dates  = [datetime.fromisoformat(e["entry_date"]) for e in entries_sorted]
    moods  = [e["mood"]       or 0 for e in entries_sorted]
    sleeps = [e["sleep_hours"] or 0 for e in entries_sorted]
    works  = [e["work_hours"]  or 0 for e in entries_sorted]
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), facecolor="#1a1a2e")
    fig.suptitle("📊 Твоя статистика", color="white", fontsize=14, fontweight="bold")

    for ax in axes:
        ax.set_facecolor("#16213e")
        ax.tick_params(colors="white", labelsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
        for spine in ax.spines.values():
            spine.set_edgecolor("#0f3460")

    axes[0].plot(dates, moods, color="#e94560", linewidth=2, marker="o", markersize=5)
    axes[0].fill_between(dates, moods, alpha=0.2, color="#e94560")
    axes[0].set_ylabel("Настроение", color="white", fontsize=9)
    axes[0].set_ylim(0.5, 5.5)
    axes[0].set_yticks([1, 2, 3, 4, 5])
    axes[0].grid(axis="y", color="#0f3460", linestyle="--", alpha=0.5)
    axes[1].bar(dates, sleeps, color="#533483", width=0.6)
    axes[1].set_ylabel("Сон (ч)", color="white", fontsize=9)
    axes[1].grid(axis="y", color="#0f3460", linestyle="--", alpha=0.5)
    axes[1].axhline(y=8, color="#e94560", linestyle="--", alpha=0.7, linewidth=1)
    axes[2].bar(dates, works, color="#05b8cc", width=0.6)
    axes[2].set_ylabel("Работа (ч)", color="white", fontsize=9)
    axes[2].grid(axis="y", color="#0f3460", linestyle="--", alpha=0.5)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor="#1a1a2e")
    plt.close(fig)
    buf.seek(0)
    return buf.read()
