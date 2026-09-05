import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Tuple

# --- Streak Metrics Calculator ---

def calculate_journal_streaks(entries: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Calculates the current streak and maximum streak of consecutive journaling days.
    """
    if not entries:
        return 0, 0

    # Extract dates from entries
    dates = set()
    for entry in entries:
        created_val = entry.get("created_at")
        if isinstance(created_val, datetime):
            dates.add(created_val.date())
        elif isinstance(created_val, date):
            dates.add(created_val)
        else:
            try:
                # Fallback parse for string formats
                dt = datetime.fromisoformat(str(created_val).replace('Z', '+00:00'))
                dates.add(dt.date())
            except Exception:
                try:
                    dt = datetime.strptime(str(created_val)[:10], "%Y-%m-%d")
                    dates.add(dt.date())
                except Exception:
                    continue

    if not dates:
        return 0, 0

    sorted_dates = sorted(list(dates), reverse=True)
    today = date.today()
    yesterday = today - timedelta(days=1)

    # If the user hasn't journaled today or yesterday, the current streak is 0
    if sorted_dates[0] != today and sorted_dates[0] != yesterday:
        current_streak = 0
    else:
        current_streak = 1
        for i in range(len(sorted_dates) - 1):
            diff = (sorted_dates[i] - sorted_dates[i+1]).days
            if diff == 1:
                current_streak += 1
            elif diff > 1:
                break

    # Calculate Max Streak
    max_streak = 0
    temp_streak = 0
    
    # Sort ascending to calculate max streak
    sorted_asc_dates = sorted(list(dates))
    if sorted_asc_dates:
        temp_streak = 1
        max_streak = 1
        for i in range(len(sorted_asc_dates) - 1):
            diff = (sorted_asc_dates[i+1] - sorted_asc_dates[i]).days
            if diff == 1:
                temp_streak += 1
            elif diff > 1:
                max_streak = max(max_streak, temp_streak)
                temp_streak = 1
        max_streak = max(max_streak, temp_streak)

    return current_streak, max_streak

# --- Visualizations with Dynamic Theme Adaptation ---

def get_chart_theme_tokens(theme: str) -> Dict[str, Any]:
    """
    Returns color and typography parameters matching the active UI theme.
    Exclusively supports '🍂 Warm Charcoal & Amber' (default) and '🔥 Obsidian Flame'.
    """
    if "Obsidian" in theme or "Flame" in theme:
        return {
            "font_color": "#F5F5F7",
            "title_color": "#F5F5F7",
            "font_family": "Playfair Display, Georgia, serif",
            "tick_color": "#A1A1AA",
            "grid_color": "rgba(255, 76, 0, 0.12)",
            "line_color": "#FF4C00",
            "marker_color": "#FF7A33",
            "bar_scale": px.colors.sequential.Sunsetdark,
            "paper_bg": "rgba(0, 0, 0, 0)",
            "plot_bg": "rgba(0, 0, 0, 0)"
        }
    else:  # 🍂 Warm Charcoal & Amber (Default)
        return {
            "font_color": "#EAE3D8",
            "title_color": "#EAE3D8",
            "font_family": "Roboto, sans-serif",
            "tick_color": "#B0A695",
            "grid_color": "#443A2E",
            "line_color": "#E8B25C",
            "marker_color": "#C9852F",
            "bar_scale": px.colors.sequential.YlOrBr,
            "paper_bg": "#2A2420",
            "plot_bg": "#2A2420"
        }

def generate_mood_trend_chart(entries: List[Dict[str, Any]], theme: str = "🍂 Warm Charcoal & Amber") -> go.Figure:
    """
    Generates a Plotly line chart representing user mood over time, dynamically themed.
    """
    tokens = get_chart_theme_tokens(theme)

    if not entries:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor=tokens["paper_bg"],
            plot_bgcolor=tokens["plot_bg"],
            xaxis={'visible': False},
            yaxis={'visible': False},
            annotations=[{
                'text': 'No journal entry data available yet.',
                'xref': 'paper', 'yref': 'paper',
                'showarrow': False, 'font': {'size': 15, 'color': tokens['tick_color']}
            }]
        )
        return fig

    # Process entry data
    chart_data = []
    for entry in entries:
        created_val = entry.get("created_at")
        if isinstance(created_val, datetime):
            dt = created_val
        else:
            try:
                dt = datetime.fromisoformat(str(created_val).replace('Z', '+00:00'))
            except Exception:
                try:
                    dt = datetime.strptime(str(created_val)[:19], "%Y-%m-%d %H:%M:%S")
                except Exception:
                    dt = datetime.utcnow()

        chart_data.append({
            "Date": dt.strftime("%Y-%m-%d %H:%M"),
            "Mood Score": entry.get("mood_score", 5),
            "Mood Category": entry.get("mood_category", "Neutral"),
            "Summary": entry.get("summary", "")
        })

    # Sort chronological (oldest to newest for trajectory)
    df = pd.DataFrame(chart_data)
    df['Date_parsed'] = pd.to_datetime(df['Date'])
    df = df.sort_values(by='Date_parsed')

    # Draw Chart
    fig = px.line(
        df,
        x="Date_parsed",
        y="Mood Score",
        text="Mood Category",
        title="Mood Trajectory over Time",
        labels={"Date_parsed": "Date", "Mood Score": "Mood Level (1-10)"},
        markers=True
    )

    # Style line and markers
    fig.update_traces(
        line=dict(color=tokens["line_color"], width=3),
        marker=dict(size=8, color=tokens["marker_color"], symbol="circle"),
        textposition="top center",
        hoverinfo="text",
        hovertemplate="<b>Date:</b> %{x|%Y-%m-%d %H:%M}<br><b>Mood Score:</b> %{y}/10<br><b>Category:</b> %{text}<extra></extra>"
    )

    fig.update_layout(
        paper_bgcolor=tokens["paper_bg"],
        plot_bgcolor=tokens["plot_bg"],
        font=dict(color=tokens["font_color"], family=tokens["font_family"]),
        title_font=dict(size=18, color=tokens["title_color"], family=tokens["font_family"]),
        xaxis=dict(
            showgrid=True,
            gridcolor=tokens["grid_color"],
            tickfont=dict(color=tokens["tick_color"]),
            linecolor=tokens["grid_color"]
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=tokens["grid_color"],
            tickfont=dict(color=tokens["tick_color"]),
            linecolor=tokens["grid_color"],
            range=[0.5, 10.5],
            dtick=1
        ),
        margin=dict(l=40, r=40, t=50, b=40)
    )

    return fig

def generate_theme_distribution_chart(entries: List[Dict[str, Any]], theme: str = "🍂 Warm Charcoal & Amber") -> go.Figure:
    """
    Generates a Plotly bar chart depicting reflection themes breakdown, dynamically themed.
    """
    tokens = get_chart_theme_tokens(theme)

    if not entries:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor=tokens["paper_bg"],
            plot_bgcolor=tokens["plot_bg"],
            xaxis={'visible': False},
            yaxis={'visible': False},
            annotations=[{
                'text': 'No themes found yet.',
                'xref': 'paper', 'yref': 'paper',
                'showarrow': False, 'font': {'size': 15, 'color': tokens['tick_color']}
            }]
        )
        return fig

    # Gather themes count
    theme_counts = {}
    for entry in entries:
        tags = entry.get("theme_tags") or []
        for tag in tags:
            tag_clean = tag.strip().title()
            if tag_clean:
                theme_counts[tag_clean] = theme_counts.get(tag_clean, 0) + 1

    if not theme_counts:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor=tokens["paper_bg"],
            plot_bgcolor=tokens["plot_bg"],
            annotations=[{
                'text': 'Write entries to analyze themes.',
                'xref': 'paper', 'yref': 'paper',
                'showarrow': False, 'font': {'size': 15, 'color': tokens['tick_color']}
            }]
        )
        return fig

    # Convert to DataFrame
    df = pd.DataFrame(list(theme_counts.items()), columns=["Theme", "Occurrences"])
    df = df.sort_values(by="Occurrences", ascending=True)

    # Draw Horizontal Bar Chart
    fig = px.bar(
        df,
        x="Occurrences",
        y="Theme",
        orientation="h",
        title="Journal Reflection Themes",
        color="Occurrences",
        color_continuous_scale=tokens["bar_scale"]
    )

    fig.update_traces(
        marker_line_color=tokens["grid_color"],
        marker_line_width=1,
        opacity=0.88,
        hovertemplate="<b>Theme:</b> %{y}<br><b>Occurrences:</b> %{x}<extra></extra>"
    )

    fig.update_layout(
        paper_bgcolor=tokens["paper_bg"],
        plot_bgcolor=tokens["plot_bg"],
        font=dict(color=tokens["font_color"], family=tokens["font_family"]),
        title_font=dict(size=18, color=tokens["title_color"], family=tokens["font_family"]),
        coloraxis_showscale=False,
        xaxis=dict(
            showgrid=True,
            gridcolor=tokens["grid_color"],
            tickfont=dict(color=tokens["tick_color"]),
            dtick=1
        ),
        yaxis=dict(
            showgrid=False,
            tickfont=dict(color=tokens["tick_color"])
        ),
        margin=dict(l=40, r=40, t=50, b=40)
    )

    return fig
