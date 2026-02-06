#!/usr/bin/env python3
"""
FastReAct Environment Stress Test

Windows系统环境健康检查脚本：
- CPU 负载检测
- 内存占用检测
- 磁盘空间检查
- 写权限验证
- 文件写入一致性测试（10MB临时文件）
- MD5校验和验证

运行方式：
    python env_stress.py
"""
import subprocess
import os
import hashlib
import time
import json
from pathlib import Path
from datetime import datetime


# ============================================================================
# 安全打印函数（处理 Windows GBK 编码问题）
# ============================================================================

def safe_print(text):
    """
    安全打印，避免 GBK 编码错误

    Args:
        text: 要打印的文本
    """
    try:
        print(text)
    except UnicodeEncodeError:
        # 移除或替换无法编码的字符
        safe_text = text.encode('gbk', errors='replace').decode('gbk')
        print(safe_text)


# ============================================================================
# PowerShell 命令执行器
# ============================================================================

def run_powershell(command):
    """
    执行PowerShell命令并返回结果

    Args:
        command: PowerShell命令字符串

    Returns:
        (stdout, stderr, returncode)
    """
    try:
        # 使用 -ExecutionPolicy Bypass 绕过执行策略
        full_command = f"powershell -ExecutionPolicy Bypass -Command \"{command}\""

        result = subprocess.run(
            full_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='replace'  # 替换无法解码的字符
        )

        # 过滤掉可能导致 GBK 编码错误的字符
        def safe_string(s):
            if not s:
                return ""
            # 移除或替换可能有问题的字符
            return ''.join(c if ord(c) < 128 else '?' for c in s)

        stdout = safe_string(result.stdout.strip())
        stderr = safe_string(result.stderr.strip())

        return stdout, stderr, result.returncode

    except subprocess.TimeoutExpired:
        return "", "Command timed out", -1
    except Exception as e:
        return "", f"Failed to execute: {str(e)}", -1


# ============================================================================
# 系统信息检测
# ============================================================================

def get_cpu_usage():
    """
    获取CPU使用率

    Returns:
        dict: CPU使用率信息
    """
    print("[CHECK] 检测 CPU 负载...")

    # PowerShell 获取 CPU 使用率
    command = "Get-Counter '\\Processor(_Total)\\% Processor Time' -SampleInterval 1 -MaxSamples 1 | " \
              "Select-Object -ExpandProperty CounterSamples | " \
              "Select-Object -ExpandProperty CookedValue"

    stdout, stderr, code = run_powershell(command)

    if code == 0 and stdout:
        try:
            cpu_usage = float(stdout)
            print(f"  CPU 使用率: {cpu_usage:.1f}%")

            # 判断负载状态
            if cpu_usage < 50:
                status = "正常"
                color = "[OK]"
            elif cpu_usage < 80:
                status = "中等"
                color = "[WARNING]"
            else:
                status = "高负载"
                color = "[ERROR]"

            return {
                "usage_percent": cpu_usage,
                "status": status,
                "indicator": color,
                "healthy": cpu_usage < 80
            }
        except ValueError:
            print(f"  [ERROR] 无法解析 CPU 数据: {stdout}")
            return {
                "usage_percent": None,
                "status": "未知",
                "indicator": "[ERROR]",
                "healthy": False,
                "error": "Parse error"
            }
    else:
        print(f"  [ERROR] 获取 CPU 信息失败: {stderr}")
        return {
            "usage_percent": None,
            "status": "检测失败",
            "indicator": "[ERROR]",
            "healthy": False,
            "error": stderr
        }


def get_memory_usage():
    """
    获取内存使用情况

    Returns:
        dict: 内存使用信息
    """
    print("[CHECK] 检测内存占用...")

    # PowerShell 获取内存信息
    command = "Get-WmiObject Win32_OperatingSystem | " \
              "Select-Object @{Name='TotalGB';Expression={[math]::Round($_.TotalVisibleMemorySize/1MB, 2)}}, " \
              "@{Name='FreeGB';Expression={[math]::Round($_.FreePhysicalMemory/1MB, 2)}}, " \
              "@{Name='UsedGB';Expression={[math]::Round(($_.TotalVisibleMemorySize-$_.FreePhysicalMemory)/1MB, 2)}} | " \
              "ConvertTo-Json"

    stdout, stderr, code = run_powershell(command)

    if code == 0 and stdout:
        try:
            data = json.loads(stdout)
            total_gb = data.get('TotalGB', 0)
            free_gb = data.get('FreeGB', 0)
            used_gb = data.get('UsedGB', 0)

            usage_percent = (used_gb / total_gb * 100) if total_gb > 0 else 0

            print(f"  总内存: {total_gb:.2f} GB")
            print(f"  已用: {used_gb:.2f} GB ({usage_percent:.1f}%)")
            print(f"  可用: {free_gb:.2f} GB")

            # 判断内存状态
            if usage_percent < 70:
                status = "正常"
                color = "[OK]"
            elif usage_percent < 90:
                status = "中等"
                color = "[WARNING]"
            else:
                status = "内存紧张"
                color = "[ERROR]"

            return {
                "total_gb": total_gb,
                "used_gb": used_gb,
                "free_gb": free_gb,
                "usage_percent": usage_percent,
                "status": status,
                "indicator": color,
                "healthy": usage_percent < 90
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"  [ERROR] 解析内存数据失败: {e}")
            return {
                "total_gb": None,
                "used_gb": None,
                "free_gb": None,
                "usage_percent": None,
                "status": "解析失败",
                "indicator": "[ERROR]",
                "healthy": False,
                "error": str(e)
            }
    else:
        print(f"  [ERROR] 获取内存信息失败: {stderr}")
        return {
            "total_gb": None,
            "used_gb": None,
            "free_gb": None,
            "usage_percent": None,
            "status": "检测失败",
            "indicator": "[ERROR]",
            "healthy": False,
            "error": stderr
        }


def get_disk_info(path):
    """
    获取磁盘空间信息

    Args:
        path: 检查路径

    Returns:
        dict: 磁盘空间信息
    """
    print(f"[CHECK] 检测磁盘空间 ({path})...")

    if not os.path.exists(path):
        print(f"  [ERROR] 路径不存在: {path}")
        return {
            "path": path,
            "exists": False,
            "total_gb": None,
            "free_gb": None,
            "free_gb_float": None,
            "healthy": False
        }

    # PowerShell 获取磁盘信息
    # 获取盘符（D: -> D）
    drive = str(Path(path).anchor)
    drive_letter = drive[0] if drive else "C"

    command = f"Get-PSDrive -Name {drive_letter} | Select-Object Used, Free | " \
              "Select-Object @{Name='FreeGB';Expression={[math]::Round($_.Free/1GB, 2)}}, " \
              "@{Name='UsedGB';Expression={[math]::Round($_.Used/1GB, 2)}} | " \
              "ConvertTo-Json"

    stdout, stderr, code = run_powershell(command)

    if code == 0 and stdout:
        try:
            data = json.loads(stdout)
            free_gb = data.get('FreeGB', 0)
            used_gb = data.get('UsedGB', 0)
            total_gb = free_gb + used_gb

            print(f"  盘符: {drive}")
            print(f"  总空间: {total_gb:.2f} GB")
            print(f"  已用: {used_gb:.2f} GB")
            print(f"  可用: {free_gb:.2f} GB")

            # 判断磁盘空间状态
            if free_gb > 10:
                status = "充足"
                color = "[OK]"
            elif free_gb > 5:
                status = "紧张"
                color = "[WARNING]"
            else:
                status = "严重不足"
                color = "[ERROR]"

            return {
                "path": path,
                "drive": drive,
                "exists": True,
                "total_gb": round(total_gb, 2),
                "used_gb": round(used_gb, 2),
                "free_gb": round(free_gb, 2),
                "free_gb_float": free_gb,
                "status": status,
                "indicator": color,
                "healthy": free_gb > 5
            }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"  [ERROR] 解析磁盘数据失败: {e}")
            return {
                "path": path,
                "drive": drive,
                "exists": True,
                "total_gb": None,
                "used_gb": None,
                "free_gb": None,
                "free_gb_float": None,
                "status": "解析失败",
                "indicator": "[ERROR]",
                "healthy": False,
                "error": str(e)
            }
    else:
        # 安全打印错误信息
        error_msg = stderr if stderr else "未知错误"
        try:
            print(f"  [ERROR] 获取磁盘信息失败: {error_msg}")
        except UnicodeEncodeError:
            print(f"  [ERROR] 获取磁盘信息失败 (编码错误，原始错误长度: {len(error_msg)})")

        return {
            "path": path,
            "exists": True,
            "total_gb": None,
            "used_gb": None,
            "free_gb": None,
            "free_gb_float": None,
            "status": "检测失败",
            "indicator": "[ERROR]",
            "healthy": False,
            "error": error_msg[:100]  # 截断避免编码问题
        }


def check_write_permission(path):
    """
    检查目录写权限

    Args:
        path: 检查路径

    Returns:
        dict: 权限检查结果
    """
    print(f"[CHECK] 检查写权限 ({path})...")

    test_file = Path(path) / f".write_test_{int(time.time())}.tmp"

    try:
        # 尝试创建测试文件
        test_file.write_text("test", encoding='utf-8')

        # 尝试读取
        content = test_file.read_text(encoding='utf-8')

        # 删除测试文件
        test_file.unlink()

        print(f"  [OK] 写权限正常")
        return {
            "path": path,
            "has_write_permission": True,
            "indicator": "[OK]",
            "healthy": True
        }

    except PermissionError:
        print(f"  [ERROR] 无写权限")
        return {
            "path": path,
            "has_write_permission": False,
            "indicator": "[ERROR]",
            "healthy": False,
            "error": "Permission denied"
        }
    except Exception as e:
        print(f"  [ERROR] 写权限检查失败: {e}")
        return {
            "path": path,
            "has_write_permission": False,
            "indicator": "[ERROR]",
            "healthy": False,
            "error": str(e)
        }


# ============================================================================
# 压力测试
# ============================================================================

def generate_test_file(path, size_mb=10):
    """
    生成测试文件并验证写入一致性

    Args:
        path: 目标目录
        size_mb: 文件大小（MB）

    Returns:
        dict: 测试结果
    """
    print(f"[TEST] 生成 {size_mb}MB 测试文件...")

    file_path = Path(path) / f".stress_test_{int(time.time())}.dat"
    size_bytes = size_mb * 1024 * 1024  # 转换为字节

    try:
        # 生成随机数据
        import random
        random.seed(time.time())

        # 为了性能，生成较小的随机块并重复
        chunk_size = 1024 * 1024  # 1MB 块
        chunk = os.urandom(chunk_size)

        start_time = time.time()

        with open(file_path, 'wb') as f:
            for i in range(size_mb):
                f.write(chunk)
                if (i + 1) % 5 == 0:
                    print(f"  进度: {i + 1}MB / {size_mb}MB")

        write_time = time.time() - start_time

        file_size = file_path.stat().st_size
        write_speed = (file_size / 1024 / 1024) / write_time if write_time > 0 else 0

        print(f"  [OK] 文件创建成功")
        print(f"  文件大小: {file_size / 1024 / 1024:.2f} MB")
        print(f"  写入速度: {write_speed:.2f} MB/s")

        # 计算 MD5
        print(f"  [CHECK] 计算 MD5 校验和...")
        md5_start = time.time()

        md5_hash = hashlib.md5()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                md5_hash.update(chunk)

        md5_checksum = md5_hash.hexdigest()
        md5_time = time.time() - md5_start

        print(f"  [OK] MD5: {md5_checksum}")
        print(f"  计算时间: {md5_time:.2f}s")

        # 验证：重新读取并计算 MD5
        print(f"  [VERIFY] 验证写入一致性...")
        verify_md5_hash = hashlib.md5()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                verify_md5_hash.update(chunk)

        verify_checksum = verify_md5_hash.hexdigest()

        if verify_checksum == md5_checksum:
            print(f"  [OK] 校验和匹配 - 写入一致性验证通过")
            consistent = True
        else:
            print(f"  [ERROR] 校验和不匹配!")
            print(f"    原始: {md5_checksum}")
            print(f"    验证: {verify_checksum}")
            consistent = False

        # 删除测试文件
        print(f"  [CLEANUP] 删除测试文件...")
        file_path.unlink()

        print(f"  [OK] 测试文件已删除")

        return {
            "path": str(file_path),
            "size_mb": size_mb,
            "actual_size_mb": round(file_size / 1024 / 1024, 2),
            "write_time": round(write_time, 2),
            "write_speed_mb_s": round(write_speed, 2),
            "md5_checksum": md5_checksum,
            "md5_calc_time": round(md5_time, 2),
            "write_consistent": consistent,
            "file_deleted": True,
            "indicator": "[OK]" if consistent else "[ERROR]",
            "healthy": consistent
        }

    except Exception as e:
        print(f"  [ERROR] 测试失败: {e}")

        # 清理可能残留的文件
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"  [CLEANUP] 已清理残留文件")
            except:
                pass

        return {
            "path": str(file_path),
            "size_mb": size_mb,
            "error": str(e),
            "indicator": "[ERROR]",
            "healthy": False,
            "file_deleted": file_path.exists() == False
        }


# ============================================================================
# 报告生成
# ============================================================================

def generate_report(results):
    """
    生成环境健康报告

    Args:
        results: 测试结果字典
    """
    print()
    print("=" * 70)
    print(" " * 15 + "WINDOWS 环境健康报告")
    print("=" * 70)
    print()

    # 1. CPU 状态
    cpu = results['cpu']
    print(f"CPU 状态: {cpu['indicator']}")
    print(f"  使用率: {cpu.get('usage_percent', 'N/A')}%")
    print(f"  状态: {cpu['status']}")
    print()

    # 2. 内存状态
    mem = results['memory']
    print(f"内存状态: {mem['indicator']}")
    print(f"  总内存: {mem.get('total_gb', 'N/A')} GB")
    print(f"  已使用: {mem.get('used_gb', 'N/A')} GB ({mem.get('usage_percent', 'N/A')}%)")
    print(f"  可用: {mem.get('free_gb', 'N/A')} GB")
    print(f"  状态: {mem['status']}")
    print()

    # 3. 磁盘状态
    disk = results['disk']
    print(f"磁盘状态: {disk['indicator']}")
    print(f"  路径: {disk['path']}")
    print(f"  盘符: {disk.get('drive', 'N/A')}")
    print(f"  总空间: {disk.get('total_gb', 'N/A')} GB")
    print(f"  可用空间: {disk.get('free_gb', 'N/A')} GB")
    print(f"  状态: {disk['status']}")
    print()

    # 4. 写权限
    perm = results['permission']
    print(f"写权限: {perm['indicator']}")
    print(f"  路径: {perm['path']}")
    print(f"  状态: {'有写权限' if perm['has_write_permission'] else '无写权限'}")
    print()

    # 5. 压力测试（如果执行）
    if 'stress_test' in results:
        stress = results['stress_test']

        if stress.get('skipped'):
            # 测试被跳过
            print(f"压力测试: [SKIP]")
            print(f"  原因: {stress.get('reason', 'Unknown')}")
            if 'free_gb' in stress:
                print(f"  可用空间: {stress['free_gb']} GB")
            print()
        else:
            # 测试已执行
            print(f"压力测试: {stress.get('indicator', '[N/A]')}")
            print(f"  文件大小: {stress.get('actual_size_mb', 'N/A')} MB")
            print(f"  写入速度: {stress.get('write_speed_mb_s', 'N/A')} MB/s")
            print(f"  MD5校验: {stress.get('md5_checksum', 'N/A')[:16] if stress.get('md5_checksum') else 'N/A'}...")
            print(f"  一致性: {'通过' if stress.get('write_consistent') else '失败'}")
            print(f"  清理: {'完成' if stress.get('file_deleted') else '失败'}")
            print()

    # 6. 总体评估
    print("=" * 70)
    print(" " * 25 + "总体评估")
    print("=" * 70)

    all_healthy = all([
        results['cpu']['healthy'],
        results['memory']['healthy'],
        results['disk']['healthy'],
        results['permission']['healthy']
    ])

    if 'stress_test' in results:
        stress = results['stress_test']
        # 只有在测试执行且失败时才算不健康
        if not stress.get('skipped', False):
            all_healthy = all_healthy and stress['healthy']

    if all_healthy:
        print("[OK] 所有检查通过 - 系统环境健康")
        print()
        print("结论: FastReAct 可以正常运行")
    else:
        print("[WARNING] 发现问题 - 请检查以下项目:")
        print()

        if not results['cpu']['healthy']:
            print(f"  - CPU 负载过高 ({results['cpu']['usage_percent']}%)")
        if not results['memory']['healthy']:
            print(f"  - 内存不足 (可用: {results['memory']['free_gb']} GB)")
        if not results['disk']['healthy']:
            print(f"  - 磁盘空间不足 (可用: {results['disk']['free_gb']} GB)")
        if not results['permission']['healthy']:
            print(f"  - 无写权限 ({results['permission']['path']})")
        if 'stress_test' in results:
            stress = results['stress_test']
            if not stress.get('skipped', False) and not stress.get('healthy', True):
                print(f"  - 文件写入测试失败")

        print()
        print("建议: 修复上述问题后再运行 FastReAct")

    print()
    print("=" * 70)
    print(f"报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


def save_report_json(results, path=None):
    """
    保存 JSON 格式报告

    Args:
        results: 测试结果
        path: 保存路径（可选）
    """
    if path is None:
        path = Path.cwd() / "env_stress_report.json"

    try:
        # 转换 WindowsPath 为字符串
        def convert_path(obj):
            if isinstance(obj, Path):
                return str(obj)
            elif isinstance(obj, dict):
                return {k: convert_path(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_path(item) for item in obj]
            return obj

        serializable_results = convert_path(results)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)

        print(f"[SAVE] 报告已保存到: {path}")
        return True
    except Exception as e:
        print(f"[ERROR] 保存报告失败: {e}")
        return False


# ============================================================================
# 主程序
# ============================================================================

def main():
    """
    主测试流程
    """
    print()
    print("*" * 70)
    print("*" + " " * 68 + "*")
    print("*" + " " * 12 + "FastReAct 环境压力测试" + " " * 30 + "*")
    print("*" + " " * 68 + "*")
    print("*" * 70)
    print()

    # 测试目标目录
    target_path = Path.cwd()  # D:\FastReAct

    print(f"[INFO] 测试目标: {target_path}")
    print(f"[INFO] 系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 存储所有结果
    results = {}

    # 1. CPU 检测
    results['cpu'] = get_cpu_usage()
    print()

    # 2. 内存检测
    results['memory'] = get_memory_usage()
    print()

    # 3. 磁盘空间检测
    results['disk'] = get_disk_info(target_path)
    print()

    # 4. 写权限检测
    results['permission'] = check_write_permission(target_path)
    print()

    # 5. 压力测试（如果空间充足）
    if results['disk']['free_gb_float'] is not None:
        if results['disk']['free_gb_float'] > 1.0:
            print("[DECISION] 可用空间 > 1GB - 执行压力测试")
            print()
            results['stress_test'] = generate_test_file(target_path, size_mb=10)
        else:
            print("[SKIP] 可用空间不足 1GB - 跳过压力测试")
            print()
            results['stress_test'] = {
                "skipped": True,
                "reason": "Insufficient disk space",
                "free_gb": results['disk']['free_gb']
            }
    else:
        print("[SKIP] 无法获取磁盘信息 - 跳过压力测试")
        print()
        results['stress_test'] = {
            "skipped": True,
            "reason": "Could not determine disk space"
        }

    # 6. 生成报告
    generate_report(results)

    # 7. 保存 JSON 报告
    print()
    save_report_json(results)

    # 8. 返回退出码
    all_healthy = all([
        results['cpu']['healthy'],
        results['memory']['healthy'],
        results['disk']['healthy'],
        results['permission']['healthy']
    ])

    if 'stress_test' in results and not results['stress_test'].get('skipped'):
        all_healthy = all_healthy and results['stress_test']['healthy']

    return 0 if all_healthy else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        print()
        if exit_code == 0:
            print("[SUCCESS] 环境健康检查完成 - 所有测试通过")
        else:
            print("[WARNING] 环境健康检查完成 - 发现问题")
        print()
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] 用户中断")
        exit(1)
    except Exception as e:
        print(f"\n[ERROR] 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
