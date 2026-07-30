"""压力测试旁路监控 —— 采集系统资源（CPU / 内存 / 磁盘 I/O）。

用法：
    # 后台运行，每秒采样，写入 CSV
    python tests/stress/scripts/monitor_resources.py --output reports/scenario4_resources.csv --duration 600

    # 持续运行直到手动 Ctrl+C
    python tests/stress/scripts/monitor_resources.py
"""

import argparse
import csv
import time
import os
import sys

try:
    import psutil
except ImportError:
    print("请先安装 psutil: pip install psutil")
    sys.exit(1)


def get_process_info():
    """获取当前 Python 进程及其子进程的资源使用。"""
    try:
        # 获取所有 Python 进程（uvicorn workers）
        all_procs = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info["cmdline"] or [])
                if "uvicorn" in cmdline or "python" in cmdline:
                    all_procs.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        total_cpu = 0.0
        total_memory = 0
        total_handles = 0
        total_threads = 0

        for proc in all_procs:
            try:
                total_cpu += proc.cpu_percent(interval=0)
                mem_info = proc.memory_info()
                total_memory += mem_info.rss
                total_handles += proc.num_handles() if hasattr(proc, "num_handles") else 0
                total_threads += proc.num_threads()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return {
            "process_count": len(all_procs),
            "cpu_percent": round(total_cpu, 1),
            "memory_mb": round(total_memory / 1024 / 1024, 1),
            "handles": total_handles,
            "threads": total_threads,
        }
    except Exception as e:
        return {"error": str(e)}


def get_system_info():
    """获取系统级别资源。"""
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_io_counters()
    net = psutil.net_io_counters()

    return {
        "system_cpu_percent": cpu,
        "system_memory_percent": mem.percent,
        "disk_read_kbps": round(disk.read_bytes / 1024, 1) if disk else 0,
        "disk_write_kbps": round(disk.write_bytes / 1024, 1) if disk else 0,
        "net_sent_kbps": round(net.bytes_sent / 1024, 1) if net else 0,
        "net_recv_kbps": round(net.bytes_recv / 1024, 1) if net else 0,
    }


def check_wal_size(project_root: str) -> int:
    """检查 SQLite WAL 文件大小（bytes）。"""
    wal_path = os.path.join(project_root, "data", "app.db-wal")
    if os.path.exists(wal_path):
        return os.path.getsize(wal_path)
    return 0


def main():
    parser = argparse.ArgumentParser(description="压力测试资源监控")
    parser.add_argument("--output", default=None, help="CSV 输出文件路径")
    parser.add_argument("--duration", type=int, default=0, help="持续时间（秒），0=持续运行")
    parser.add_argument("--interval", type=float, default=1.0, help="采样间隔（秒）")
    parser.add_argument(
        "--project-root",
        default=os.path.join(os.path.dirname(__file__), "..", "..", ".."),
        help="项目根目录",
    )
    args = parser.parse_args()

    project_root = os.path.abspath(args.project_root)
    output_file = args.output
    if output_file:
        output_file = os.path.abspath(output_file)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # CSV 表头
    fieldnames = [
        "timestamp",
        "process_count",
        "cpu_percent",
        "memory_mb",
        "handles",
        "threads",
        "system_cpu_percent",
        "system_memory_percent",
        "disk_read_kbps",
        "disk_write_kbps",
        "net_sent_kbps",
        "net_recv_kbps",
        "wal_size_bytes",
    ]

    csv_file = None
    writer = None
    if output_file:
        csv_file = open(output_file, "w", newline="", encoding="utf-8")
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        print(f"监控输出: {output_file}")

    start_time = time.time()
    iteration = 0
    prev_disk = psutil.disk_io_counters()
    prev_net = psutil.net_io_counters()

    try:
        while True:
            iteration += 1
            timestamp = time.time()

            proc_info = get_process_info()
            sys_info = get_system_info()

            # 计算磁盘/网络增量
            curr_disk = psutil.disk_io_counters()
            curr_net = psutil.net_io_counters()
            if prev_disk and curr_disk:
                disk_read = max(0, curr_disk.read_bytes - prev_disk.read_bytes) / 1024
                disk_write = max(0, curr_disk.write_bytes - prev_disk.write_bytes) / 1024
            else:
                disk_read, disk_write = 0, 0
            if prev_net and curr_net:
                net_sent = max(0, curr_net.bytes_sent - prev_net.bytes_sent) / 1024
                net_recv = max(0, curr_net.bytes_recv - prev_net.bytes_recv) / 1024
            else:
                net_sent, net_recv = 0, 0

            prev_disk, prev_net = curr_disk, curr_net

            wal_size = check_wal_size(project_root)

            row = {
                "timestamp": round(timestamp - start_time, 1),
                "process_count": proc_info.get("process_count", 0),
                "cpu_percent": proc_info.get("cpu_percent", 0),
                "memory_mb": proc_info.get("memory_mb", 0),
                "handles": proc_info.get("handles", 0),
                "threads": proc_info.get("threads", 0),
                "system_cpu_percent": sys_info["system_cpu_percent"],
                "system_memory_percent": sys_info["system_memory_percent"],
                "disk_read_kbps": round(disk_read, 1),
                "disk_write_kbps": round(disk_write, 1),
                "net_sent_kbps": round(net_sent, 1),
                "net_recv_kbps": round(net_recv, 1),
                "wal_size_bytes": wal_size,
            }

            if writer:
                writer.writerow(row)
                if iteration % 10 == 0:
                    csv_file.flush()

            # 控制台简要输出
            print(
                f"[{row['timestamp']:6.0f}s] "
                f"CPU:{row['cpu_percent']:5.1f}% "
                f"MEM:{row['memory_mb']:6.1f}MB "
                f"HD:{row['handles']:4d} "
                f"WAL:{wal_size/1024:5.1f}KB"
            )

            # 检查是否超时
            if args.duration > 0 and (timestamp - start_time) >= args.duration:
                print(f"\n监控完成，共 {iteration} 次采样，{args.duration} 秒")
                break

            time.sleep(args.interval)

    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n监控被中断，共 {iteration} 次采样，{elapsed:.0f} 秒")
    finally:
        if csv_file:
            csv_file.close()
            print(f"数据已保存至: {output_file}")


if __name__ == "__main__":
    main()
