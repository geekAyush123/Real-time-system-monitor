import gradio as gr
import pandas as pd
import sqlite3
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import IsolationForest
import plotly.express as px
import plotly.graph_objects as go

from cache import Cache

# ------------- Helpers -------------

cache = Cache()


def get_db_connection():
    return sqlite3.connect("data/system_metrics.db")


def predict_usage(metric_name: str):
    """
    Predict future usage using linear regression on aggregated_metrics.
    Returns float or None.
    """
    try:
        conn = get_db_connection()
        df = pd.read_sql(
            f"""
            SELECT timestamp, {metric_name}
            FROM aggregated_metrics
            ORDER BY timestamp DESC
            LIMIT 200
            """,
            conn,
        )
        conn.close()
    except Exception:
        return None

    if len(df) < 2:
        return None

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["time_delta"] = (df["timestamp"] - df["timestamp"].min()).dt.total_seconds()

    X = df[["time_delta"]]
    y = df[metric_name]

    model = LinearRegression()
    model.fit(X, y)

    future_time = df["time_delta"].max() + 300  # next 5 mins
    prediction = model.predict(np.array([[future_time]]))
    return float(prediction[0])


def make_empty_fig(title: str, y_label: str = ""):
    fig = go.Figure()
    fig.update_layout(
        title=title,
        xaxis_title="Time",
        yaxis_title=y_label,
        template="plotly_white",
    )
    return fig


def detect_anomalies_isolation_forest(hist_df: pd.DataFrame, contamination: float):
    """
    Use IsolationForest to detect anomalies on historical metrics.
    Returns:
      anomalies_df (only anomalous rows),
      latest_is_anomaly (bool or None)
    """
    required_cols = [
        "avg_cpu_usage",
        "avg_memory_usage",
        "avg_disk_io_read",
        "avg_disk_io_write",
        "avg_net_io_sent",
        "avg_net_io_recv",
    ]

    if hist_df.empty or not all(col in hist_df.columns for col in required_cols):
        return pd.DataFrame(), None

    # Drop rows with NaN in the required columns
    data = hist_df.dropna(subset=required_cols).copy()
    if data.empty:
        return pd.DataFrame(), None

    X = data[required_cols]

    # Fit IsolationForest
    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
    )
    model.fit(X)

    scores = model.decision_function(X)
    labels = model.predict(X)  # -1 = anomaly, 1 = normal

    data["if_score"] = scores
    data["is_anomaly"] = (labels == -1)

    anomalies_df = data[data["is_anomaly"]].copy()

    # Check if latest row is anomaly
    latest_ts = data["timestamp"].max()
    latest_row = data[data["timestamp"] == latest_ts]
    if latest_row.empty:
        latest_is_anomaly = None
    else:
        latest_is_anomaly = bool(latest_row["is_anomaly"].iloc[0])

    return anomalies_df, latest_is_anomaly


def filter_by_time(hist_df: pd.DataFrame, time_range: str):
    if hist_df.empty:
        return hist_df

    hist_df = hist_df.copy()
    hist_df["timestamp"] = pd.to_datetime(hist_df["timestamp"])

    now = hist_df["timestamp"].max()
    if time_range == "Last 5 mins":
        delta = pd.Timedelta(minutes=5)
    elif time_range == "Last 15 mins":
        delta = pd.Timedelta(minutes=15)
    else:
        delta = pd.Timedelta(hours=1)

    return hist_df[hist_df["timestamp"] >= now - delta]


def update_dashboard(time_range: str, contamination: float):
    """
    Main Gradio callback.
    Returns:
      cpu_pred_md, mem_pred_md,
      cpu_fig, mem_fig, disk_fig, net_fig,
      top_cpu_fig, top_mem_fig,
      alerts_md, anomalies_table
    """
    # ---------- Predictions ----------
    cpu_pred = predict_usage("avg_cpu_usage")
    mem_pred = predict_usage("avg_memory_usage")

    if cpu_pred is not None:
        cpu_pred_md = f"**Predicted CPU Usage (next 5 min):** {cpu_pred:.2f}%"
    else:
        cpu_pred_md = "**Predicted CPU Usage (next 5 min):** Not enough data"

    if mem_pred is not None:
        mem_pred_md = f"**Predicted Memory Usage (next 5 min):** {mem_pred:.2f}%"
    else:
        mem_pred_md = "**Predicted Memory Usage (next 5 min):** Not enough data"

    # ---------- Live metrics via Cache ----------
    metrics = cache.get_latest_metrics(count=300)
    top_cpu = cache.get_top_processes("cpu")
    top_mem = cache.get_top_processes("mem")

    cpu_fig = make_empty_fig("CPU Usage (%)", "CPU %")
    mem_fig = make_empty_fig("Memory Usage (%)", "Memory %")
    disk_fig = make_empty_fig("Disk IO", "Bytes")
    net_fig = make_empty_fig("Network IO", "Bytes")
    top_cpu_fig = make_empty_fig("Top CPU Processes", "CPU %")
    top_mem_fig = make_empty_fig("Top Memory Processes", "Memory %")

    # ---------- CPU & Memory charts ----------
    if metrics:
        df = pd.DataFrame(metrics)
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
        df["cpu_usage"] = pd.to_numeric(df["cpu_usage"], errors="coerce")
        df["memory_usage"] = pd.to_numeric(df["memory_usage"], errors="coerce")

        # Tail for smooth plotting – you can also time-filter here based on df timestamps
        df = df.tail(50)

        cpu_fig = px.line(
            df,
            x="timestamp",
            y="cpu_usage",
            title="CPU Usage (%)",
        )
        cpu_fig.update_layout(
            template="plotly_white",
            margin=dict(l=40, r=20, t=40, b=40),
            xaxis_title="Time",
            yaxis_title="CPU %",
        )

        mem_fig = px.line(
            df,
            x="timestamp",
            y="memory_usage",
            title="Memory Usage (%)",
        )
        mem_fig.update_layout(
            template="plotly_white",
            margin=dict(l=40, r=20, t=40, b=40),
            xaxis_title="Time",
            yaxis_title="Memory %",
        )

    # ---------- Disk & Network + IsolationForest anomalies ----------
    anomalies_df = pd.DataFrame()
    latest_is_anomaly = None

    try:
        conn = get_db_connection()
        hist_df = pd.read_sql(
            "SELECT * FROM aggregated_metrics ORDER BY timestamp DESC LIMIT 500",
            conn,
        )
        conn.close()

        if not hist_df.empty:
            hist_df["timestamp"] = pd.to_datetime(hist_df["timestamp"])
            hist_df = filter_by_time(hist_df, time_range)

            if not hist_df.empty:
                # Disk
                disk_fig = px.line(
                    hist_df,
                    x="timestamp",
                    y=["avg_disk_io_read", "avg_disk_io_write"],
                    title="Disk IO (Read / Write)",
                )
                disk_fig.update_layout(
                    template="plotly_white",
                    margin=dict(l=40, r=20, t=40, b=40),
                    xaxis_title="Time",
                    yaxis_title="Bytes",
                    legend_title="Disk IO",
                )

                # Network
                net_fig = px.line(
                    hist_df,
                    x="timestamp",
                    y=["avg_net_io_sent", "avg_net_io_recv"],
                    title="Network IO (Sent / Received)",
                )
                net_fig.update_layout(
                    template="plotly_white",
                    margin=dict(l=40, r=20, t=40, b=40),
                    xaxis_title="Time",
                    yaxis_title="Bytes",
                    legend_title="Network IO",
                )

                # Isolation Forest anomalies
                anomalies_df, latest_is_anomaly = detect_anomalies_isolation_forest(
                    hist_df, contamination
                )

    except Exception:
        pass  # keep defaults

    # ---------- Top processes charts ----------
    if top_cpu:
        df_cpu = pd.DataFrame(top_cpu, columns=["Process", "CPU %"])
        top_cpu_fig = px.bar(
            df_cpu,
            x="Process",
            y="CPU %",
            title="Top CPU Processes",
        )
        top_cpu_fig.update_layout(
            template="plotly_white",
            xaxis_tickangle=-45,
            margin=dict(l=40, r=20, t=40, b=80),
            xaxis_title="Process",
            yaxis_title="CPU %",
        )

    if top_mem:
        df_mem = pd.DataFrame(top_mem, columns=["Process", "Memory %"])
        top_mem_fig = px.bar(
            df_mem,
            x="Process",
            y="Memory %",
            title="Top Memory Processes",
        )
        top_mem_fig.update_layout(
            template="plotly_white",
            xaxis_tickangle=-45,
            margin=dict(l=40, r=20, t=40, b=80),
            xaxis_title="Process",
            yaxis_title="Memory %",
        )

    # ---------- Alerts markdown (from IsolationForest) ----------
    if anomalies_df is not None and not anomalies_df.empty:
        lines = ["### 🔔 Isolation Forest – High Usage Anomalies Detected"]
        # Thoda concise table-type text
        for _, row in anomalies_df.tail(10).iterrows():
            ts = row["timestamp"]
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
            cpu = row.get("avg_cpu_usage", None)
            mem = row.get("avg_memory_usage", None)
            lines.append(
                f"- `{ts_str}` → CPU: **{cpu:.2f}%**, Memory: **{mem:.2f}%**"
            )

        if latest_is_anomaly:
            lines.append("\n**⚠️ Latest point is flagged as ANOMALOUS.**")
        else:
            lines.append("\nLatest point is **not anomalous**.")
        alerts_md = "\n".join(lines)
    else:
        alerts_md = "### ✅ Isolation Forest: No anomalies detected in the selected time range."

    # Anomalies table for more flexibility
    display_cols = [
        "timestamp",
        "avg_cpu_usage",
        "avg_memory_usage",
        "avg_disk_io_read",
        "avg_disk_io_write",
        "avg_net_io_sent",
        "avg_net_io_recv",
        "if_score",
    ]
    if anomalies_df is not None and not anomalies_df.empty:
        anomalies_table = anomalies_df[display_cols].sort_values("timestamp")
    else:
        anomalies_table = pd.DataFrame(columns=display_cols)

    return (
        cpu_pred_md,
        mem_pred_md,
        cpu_fig,
        mem_fig,
        disk_fig,
        net_fig,
        top_cpu_fig,
        top_mem_fig,
        alerts_md,
        anomalies_table,
    )


# ------------- Gradio UI -------------

with gr.Blocks(
    title="Real-Time System Monitor",
    analytics_enabled=False,
) as demo:
    gr.Markdown(
        """
    # 🖥️ Real-Time System Monitor

    Live, accessible dashboard for **CPU, Memory, Disk, Network**, with:
    - Next 5 min **usage predictions**
    - **Isolation Forest–based anomaly detection**
    - Top processes view
    """
    )

    with gr.Row():
        with gr.Column():
            time_range = gr.Dropdown(
                ["Last 5 mins", "Last 15 mins", "Last 1 hour"],
                value="Last 5 mins",
                label="Time Range",
                info="Choose the historical window for Disk/Network & anomaly detection.",
            )
        with gr.Column():
            contamination = gr.Slider(
                minimum=0.01,
                maximum=0.20,
                value=0.05,
                step=0.01,
                label="Anomaly Sensitivity (Isolation Forest contamination)",
                info="Higher = more anomalies detected.",
            )
        refresh_btn = gr.Button("🔄 Refresh dashboard", variant="primary")

    with gr.Row():
        cpu_pred_md = gr.Markdown(label="CPU Prediction")
        mem_pred_md = gr.Markdown(label="Memory Prediction")

    with gr.Tab("CPU / Memory"):
        with gr.Row():
            cpu_plot = gr.Plot(label="CPU Usage")
            mem_plot = gr.Plot(label="Memory Usage")

    with gr.Tab("Disk / Network"):
        with gr.Row():
            disk_plot = gr.Plot(label="Disk IO")
            net_plot = gr.Plot(label="Network IO")

    with gr.Tab("Top Processes"):
        with gr.Row():
            top_cpu_plot = gr.Plot(label="Top CPU Processes")
            top_mem_plot = gr.Plot(label="Top Memory Processes")

    with gr.Tab("Anomalies (Isolation Forest)"):
        alerts_box = gr.Markdown()
        anomalies_table = gr.Dataframe(
            headers=[
                "timestamp",
                "avg_cpu_usage",
                "avg_memory_usage",
                "avg_disk_io_read",
                "avg_disk_io_write",
                "avg_net_io_sent",
                "avg_net_io_recv",
                "if_score",
            ],
            interactive=True,
            wrap=True,
            label="Detected anomalous points",
        )

    # Button → dashboard update
    refresh_btn.click(
        fn=update_dashboard,
        inputs=[time_range, contamination],
        outputs=[
            cpu_pred_md,
            mem_pred_md,
            cpu_plot,
            mem_plot,
            disk_plot,
            net_plot,
            top_cpu_plot,
            top_mem_plot,
            alerts_box,
            anomalies_table,
        ],
    )

    # Initial auto-load
    demo.load(
        fn=update_dashboard,
        inputs=[time_range, contamination],
        outputs=[
            cpu_pred_md,
            mem_pred_md,
            cpu_plot,
            mem_plot,
            disk_plot,
            net_plot,
            top_cpu_plot,
            top_mem_plot,
            alerts_box,
            anomalies_table,
        ],
    )

if __name__ == "__main__":
    demo.launch()
