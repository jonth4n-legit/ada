"""
保活脚本 - 从 .env 文件读取账号并更新配置
"""
import os
import sys
import re
import time
import logging
from typing import List, Dict, Optional
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 配置日志（先配置，以便在导入错误时可以使用）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("keep-alive-env")

# 设置环境变量，使保活默认使用无头浏览器
os.environ["HEADLESS_MODE"] = "true"

# 导入 update_configs.py 中的功能
try:
    import update_configs
    from update_configs import (
        GPTMailClient,
        extract_config_from_browser,
        login_and_update_config,
        THREAD_COUNT
    )
except ImportError as e:
    logger.error(f"❌ 无法导入 update_configs 模块: {e}")
    logger.error(f"   当前工作目录: {os.getcwd()}")
    logger.error(f"   Python 路径: {sys.path}")
    logger.error(f"   文件路径: {BASE_DIR}")
    logger.error(f"   update_configs.py 是否存在: {os.path.exists(os.path.join(BASE_DIR, 'update_configs.py'))}")
    raise

# 禁用 Selenium 和浏览器驱动的冗余日志
logging.getLogger("selenium").setLevel(logging.ERROR)
logging.getLogger("selenium.webdriver").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)


def extract_email_from_name(name: str) -> Optional[str]:
    """从账号名称中提取邮箱地址"""
    if not name:
        return None
    
    # 邮箱正则表达式
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, name)
    if match:
        return match.group(0).lower()
    return None


def parse_accounts_from_env(env_path: str = ".env") -> List[Dict[str, str]]:
    """
    从 .env 文件解析账号配置
    
    Returns:
        账号列表，每个账号包含：index, name, email, secure_c_ses, csesidx, config_id, host_c_oses
    """
    accounts = []
    
    if not os.path.exists(env_path):
        logger.error(f"❌ .env 文件不存在: {env_path}")
        return accounts
    
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        account_vars = {}  # {index: {vars}}
        
        # 解析所有账号相关的环境变量
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            
            # 检查是否是账号配置
            if key.startswith("ACCOUNT") and key.endswith("_SECURE_C_SES"):
                idx_str = key[len("ACCOUNT") : -len("_SECURE_C_SES")]
                try:
                    idx = int(idx_str)
                    if idx not in account_vars:
                        account_vars[idx] = {}
                    account_vars[idx]["SECURE_C_SES"] = value
                    account_vars[idx]["index"] = idx
                except ValueError:
                    continue
            elif key.startswith("ACCOUNT") and "_" in key:
                parts = key.split("_", 1)
                if len(parts) == 2 and parts[0].startswith("ACCOUNT"):
                    idx_str = parts[0][len("ACCOUNT"):]
                    try:
                        idx = int(idx_str)
                        var_name = parts[1]
                        if idx not in account_vars:
                            account_vars[idx] = {}
                        account_vars[idx][var_name] = value
                        account_vars[idx]["index"] = idx
                    except ValueError:
                        continue
        
        # 处理多账号配置
        for idx in sorted(account_vars.keys()):
            vars_dict = account_vars[idx]
            if vars_dict.get("SECURE_C_SES") and vars_dict.get("CSESIDX") and vars_dict.get("CONFIG_ID"):
                name = vars_dict.get("NAME") or f"account-{idx}"
                email = extract_email_from_name(name)
                if not email:
                    # 如果名称中没有邮箱，尝试使用 name 作为邮箱
                    email = name if "@" in name else None
                
                if email:
                    accounts.append({
                        "index": idx,
                        "name": name,
                        "email": email,
                        "secure_c_ses": vars_dict.get("SECURE_C_SES"),
                        "csesidx": vars_dict.get("CSESIDX"),
                        "config_id": vars_dict.get("CONFIG_ID"),
                        "host_c_oses": vars_dict.get("HOST_C_OSES", ""),
                    })
                else:
                    logger.warning(f"⚠️ 账号 {idx} ({name}) 无法提取邮箱，跳过")
        
        logger.info(f"📋 从 .env 文件读取到 {len(accounts)} 个账号")
        return accounts
        
    except Exception as e:
        logger.error(f"❌ 读取 .env 文件失败: {e}")
        return []


def update_env_file(accounts: List[Dict[str, str]], env_path: str = ".env"):
    """
    更新 .env 文件中的账号配置
    
    Args:
        accounts: 更新后的账号列表，每个账号包含 index, name, secure_c_ses, csesidx, config_id, host_c_oses
    """
    if not os.path.exists(env_path):
        logger.error(f"❌ .env 文件不存在: {env_path}")
        return
    
    try:
        # 读取原文件
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 创建账号索引映射
        account_map = {acc["index"]: acc for acc in accounts}
        
        # 更新文件内容
        new_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            original_line = line
            
            # 检查是否是账号相关的行
            if "ACCOUNT" in line and "_" in line and "=" in line:
                # 尝试匹配 ACCOUNT{数字}_ 格式
                match = re.match(r'ACCOUNT(\d+)_', line)
                if match:
                    idx = int(match.group(1))
                    if idx in account_map:
                        acc = account_map[idx]
                        key = line.split("=", 1)[0].strip()
                        
                        # 根据键名更新对应的值
                        if key.endswith("_NAME"):
                            new_line = f'ACCOUNT{idx}_NAME="{acc["name"]}"\n'
                        elif key.endswith("_SECURE_C_SES"):
                            new_line = f'ACCOUNT{idx}_SECURE_C_SES="{acc["secure_c_ses"]}"\n'
                        elif key.endswith("_CSESIDX"):
                            new_line = f'ACCOUNT{idx}_CSESIDX="{acc["csesidx"]}"\n'
                        elif key.endswith("_CONFIG_ID"):
                            new_line = f'ACCOUNT{idx}_CONFIG_ID="{acc["config_id"]}"\n'
                        elif key.endswith("_HOST_C_OSES"):
                            if acc.get("host_c_oses"):
                                new_line = f'ACCOUNT{idx}_HOST_C_OSES="{acc["host_c_oses"]}"\n'
                            else:
                                new_line = original_line  # 保持原样
                        else:
                            new_line = original_line
                        
                        new_lines.append(new_line)
                        i += 1
                        continue
            
            # 其他行保持不变
            new_lines.append(original_line)
            i += 1
        
        # 写回文件
        with open(env_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        logger.info(f"✅ .env 文件已更新")
        
    except Exception as e:
        logger.error(f"❌ 更新 .env 文件失败: {e}")
        raise


def update_single_account_from_env(account: Dict[str, str], account_index: int, total_accounts: int) -> Optional[Dict[str, str]]:
    """
    更新单个账号的配置（从 .env 格式）
    
    Args:
        account: 账号信息字典（包含 email, name 等）
        account_index: 账号索引
        total_accounts: 总账号数
        
    Returns:
        更新后的配置信息
    """
    email = account.get("email")
    account_name = account.get("name", email or "未知账号")
    if not email:
        logger.error(f"❌ [{account_index}/{total_accounts}] 账号信息中缺少邮箱: {account_name}")
        return None
    
    # 输出开始保活日志（格式：便于解析）
    start_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    logger.info(f"[{account_index}/{total_accounts}] 开始更新账号: {account_name} ({email}) - {start_time_str}")
    
    # 构建 update_configs.py 期望的格式
    account_for_update = {
        "Name": email  # update_configs.py 使用 Name 字段作为邮箱
    }
    
    start_time = time.time()
    
    # 调用 update_configs.py 中的登录和更新函数
    new_config = login_and_update_config(account_for_update, account_index, total_accounts)
    
    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)
    end_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    
    if new_config:
        logger.info(f"✅ [{account_index}/{total_accounts}] 更新成功账号: {account_name} ({email}) - {end_time_str} (耗时: {minutes}分{seconds}秒)")
        
        # 转换为 .env 格式
        return {
            "index": account["index"],
            "name": account["name"],  # 保持原名称
            "email": email,
            "secure_c_ses": new_config.get("SECURE_C_SES", account["secure_c_ses"]),
            "csesidx": new_config.get("CSESIDX", account["csesidx"]),
            "config_id": new_config.get("CONFIG_ID", account["config_id"]),
            "host_c_oses": new_config.get("HOST_C_OSES", account.get("host_c_oses", "")),
        }
    else:
        logger.error(f"❌ [{account_index}/{total_accounts}] 更新失败账号: {account_name} ({email}) - {end_time_str} (耗时: {minutes}分{seconds}秒)")
        # 如果更新失败，返回原配置
        return account


def main():
    """主函数"""
    logger.info("🚀 开始保活任务 - 更新 .env 文件中的账号配置...")
    
    env_path = os.path.join(BASE_DIR, ".env")
    
    # 读取 .env 文件中的账号
    accounts = parse_accounts_from_env(env_path)
    
    if not accounts:
        logger.error("❌ 未找到任何账号信息")
        return
    
    logger.info(f"📋 找到 {len(accounts)} 个账号，开始更新...")
    
    # 记录总开始时间
    total_start_time = time.time()
    
    # 使用线程池执行更新
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    updated_accounts = []
    success_count = 0
    fail_count = 0
    
    with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
        futures = {
            executor.submit(update_single_account_from_env, account, i + 1, len(accounts)): i
            for i, account in enumerate(accounts)
        }
        
        # 等待所有任务完成
        results = [None] * len(accounts)
        for future in as_completed(futures):
            account_index = futures[future]
            try:
                result = future.result()
                results[account_index] = result
                if result and result.get('config_id'):
                    success_count += 1
                    logger.info(f"✅ 账号 {account_index + 1} ({result.get('name', 'unknown')}) 更新成功")
                else:
                    fail_count += 1
                    logger.error(f"❌ 账号 {account_index + 1} 更新失败")
            except Exception as e:
                fail_count += 1
                logger.error(f"❌ 账号 {account_index + 1} 更新异常: {e}")
                # 保留原配置
                results[account_index] = accounts[account_index]
    
    # 过滤掉 None 值
    updated_accounts = [acc for acc in results if acc]
    
    # 更新 .env 文件
    if updated_accounts:
        update_env_file(updated_accounts, env_path)
    
    # 计算总耗时
    total_elapsed_time = time.time() - total_start_time
    total_minutes = int(total_elapsed_time // 60)
    total_seconds = int(total_elapsed_time % 60)
    
    # 输出统计信息
    logger.info("=" * 60)
    logger.info("📊 更新统计:")
    logger.info(f"   总账号数: {len(accounts)}")
    logger.info(f"   成功: {success_count}")
    logger.info(f"   失败: {fail_count}")
    if len(accounts) > 0:
        logger.info(f"   成功率: {success_count / len(accounts) * 100:.1f}%")
    logger.info(f"   总耗时: {total_minutes}分{total_seconds}秒 ({int(total_elapsed_time)}秒)")
    logger.info("=" * 60)
    logger.info(f"✅ 保活任务完成，.env 文件已更新")


if __name__ == "__main__":
    main()

