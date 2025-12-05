"""Cookie 自动刷新模块 - 使用 Playwright 自动化浏览器刷新 Cookie
每小时刷新一次Cookie并更新到本地配置文件
"""

import os
import sys
import json
import time
import re
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict

# 配置文件路径
CONFIG_FILE = Path(__file__).parent / "business_gemini_session.json"

# Cookie刷新配置
COOKIE_REFRESH_INTERVAL = 3600  # 刷新间隔：1小时（秒）
CHECK_INTERVAL = 60  # 检查间隔：1分钟（秒）

# Playwright可用性检测
PLAYWRIGHT_AVAILABLE = False
PLAYWRIGHT_BROWSER_INSTALLED = False

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass


def check_playwright_browser() -> bool:
    """检测Playwright浏览器是否已安装"""
    global PLAYWRIGHT_BROWSER_INSTALLED
    if not PLAYWRIGHT_AVAILABLE:
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        PLAYWRIGHT_BROWSER_INSTALLED = True
        return True
    except Exception as e:
        print(f"[Cookie刷新] Playwright浏览器未安装: {e}")
        print("[Cookie刷新] 请运行: playwright install chromium")
        return False


def load_config() -> Optional[dict]:
    """加载配置文件"""
    if not CONFIG_FILE.exists():
        print(f"[Cookie刷新] 配置文件不存在: {CONFIG_FILE}")
        return None
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Cookie刷新] 加载配置失败: {e}")
        return None


def save_config(config: dict):
    """保存配置到文件"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[Cookie刷新] 保存配置失败: {e}")


def get_proxy() -> Optional[str]:
    """从配置中获取代理"""
    config = load_config()
    if config:
        return config.get("proxy")
    return None


def refresh_cookie_with_browser(account: dict, proxy: Optional[str] = None) -> Optional[Dict[str, str]]:
    """
    使用 Playwright 自动化浏览器刷新 Cookie
    返回: {"secure_c_ses": "...", "host_c_oses": "...", "csesidx": "..."} 或 None
    """
    if not PLAYWRIGHT_AVAILABLE:
        print("[Cookie刷新] Playwright 未安装，无法自动刷新 Cookie")
        return None

    if not PLAYWRIGHT_BROWSER_INSTALLED:
        if not check_playwright_browser():
            return None

    try:
        with sync_playwright() as p:
            # 启动浏览器
            browser_args = ['--no-sandbox', '--disable-setuid-sandbox'] if os.name != 'nt' else []
            try:
                browser = p.chromium.launch(headless=True, args=browser_args)
            except Exception as e:
                error_msg = str(e)
                if "Executable doesn't exist" in error_msg:
                    print("[Cookie刷新] Playwright 浏览器未安装，请运行: playwright install chromium")
                else:
                    print(f"[Cookie刷新] 启动浏览器失败: {error_msg}")
                return None

            # 获取现有 Cookie
            existing_secure_c_ses = account.get("secure_c_ses")
            existing_host_c_oses = account.get("host_c_oses")

            # 创建浏览器上下文
            context_options = {
                "user_agent": account.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'),
                "viewport": {"width": 1920, "height": 1080}
            }

            # 设置现有Cookie以保持登录状态
            # 注意: __Host- 前缀的Cookie不能设置domain，必须是当前域
            # 所以我们不在context创建时设置cookie，而是在页面加载后通过context.add_cookies设置

            if proxy:
                context_options["proxy"] = {"server": proxy}

            context = browser.new_context(**context_options)
            page = context.new_page()

            try:
                # 先访问目标域名以便设置Cookie
                print(f"[Cookie刷新] 正在访问 business.gemini.google ...")
                page.goto("https://business.gemini.google/", wait_until="domcontentloaded", timeout=30000)
                
                # 在当前域设置Cookie (使用url方式)
                if existing_secure_c_ses:
                    cookies_to_add = [{
                        "name": "__Secure-C_SES",
                        "value": existing_secure_c_ses,
                        "url": "https://business.gemini.google/",
                        "secure": True,
                        "sameSite": "None"
                    }]
                    if existing_host_c_oses:
                        cookies_to_add.append({
                            "name": "__Host-C_OSES",
                            "value": existing_host_c_oses,
                            "url": "https://business.gemini.google/",
                            "secure": True,
                            "sameSite": "Strict"
                        })
                    try:
                        context.add_cookies(cookies_to_add)
                        print(f"[Cookie刷新] Cookie已设置，刷新页面...")
                    except Exception as e:
                        print(f"[Cookie刷新] 设置Cookie失败: {e}")
                
                # 刷新页面使Cookie生效
                page.reload(wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(5000)

                # 等待页面加载
                try:
                    page.wait_for_selector("body", timeout=10000)
                except:
                    pass
                page.wait_for_timeout(3000)

                # 检查是否在登录页面
                current_url = page.url
                print(f"[Cookie刷新] 当前页面URL: {current_url}")
                
                is_login_page = (
                    "accounts.google.com/v3/signin" in current_url or
                    "accounts.google.com/ServiceLogin" in current_url
                )

                if is_login_page:
                    print(f"[Cookie刷新] 检测到Google登录页面，等待自动跳转...")
                    # 等待自动登录跳转
                    try:
                        page.wait_for_timeout(5000)
                        current_url = page.url
                        print(f"[Cookie刷新] 等待后URL: {current_url}")
                        # 重新判断是否还在登录页
                        is_login_page = (
                            "accounts.google.com/v3/signin" in current_url or
                            "accounts.google.com/ServiceLogin" in current_url
                        )
                    except:
                        pass

                # 尝试触发Cookie刷新
                try:
                    page.evaluate("""
                        () => {
                            fetch('https://business.gemini.google/', { 
                                method: 'GET',
                                credentials: 'include'
                            }).catch(() => {});
                        }
                    """)
                    page.wait_for_timeout(2000)
                except:
                    pass

                # 提取csesidx
                current_url = page.url
                csesidx = None
                
                match = re.search(r'csesidx[=:](\\d+)', current_url)
                if match:
                    csesidx = match.group(1)

                if not csesidx:
                    try:
                        csesidx = page.evaluate("""
                            () => {
                                const urlParams = new URLSearchParams(window.location.search);
                                let csesidx = urlParams.get('csesidx');
                                if (!csesidx) {
                                    const match = window.location.href.match(/csesidx[=:](\\d+)/);
                                    if (match) csesidx = match[1];
                                }
                                if (!csesidx) {
                                    try {
                                        csesidx = localStorage.getItem('csesidx') || 
                                                 localStorage.getItem('CSESIDX');
                                    } catch (e) {}
                                }
                                return csesidx;
                            }
                        """)
                    except:
                        pass

                # 获取所有Cookie
                all_cookies = context.cookies()
                secure_c_ses = None
                host_c_oses = None

                for cookie in all_cookies:
                    cookie_name = cookie['name']
                    cookie_domain = cookie.get('domain', '')
                    
                    if cookie_name == '__Secure-C_SES':
                        if not secure_c_ses or cookie_domain in ['business.gemini.google', '.gemini.google']:
                            secure_c_ses = cookie['value']
                    elif cookie_name == '__Host-C_OSES':
                        if not host_c_oses or cookie_domain == 'business.gemini.google':
                            host_c_oses = cookie['value']

                # 尝试从document.cookie获取
                if not secure_c_ses:
                    try:
                        page_cookies = page.evaluate("() => document.cookie")
                        if page_cookies:
                            for cookie_str in page_cookies.split(';'):
                                cookie_str = cookie_str.strip()
                                if cookie_str.startswith('__Secure-C_SES='):
                                    secure_c_ses = cookie_str.split('=', 1)[1]
                                elif cookie_str.startswith('__Host-C_OSES='):
                                    host_c_oses = cookie_str.split('=', 1)[1]
                    except:
                        pass

                if not secure_c_ses:
                    print("[Cookie刷新] 未找到 __Secure-C_SES Cookie")
                    if is_login_page:
                        print("[Cookie刷新] Cookie已过期，需要手动登录刷新")
                    return None

                # 使用现有csesidx作为回退
                if not csesidx:
                    csesidx = account.get("csesidx")
                    if not csesidx:
                        print("[Cookie刷新] 未找到 csesidx")
                        return None

                # 检查Cookie是否更新
                cookie_changed = secure_c_ses != existing_secure_c_ses
                
                # 只有在真正的Google登录页且完全没获取到新Cookie时才判定失败
                if is_login_page and not secure_c_ses:
                    print("[Cookie刷新] 在登录页且未获取到Cookie，Cookie可能已失效")
                    return None
                
                if cookie_changed:
                    print(f"[Cookie刷新] Cookie已更新")
                else:
                    print(f"[Cookie刷新] Cookie值未变化（可能只是续期）")

                return {
                    "secure_c_ses": secure_c_ses,
                    "host_c_oses": host_c_oses or account.get("host_c_oses", ""),
                    "csesidx": csesidx
                }

            except PlaywrightTimeoutError:
                print("[Cookie刷新] 页面加载超时")
                return None
            except Exception as e:
                print(f"[Cookie刷新] 刷新失败: {e}")
                return None
            finally:
                try:
                    context.close()
                    browser.close()
                except:
                    pass

    except Exception as e:
        print(f"[Cookie刷新] 发生错误: {e}")
        return None


def refresh_account_cookie(account_idx: int, account: dict, proxy: Optional[str] = None) -> bool:
    """
    刷新指定账号的Cookie并更新配置
    返回: True成功, False失败
    """
    print(f"[Cookie刷新] 开始刷新账号 {account_idx} 的Cookie...")
    
    cookies = refresh_cookie_with_browser(account, proxy)
    
    if not cookies:
        print(f"[Cookie刷新] 账号 {account_idx}: 刷新失败")
        return False

    # 加载最新配置
    config = load_config()
    if not config:
        return False

    accounts = config.get("accounts", [])
    if account_idx >= len(accounts):
        print(f"[Cookie刷新] 账号 {account_idx} 不存在")
        return False

    # 更新Cookie
    old_ses = accounts[account_idx].get("secure_c_ses", "")
    accounts[account_idx]["secure_c_ses"] = cookies["secure_c_ses"]
    accounts[account_idx]["host_c_oses"] = cookies.get("host_c_oses", "")
    accounts[account_idx]["csesidx"] = cookies.get("csesidx", "")
    accounts[account_idx]["cookie_refresh_time"] = datetime.now().isoformat()
    
    # 清除过期标记
    accounts[account_idx].pop("cookie_expired", None)
    accounts[account_idx].pop("cookie_expired_time", None)
    
    config["accounts"] = accounts
    save_config(config)

    cookie_changed = old_ses != cookies["secure_c_ses"]
    if cookie_changed:
        print(f"[✓] 账号 {account_idx} Cookie已刷新 (csesidx: {cookies.get('csesidx', 'N/A')[:10]}...)")
    else:
        print(f"[✓] 账号 {account_idx} Cookie已验证 (值未变化)")

    return True


def cookie_refresh_worker():
    """
    后台Cookie刷新工作线程
    每小时刷新所有账号的Cookie
    """
    if not PLAYWRIGHT_AVAILABLE:
        print("[Cookie刷新] Playwright未安装，自动刷新已禁用")
        print("[Cookie刷新] 安装方法: pip install playwright && playwright install chromium")
        return

    # 等待主程序启动
    time.sleep(5)

    # 检测浏览器
    if not check_playwright_browser():
        print("[Cookie刷新] Playwright浏览器未安装，自动刷新已禁用")
        return

    print(f"[Cookie刷新] 后台刷新线程已启动，刷新间隔: {COOKIE_REFRESH_INTERVAL // 60} 分钟")

    last_refresh_time = 0  # 首次立即刷新

    while True:
        try:
            current_time = time.time()
            
            # 检查是否到达刷新时间
            if current_time - last_refresh_time >= COOKIE_REFRESH_INTERVAL:
                config = load_config()
                if not config:
                    time.sleep(CHECK_INTERVAL)
                    continue

                # 检查是否启用自动刷新
                if not config.get("auto_refresh_cookie", False):
                    time.sleep(CHECK_INTERVAL)
                    continue

                accounts = config.get("accounts", [])
                proxy = config.get("proxy")

                print(f"[Cookie刷新] 开始刷新 {len(accounts)} 个账号的Cookie...")

                success_count = 0
                for idx, acc in enumerate(accounts):
                    # 跳过禁用的账号
                    if not acc.get("available", True):
                        continue
                    
                    # 检查是否有有效的Cookie
                    if not acc.get("secure_c_ses") or not acc.get("csesidx"):
                        print(f"[Cookie刷新] 账号 {idx}: 缺少Cookie，跳过")
                        continue

                    if refresh_account_cookie(idx, acc, proxy):
                        success_count += 1
                    
                    # 账号间间隔，避免请求过快
                    time.sleep(5)

                print(f"[Cookie刷新] 刷新完成: {success_count}/{len(accounts)} 成功")
                last_refresh_time = current_time

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("[Cookie刷新] 线程已停止")
            break
        except Exception as e:
            print(f"[Cookie刷新] 线程错误: {e}")
            time.sleep(60)


def start_cookie_refresh_thread() -> Optional[threading.Thread]:
    """启动Cookie刷新后台线程"""
    config = load_config()
    if not config:
        return None

    if not config.get("auto_refresh_cookie", False):
        print("[Cookie刷新] 自动刷新未启用 (在配置中设置 auto_refresh_cookie: true 启用)")
        return None

    thread = threading.Thread(target=cookie_refresh_worker, daemon=True)
    thread.start()
    return thread


def manual_refresh_all():
    """手动刷新所有账号的Cookie"""
    if not PLAYWRIGHT_AVAILABLE:
        print("[Cookie刷新] Playwright未安装")
        return

    if not check_playwright_browser():
        return

    config = load_config()
    if not config:
        return

    accounts = config.get("accounts", [])
    proxy = config.get("proxy")

    print(f"[Cookie刷新] 开始手动刷新 {len(accounts)} 个账号...")

    for idx, acc in enumerate(accounts):
        if not acc.get("available", True):
            print(f"[Cookie刷新] 账号 {idx}: 已禁用，跳过")
            continue
        
        if not acc.get("secure_c_ses") or not acc.get("csesidx"):
            print(f"[Cookie刷新] 账号 {idx}: 缺少Cookie，跳过")
            continue

        refresh_account_cookie(idx, acc, proxy)
        time.sleep(3)

    print("[Cookie刷新] 手动刷新完成")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Cookie自动刷新工具")
    parser.add_argument("--once", action="store_true", help="只执行一次刷新")
    parser.add_argument("--daemon", action="store_true", help="后台运行")
    parser.add_argument("--account", type=int, help="只刷新指定账号")
    args = parser.parse_args()

    if args.once:
        if args.account is not None:
            config = load_config()
            if config:
                accounts = config.get("accounts", [])
                if 0 <= args.account < len(accounts):
                    refresh_account_cookie(args.account, accounts[args.account], config.get("proxy"))
                else:
                    print(f"账号 {args.account} 不存在")
        else:
            manual_refresh_all()
    elif args.daemon:
        print("="*50)
        print("Cookie自动刷新服务")
        print("="*50)
        cookie_refresh_worker()
    else:
        print("使用方法:")
        print("  python cookie_refresh.py --once          # 立即刷新一次所有账号")
        print("  python cookie_refresh.py --once --account 0  # 只刷新账号0")
        print("  python cookie_refresh.py --daemon        # 后台持续运行")
        print("\n在gemini.py中自动启动: 在配置中设置 auto_refresh_cookie: true")
