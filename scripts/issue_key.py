#!/usr/bin/env python3
"""API Key 运维 CLI：签发 / 列出 / 吊销（V0.5）。

支付闭环上线前，付费用户的 key 由运营人工签发：

    python scripts/issue_key.py issue --label "微信用户小王" --tier pro --quota 500
    python scripts/issue_key.py list
    python scripts/issue_key.py revoke sv-xxxxxxxx

直接操作 SNACKVALUE_DB_PATH（或项目内 data/）指向的 SQLite，无需服务在线。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import database as db
from backend.billing import issue_key, list_keys, purge_keys, revoke_key


def main() -> int:
    parser = argparse.ArgumentParser(description="SnackValue API Key 管理")
    sub = parser.add_subparsers(dest="command", required=True)

    p_issue = sub.add_parser("issue", help="签发新 key")
    p_issue.add_argument("--label", default="", help="备注（用户/渠道名）")
    p_issue.add_argument("--tier", default="free", choices=["free", "pro"])
    p_issue.add_argument("--quota", type=int, default=None,
                         help="每日配额覆盖；不传 = 用全局 SNACKVALUE_DAILY_QUOTA")

    sub.add_parser("list", help="列出全部 key（脱敏）与用量")

    p_revoke = sub.add_parser("revoke", help="吊销 key")
    p_revoke.add_argument("key", help="完整 api_key")

    p_purge = sub.add_parser("purge", help="删除全部 key 记录，服务回到开放模式")
    p_purge.add_argument("--yes", action="store_true", help="确认执行（必填）")

    args = parser.parse_args()
    db.init_db()

    if args.command == "issue":
        info = issue_key(label=args.label, tier=args.tier, daily_quota=args.quota)
        print("签发成功（完整 key 仅显示这一次，请立即保存）：")
        print(f"  api_key    : {info['api_key']}")
        print(f"  label      : {info['label'] or '-'}")
        print(f"  tier       : {info['tier']}")
        print(f"  daily_quota: {info['daily_quota'] if info['daily_quota'] is not None else '全局默认'}")
    elif args.command == "list":
        keys = list_keys()
        if not keys:
            print("（还没有签发过 key）")
        for k in keys:
            status = "已吊销" if k["revoked_at"] else "有效"
            quota = k["daily_quota"] if k["daily_quota"] is not None else "全局"
            print(f"{k['api_key_masked']}  [{status}] tier={k['tier']} quota={quota} "
                  f"今日={k['usage_today']} 累计={k['usage_total']} label={k['label'] or '-'}")
    elif args.command == "revoke":
        if revoke_key(args.key):
            print(f"已吊销：{args.key}（服务保持认证模式；要回开放模式请用 purge）")
        else:
            print("key 不存在或已吊销", file=sys.stderr)
            return 1
    elif args.command == "purge":
        if not args.yes:
            print("危险操作：将删除全部 key 且服务回到开放模式。确认请加 --yes", file=sys.stderr)
            return 1
        n = purge_keys()
        print(f"已删除 {n} 条 key 记录，服务回到开放模式")
    return 0


if __name__ == "__main__":
    sys.exit(main())
