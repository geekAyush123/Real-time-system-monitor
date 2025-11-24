# Enhanced Gradio Dashboard with Multi-Machine Support
# Shows all machines separately + combined view

import gradio as gr
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

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

def update_dashboard(time_range):
    """Main dashboard update function"""
    
    # Get summary
    summary = get_machine_summary()
    
    # Create plots for each metric
    cpu_fig = create_multi_machine_plot('cpu_usage', time_range, 'CPU Usage (%)')
    mem_fig = create_multi_machine_plot('memory_usage', time_range, 'Memory Usage (%)')
    disk_read_fig = create_multi_machine_plot('disk_io_read', time_range, 'Disk Read (bytes)')
    disk_write_fig = create_multi_machine_plot('disk_io_write', time_range, 'Disk Write (bytes)')
    net_sent_fig = create_multi_machine_plot('net_io_sent', time_range, 'Network Sent (bytes)')
    net_recv_fig = create_multi_machine_plot('net_io_recv', time_range, 'Network Received (bytes)')
    
    return summary, cpu_fig, mem_fig, disk_read_fig, disk_write_fig, net_sent_fig, net_recv_fig

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
    
    # Refresh button action
    refresh_btn.click(
        fn=update_dashboard,
        inputs=[time_range],
        outputs=[summary_md, cpu_plot, mem_plot, disk_read_plot, disk_write_plot, net_sent_plot, net_recv_plot]
    )
    
    # Auto-load on start
    demo.load(
        fn=update_dashboard,
        inputs=[time_range],
        outputs=[summary_md, cpu_plot, mem_plot, disk_read_plot, disk_write_plot, net_sent_plot, net_recv_plot]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7863, share=True)
