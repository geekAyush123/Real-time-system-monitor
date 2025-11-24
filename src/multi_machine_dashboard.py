# Enhanced Gradio Dashboard with Multi-Machine Support
# Shows all machines separately + combined view

import gradio as gr
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from datetime import datetime, timedelta
try:
    from sklearn.ensemble import IsolationForest
    _ANOMALY_ENABLED = True
except ImportError:
    # scikit-learn not installed; anomaly features disabled
    _ANOMALY_ENABLED = False

def get_db_connection():
    return sqlite3.connect("data/system_metrics.db")

def get_all_machines():
    """Get list of ACTIVE machine IDs (only machines that sent data in last 2 minutes)"""
    try:
        conn = get_db_connection()
        # Only get machines that are actively sending data (last 2 minutes)
        time_threshold = (datetime.now() - timedelta(minutes=2)).strftime('%Y-%m-%d %H:%M:%S')
        query = f"""
            SELECT DISTINCT machine_id 
            FROM raw_metrics 
            WHERE timestamp >= '{time_threshold}'
            ORDER BY machine_id
        """
        df = pd.read_sql(query, conn)
        conn.close()
        machines = df['machine_id'].tolist()
        return machines
    except:
        return []

def get_machine_metrics(machine_id, time_range):
    """Get metrics for a specific machine"""
    try:
        conn = get_db_connection()
        
        # Calculate time filter
        if time_range == "Last 5 mins":
            minutes = 5
        elif time_range == "Last 15 mins":
            minutes = 15
        else:
            minutes = 60
        
        time_filter = (datetime.now() - timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
        
        query = f"""
            SELECT timestamp, cpu_usage, memory_usage, 
                   disk_io_read, disk_io_write,
                   net_io_sent, net_io_recv
            FROM raw_metrics 
            WHERE machine_id = '{machine_id}' 
            AND timestamp >= '{time_filter}'
            ORDER BY timestamp DESC 
            LIMIT 500
        """
        
        df = pd.read_sql(query, conn)
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    except Exception as e:
        print(f"Error getting metrics for {machine_id}: {e}")
        return pd.DataFrame()

def create_multi_machine_plot(metric_name, time_range, metric_label):
    """Create a plot showing all machines for a specific metric"""
    machines = get_all_machines()
    
    if not machines:
        fig = go.Figure()
        fig.update_layout(title=f"No data available - {metric_label}")
        return fig
    
    fig = go.Figure()
    
    for machine_id in machines:
        df = get_machine_metrics(machine_id, time_range)
        if not df.empty:
            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df[metric_name],
                mode='lines+markers',
                name=machine_id,
                marker=dict(size=4)
            ))
    
    fig.update_layout(
        title=f"{metric_label} - All Machines",
        xaxis_title="Time",
        yaxis_title=metric_label,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode='x unified'
    )
    
    return fig

def get_machine_summary():
    """Get summary statistics for all ACTIVE machines"""
    machines = get_all_machines()
    
    if not machines:
        return "### 🖥️ Connected Machines: 0\n\n❌ No active machines detected.\n\nMake sure producer is running on worker nodes."
    
    summary = f"### 🖥️ Connected Machines: {len(machines)}\n"
    summary += f"*Only showing machines active in last 2 minutes*\n\n"
    
    try:
        conn = get_db_connection()
        
        for machine_id in machines:
            query = f"""
                SELECT 
                    AVG(cpu_usage) as avg_cpu,
                    AVG(memory_usage) as avg_mem,
                    MAX(cpu_usage) as max_cpu,
                    MAX(memory_usage) as max_mem,
                    COUNT(*) as data_points
                FROM raw_metrics 
                WHERE machine_id = '{machine_id}'
                AND timestamp >= datetime('now', '-5 minutes')
            """
            
            df = pd.read_sql(query, conn)
            
            if not df.empty and df['data_points'].iloc[0] > 0:
                avg_cpu = df['avg_cpu'].iloc[0]
                avg_mem = df['avg_mem'].iloc[0]
                max_cpu = df['max_cpu'].iloc[0]
                max_mem = df['max_mem'].iloc[0]
                data_points = df['data_points'].iloc[0]
                
                summary += f"**{machine_id}**\n"
                summary += f"- CPU: Avg {avg_cpu:.1f}% | Max {max_cpu:.1f}%\n"
                summary += f"- Memory: Avg {avg_mem:.1f}% | Max {max_mem:.1f}%\n"
                summary += f"- Data points (last 5 min): {data_points}\n\n"
        
        conn.close()
    except Exception as e:
        summary += f"\nError: {str(e)}"
    
    return summary

def build_anomaly_dataframe(time_range):
    """Construct feature dataframe for anomaly detection across all machines."""
    machines = get_all_machines()
    rows = []
    for m in machines:
        df = get_machine_metrics(m, time_range)
        if df.empty:
            continue
        # Ensure sorted ascending
        df = df.sort_values('timestamp')
        # Compute deltas for disk and network
        df['disk_read_delta'] = df['disk_io_read'].diff().fillna(0)
        df['disk_write_delta'] = df['disk_io_write'].diff().fillna(0)
        df['net_sent_delta'] = df['net_io_sent'].diff().fillna(0)
        df['net_recv_delta'] = df['net_io_recv'].diff().fillna(0)
        # Take last N (50) samples for modeling
        sample_df = df.tail(50)
        for _, r in sample_df.iterrows():
            rows.append({
                'machine_id': m,
                'timestamp': r['timestamp'],
                'cpu': r['cpu_usage'],
                'mem': r['memory_usage'],
                'disk_read_d': r['disk_read_delta'],
                'disk_write_d': r['disk_write_delta'],
                'net_sent_d': r['net_sent_delta'],
                'net_recv_d': r['net_recv_delta']
            })
    if not rows:
        return pd.DataFrame()
    df_all = pd.DataFrame(rows)
    return df_all

_model_cache = {
    'model': None,
    'trained_rows': 0
}

def compute_anomalies(time_range):
    """Return anomaly dataframe with scores and flags. Gracefully degrade if disabled."""
    if not _ANOMALY_ENABLED:
        return pd.DataFrame(), "⚠️ scikit-learn not installed. Run: pip install scikit-learn"
    df_feat = build_anomaly_dataframe(time_range)
    if df_feat.empty:
        return pd.DataFrame(), "No data available for anomaly detection."
    feature_cols = ['cpu','mem','disk_read_d','disk_write_d','net_sent_d','net_recv_d']
    # Train / retrain if data size changed significantly
    if (_model_cache['model'] is None) or (abs(len(df_feat) - _model_cache['trained_rows']) > 100):
        iso = IsolationForest(n_estimators=120, contamination='auto', random_state=42)
        iso.fit(df_feat[feature_cols])
        _model_cache['model'] = iso
        _model_cache['trained_rows'] = len(df_feat)
    iso = _model_cache['model']
    scores = iso.decision_function(df_feat[feature_cols])
    preds = iso.predict(df_feat[feature_cols])  # -1 anomalous, 1 normal
    df_feat['score'] = scores
    df_feat['is_anomaly'] = (preds == -1)
    return df_feat, "Anomaly model applied successfully"

def build_anomaly_summary(df_anom, status_msg):
    if df_anom.empty:
        return f"### 🔍 Anomaly Detection\n\n{status_msg}"
    recent = df_anom.sort_values('timestamp').groupby('machine_id').tail(1)
    total_anomalies = int(df_anom['is_anomaly'].sum())
    md = ["### 🔍 Anomaly Detection", f"Status: {status_msg}", f"Total anomalous points (window): {total_anomalies}"]
    md.append("\n**Latest machine states:**")
    for _, row in recent.iterrows():
        flag = "🟢 Normal"
        if row['is_anomaly']:
            flag = "🔴 Anomalous"
        md.append(f"- {row['machine_id']}: {flag} (score {row['score']:.4f})")
    return "\n".join(md)

def create_anomaly_plot(df_anom):
    if df_anom.empty:
        fig = go.Figure()
        fig.update_layout(title="No anomaly data")
        return fig
    # Scatter CPU vs Memory color-coded
    fig = go.Figure()
    for m in df_anom['machine_id'].unique():
        sub = df_anom[df_anom['machine_id']==m]
        fig.add_trace(go.Scatter(
            x=sub['cpu'],
            y=sub['mem'],
            mode='markers',
            name=m,
            marker=dict(
                size=6,
                color=['red' if a else 'blue' for a in sub['is_anomaly']],
                opacity=0.7
            ),
            text=sub['timestamp'].astype(str)
        ))
    fig.update_layout(
        title='CPU vs Memory (Red = Anomaly)',
        xaxis_title='CPU %',
        yaxis_title='Memory %',
        template='plotly_white'
    )
    return fig

def update_dashboard(time_range):
    """Main dashboard update function"""
    summary = get_machine_summary()
    cpu_fig = create_multi_machine_plot('cpu_usage', time_range, 'CPU Usage (%)')
    mem_fig = create_multi_machine_plot('memory_usage', time_range, 'Memory Usage (%)')
    disk_read_fig = create_multi_machine_plot('disk_io_read', time_range, 'Disk Read (bytes)')
    disk_write_fig = create_multi_machine_plot('disk_io_write', time_range, 'Disk Write (bytes)')
    net_sent_fig = create_multi_machine_plot('net_io_sent', time_range, 'Network Sent (bytes)')
    net_recv_fig = create_multi_machine_plot('net_io_recv', time_range, 'Network Received (bytes)')
    # Anomaly section
    df_anom, status_msg = compute_anomalies(time_range)
    anomaly_summary = build_anomaly_summary(df_anom, status_msg)
    anomaly_plot = create_anomaly_plot(df_anom)
    return summary, cpu_fig, mem_fig, disk_read_fig, disk_write_fig, net_sent_fig, net_recv_fig, anomaly_summary, anomaly_plot

# Gradio UI
with gr.Blocks(title="Multi-Machine Monitor", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🖥️ Real-Time Multi-Machine System Monitor
    
    ### Distributed Monitoring Dashboard
    Monitor multiple machines in real-time from a single interface.
    Each line represents a different machine in your cluster.
    """)
    
    with gr.Row():
        time_range = gr.Dropdown(
            ["Last 5 mins", "Last 15 mins", "Last 1 hour"],
            value="Last 5 mins",
            label="⏰ Time Range",
            info="Select time window for all charts"
        )
        refresh_btn = gr.Button("🔄 Refresh Dashboard", variant="primary", scale=0)
    
    # Machine Summary
    with gr.Row():
        summary_md = gr.Markdown(label="Machine Summary")
    
    # CPU & Memory
    with gr.Tab("📊 CPU & Memory"):
        with gr.Row():
            with gr.Column():
                cpu_plot = gr.Plot(label="CPU Usage")
            with gr.Column():
                mem_plot = gr.Plot(label="Memory Usage")
    
    # Disk I/O
    with gr.Tab("💾 Disk I/O"):
        with gr.Row():
            with gr.Column():
                disk_read_plot = gr.Plot(label="Disk Read")
            with gr.Column():
                disk_write_plot = gr.Plot(label="Disk Write")
    
    # Network I/O
    with gr.Tab("🌐 Network I/O"):
        with gr.Row():
            with gr.Column():
                net_sent_plot = gr.Plot(label="Network Sent")
            with gr.Column():
                net_recv_plot = gr.Plot(label="Network Received")
    
    # Anomaly Tab
    with gr.Tab("🚨 Anomalies"):
        with gr.Row():
            anomaly_md = gr.Markdown(label="Anomaly Summary")
        with gr.Row():
            anomaly_plot = gr.Plot(label="Anomaly Scatter")

    # Refresh button action
    refresh_btn.click(
        fn=update_dashboard,
        inputs=[time_range],
        outputs=[summary_md, cpu_plot, mem_plot, disk_read_plot, disk_write_plot, net_sent_plot, net_recv_plot, anomaly_md, anomaly_plot]
    )

    # Auto-load on start
    demo.load(
        fn=update_dashboard,
        inputs=[time_range],
        outputs=[summary_md, cpu_plot, mem_plot, disk_read_plot, disk_write_plot, net_sent_plot, net_recv_plot, anomaly_md, anomaly_plot]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7863, share=True)
