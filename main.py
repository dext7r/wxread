#!/usr/bin/env python3
"""
微信读书自动阅读工具 - 主程序入口

新版本使用模块化架构，提供更好的错误处理、配置管理和扩展性。
兼容旧版本配置，支持平滑迁移。

使用方法：
    python main.py                    # 使用默认配置
    python main.py --config config.json  # 使用指定配置文件
    python main.py --test-push       # 测试推送功能
"""

import sys
import argparse
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.config.manager import ConfigManager
    from src.core.bot import WxReadBot
    from src.utils.logger import setup_logging, get_logger
    from src.utils.exceptions import WxReadError, ConfigError
    NEW_VERSION_AVAILABLE = True
except ImportError:
    NEW_VERSION_AVAILABLE = False


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="微信读书自动阅读工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                          # 使用默认配置运行
  %(prog)s --config config.json     # 使用指定配置文件
  %(prog)s --test-push              # 测试推送功能
  %(prog)s --log-level DEBUG        # 设置日志级别
        """
    )

    parser.add_argument(
        '--config', '-c',
        type=str,
        help='配置文件路径'
    )

    parser.add_argument(
        '--test-push',
        action='store_true',
        help='测试推送功能'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='日志级别 (默认: INFO)'
    )

    parser.add_argument(
        '--log-dir',
        type=str,
        default='logs',
        help='日志目录 (默认: logs)'
    )

    parser.add_argument(
        '--version', '-v',
        action='version',
        version='微信读书自动阅读工具 v2.0.0'
    )

    parser.add_argument(
        '--legacy',
        action='store_true',
        help='强制使用旧版本逻辑'
    )

    return parser.parse_args()


def main_new_version():
    """新版本主函数"""
    args = parse_arguments()

    # 设置日志
    setup_logging(
        level=args.log_level,
        log_dir=args.log_dir,
        enable_console=True,
        enable_file=True
    )

    logger = get_logger(__name__)
    logger.info("=" * 50)
    logger.info("微信读书自动阅读工具 v2.0.0 启动")
    logger.info("=" * 50)

    try:
        # 加载配置
        config_manager = ConfigManager(args.config)
        logger.info("配置加载成功")

        # 测试推送功能
        if args.test_push:
            from src.notifications.manager import NotificationManager

            notification = NotificationManager.create_from_config(
                config_manager.get_all()
            )

            if notification.is_enabled():
                logger.info("开始测试推送功能...")
                success = notification.test_push()
                if success:
                    logger.info("✅ 推送测试成功")
                    return 0
                else:
                    logger.error("❌ 推送测试失败")
                    return 1
            else:
                logger.info("推送功能未启用，无法测试")
                return 0

        # 创建并启动机器人
        bot = WxReadBot(config_manager)

        try:
            result = bot.start_reading()

            # 输出结果
            logger.info("=" * 50)
            logger.info("阅读任务完成")
            logger.info(f"成功次数: {result['success_count']}/{result['total_attempts']}")
            logger.info(f"阅读时长: {result['reading_minutes']} 分钟")
            logger.info(f"成功率: {result['success_rate']:.1f}%")
            logger.info("=" * 50)

            return 0

        finally:
            bot.close()

    except ConfigError as e:
        logger.error(f"配置错误: {e}")
        return 1
    except WxReadError as e:
        logger.error(f"运行错误: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("用户中断程序")
        return 0
    except Exception as e:
        logger.error(f"未知错误: {e}", exc_info=True)
        return 1


def main_legacy():
    """旧版本主函数（兼容模式）"""
    print("⚠️  使用兼容模式运行...")

    # 导入旧版本模块
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    # 执行旧版本逻辑
    import subprocess
    result = subprocess.run([sys.executable, "main_old.py"],
                          capture_output=False, text=True)
    return result.returncode


def main():
    """主函数"""
    args = parse_arguments()

    # 检查是否强制使用旧版本
    if args.legacy:
        return main_legacy()

    # 检查新版本是否可用
    if NEW_VERSION_AVAILABLE:
        return main_new_version()
    else:
        print("⚠️  新版本模块未找到，使用兼容模式...")
        return main_legacy()


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ 程序运行失败: {e}")
        sys.exit(1)
