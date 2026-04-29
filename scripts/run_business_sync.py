import argparse
import os
import sys
from pathlib import Path


project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from structalert.__main__ import setup_logging
from structalert.tasks import run_business_data_sync


def main():
    parser = argparse.ArgumentParser(description="业务数据增量同步脚本")
    parser.add_argument("--config", "-c", required=True, help="配置文件路径")
    args = parser.parse_args()

    config_path = os.path.abspath(args.config)
    os.environ["CONFIG_PATH"] = config_path
    setup_logging(config_path)
    run_business_data_sync()


if __name__ == "__main__":
    main()
