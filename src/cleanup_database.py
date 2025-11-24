"""
Cleanup Script - Remove old/inactive machine data
Run this periodically to keep database clean
"""

import sqlite3
from datetime import datetime, timedelta

def cleanup_old_data(hours=24):
    """
    Delete data older than specified hours
    Default: keeps last 24 hours of data
    """
    try:
        conn = sqlite3.connect('data/system_metrics.db')
        cursor = conn.cursor()
        
        # Calculate threshold time
        threshold = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
        
        # Delete old raw metrics
        cursor.execute("DELETE FROM raw_metrics WHERE timestamp < ?", (threshold,))
        deleted_raw = cursor.rowcount
        
        # Delete old aggregated metrics
        cursor.execute("DELETE FROM aggregated_metrics WHERE timestamp < ?", (threshold,))
        deleted_agg = cursor.rowcount
        
        # Delete old anomalies
        cursor.execute("DELETE FROM anomalies WHERE timestamp < ?", (threshold,))
        deleted_anomalies = cursor.rowcount
        
        # Delete old top processes
        cursor.execute("DELETE FROM top_processes WHERE timestamp < ?", (threshold,))
        deleted_processes = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"✅ Cleanup completed!")
        print(f"   - Raw metrics deleted: {deleted_raw}")
        print(f"   - Aggregated metrics deleted: {deleted_agg}")
        print(f"   - Anomalies deleted: {deleted_anomalies}")
        print(f"   - Top processes deleted: {deleted_processes}")
        print(f"   - Kept data from last {hours} hours")
        
        return True
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False

def cleanup_inactive_machines(minutes=5):
    """
    Delete data from machines that haven't sent data in last X minutes
    This removes disconnected/old machines
    """
    try:
        conn = sqlite3.connect('data/system_metrics.db')
        cursor = conn.cursor()
        
        # Get active machines (sent data recently)
        threshold = (datetime.now() - timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            SELECT DISTINCT machine_id 
            FROM raw_metrics 
            WHERE timestamp >= ?
        """, (threshold,))
        
        active_machines = [row[0] for row in cursor.fetchall()]
        
        if not active_machines:
            print("⚠️  No active machines found. Not deleting any data.")
            conn.close()
            return False
        
        # Delete data from inactive machines
        placeholders = ','.join('?' * len(active_machines))
        
        cursor.execute(f"""
            DELETE FROM raw_metrics 
            WHERE machine_id NOT IN ({placeholders})
        """, active_machines)
        
        deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"✅ Inactive machine cleanup completed!")
        print(f"   - Active machines: {len(active_machines)} -> {active_machines}")
        print(f"   - Deleted {deleted} records from inactive machines")
        
        return True
        
    except Exception as e:
        print(f"❌ Inactive machine cleanup failed: {e}")
        return False

def vacuum_database():
    """
    Optimize database after cleanup (reclaim disk space)
    """
    try:
        conn = sqlite3.connect('data/system_metrics.db')
        conn.execute("VACUUM")
        conn.close()
        print("✅ Database optimized (VACUUM completed)")
        return True
    except Exception as e:
        print(f"❌ Database optimization failed: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "="*50)
    print("DATABASE CLEANUP UTILITY")
    print("="*50 + "\n")
    
    print("Select cleanup option:")
    print("1. Remove old data (older than 24 hours)")
    print("2. Remove inactive machines (no data in last 5 minutes)")
    print("3. Both (recommended)")
    print("4. Optimize database (VACUUM)")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        cleanup_old_data(hours=24)
    elif choice == "2":
        cleanup_inactive_machines(minutes=5)
    elif choice == "3":
        cleanup_old_data(hours=24)
        cleanup_inactive_machines(minutes=5)
        vacuum_database()
    elif choice == "4":
        vacuum_database()
    else:
        print("Invalid choice!")
    
    print("\n" + "="*50 + "\n")
