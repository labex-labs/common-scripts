import re
import json
import requests
import argparse
from datetime import datetime, timedelta


class Feishu:
    """Feishu API"""

    def __init__(self, app_id: str, app_secret: str) -> None:
        self.app_id = app_id
        self.app_secret = app_secret

    def tenant_access_token(self):
        """Get tenant access token"""
        r = requests.post(
            url="https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            headers={
                "Content-Type": "application/json; charset=utf-8",
            },
            data=json.dumps({"app_id": self.app_id, "app_secret": self.app_secret}),
        )
        return r.json()["tenant_access_token"]

    def get_bitable_records(self, app_token: str, table_id: str, params: str) -> None:
        """Get bitable records"""
        records = []
        r = requests.get(
            url=f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records?{params}",
            headers={
                "Authorization": f"Bearer {self.tenant_access_token()}",
            },
        )
        if r.json()["data"]["total"] > 0:
            records += r.json()["data"]["items"]
            # 当存在多页时，递归获取
            while r.json()["data"]["has_more"]:
                page_token = r.json()["data"]["page_token"]
                r = requests.get(
                    url=f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records?page_token={page_token}&{params}",
                    headers={
                        "Authorization": f"Bearer {self.tenant_access_token()}",
                    },
                )
                if r.json()["data"]["total"] > 0:
                    records += r.json()["data"]["items"]
        return records

    def add_bitable_record(self, app_token: str, table_id: str, data: dict) -> None:
        """Add record to bitable"""
        r = requests.post(
            url=f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            headers={
                "Authorization": f"Bearer {self.tenant_access_token()}",
                "Content-Type": "application/json; charset=utf-8",
            },
            data=json.dumps(data),
        )
        return r.json()

    def update_bitable_record(
        self, app_token: str, table_id: str, record_id: str, data: dict
    ) -> None:
        """Update record in bitable"""
        r = requests.put(
            url=f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
            headers={
                "Authorization": f"Bearer {self.tenant_access_token()}",
                "Content-Type": "application/json; charset=utf-8",
            },
            data=json.dumps(data),
        )
        return r.json()

    def delete_bitable_record(
        self, app_token: str, table_id: str, record_id: str
    ) -> None:
        """Delete record in bitable"""
        r = requests.delete(
            url=f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
            headers={
                "Authorization": f"Bearer {self.tenant_access_token()}",
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        return r.json()


class GitHub:
    """GitHub 相关 API"""

    def __init__(self, token: str) -> None:
        self.token = token

    def get_issue(self, repo_name: str, issue_number: int) -> str:
        url = f"https://api.github.com/repos/{repo_name}/issues/{issue_number}"
        headers = {
            "Authorization": "token " + self.token,
            "Accept": "application/vnd.github+json",
        }
        r = requests.get(url, headers=headers)
        return r.json()

    def patch_pr_assignees(
        self, repo_name: str, pr_number: int, assignees: list
    ) -> dict:
        url = f"https://api.github.com/repos/{repo_name}/issues/{pr_number}"
        r = requests.patch(
            url=url,
            headers={
                "Authorization": "token " + self.token,
                "Accept": "application/vnd.github+json",
            },
            data=json.dumps({"assignees": assignees}),
        )
        return r.json()

    def comment_pr(self, repo_name: str, pr_number: int, comment_text: str) -> dict:
        url = f"https://api.github.com/repos/{repo_name}/issues/{pr_number}/comments"
        r = requests.post(
            url=url,
            headers={
                "Authorization": "token " + self.token,
                "Accept": "application/vnd.github+json",
            },
            data=json.dumps(
                {
                    "body": comment_text,
                }
            ),
        )
        return r.json()

    def get_pr_list(self, repo_name: str) -> list:
        """获取 pr 列表

        Args:
            repo_name (str): 仓库名称
        """
        url = f"https://api.github.com/repos/{repo_name}/pulls"
        headers = {
            "Authorization": "token " + self.token,
            "Accept": "application/vnd.github+json",
        }
        params = {
            "state": "all",
            "per_page": 100,
        }

        all_pulls = []
        page = 1

        while True:
            params["page"] = page
            print(f"Fetching page {page} of pulls...")
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                raise Exception(
                    f"Error retrieving pulls: {response.status_code}, {response.text}"
                )

            pulls = response.json()
            if not pulls:
                break

            all_pulls.extend(pulls)
            page += 1

        # 仅保留 open 和 merged 状态的 PR
        only_pulls = [
            pull
            for pull in all_pulls
            if pull["state"] == "open" or pull.get("merged_at") is not None
        ]
        return only_pulls


class Sync:
    def __init__(self, app_id: str, app_secret: str, ghtoken: str) -> None:
        self.ghtoken = ghtoken
        self.github = GitHub(token=ghtoken)
        self.feishu = Feishu(app_id, app_secret)
        self.app_token = "bascnNz4Nqjqgqm1Nm5AYke6xxb"
        self.table_id = "tblExqBjw46rHCre"

    def pr_index_json(self, repo_name: str, pr_number: int) -> list:
        url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}/files"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": "token " + self.ghtoken,
        }
        response = requests.get(url, headers=headers)
        raw_urls = []
        for file in response.json():
            if "index.json" in file["filename"]:
                raw_url = file["raw_url"]
                filename = file["filename"]
                raw_urls.append(
                    {
                        "raw_url": raw_url,
                        "filename": filename,
                    }
                )
        if len(raw_urls) == 1:
            print(f"→ Found {len(raw_urls)} index.json in PR#{pr_number}.")
            index_json = requests.get(raw_urls[0]["raw_url"]).json()
            lab_path = raw_urls[0]["filename"].removesuffix("/index.json")
            return index_json, lab_path
        else:
            return None, None

    def pr_reviews(self, repo_name: str, pr_number: int) -> list:
        url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}/reviews"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": "token " + self.ghtoken,
        }
        response = requests.get(url, headers=headers)
        approved_by = []
        changes_requested_by = []
        for review in response.json():
            if review["state"] == "APPROVED":
                approved_by.append(review["user"]["login"])
            elif review["state"] == "CHANGES_REQUESTED":
                changes_requested_by.append(review["user"]["login"])
        return list(set(approved_by)), list(set(changes_requested_by))

    def unix_ms_timestamp(self, time_str: str) -> int:
        if time_str != None:
            date_obj = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ") + timedelta(
                hours=8
            )
            unix_ms_timestamp = int(date_obj.timestamp() * 1000)
        else:
            unix_ms_timestamp = 946656000000
        return unix_ms_timestamp

    def get_pr_assign_issue_id(self, pr_body: str) -> int:
        issue_id_str_1 = re.findall(r"- fix #(\d+)", pr_body)
        issue_id_str_2 = re.findall(
            r"- fix https:\/\/github\.com\/labex-labs\/scenarios\/issues\/(\d+)",
            pr_body,
        )
        try:
            issue_id = int(issue_id_str_1[0])
        except:
            try:
                issue_id = int(issue_id_str_2[0])
            except:
                issue_id = 0
        return issue_id

    def sync_pr(self, repo_name: str) -> None:
        # Get all records from feishu
        records = self.feishu.get_bitable_records(
            self.app_token, self.table_id, params=""
        )
        # Make a dict of PR_NUMBER and record_id
        num_id_dicts = {r["fields"]["PR_NUM"]: r["record_id"] for r in records}
        # Get all pr from github
        pr_list = self.github.get_pr_list(repo_name)
        print(f"Found {len(pr_list)} PR in GitHub.")
        # Feishu 未关闭的 PR
        feishu_not_closed_pr_nums = [str(r["fields"]["PR_NUM"]) for r in records if r["fields"]["PR_STATE"] == "OPEN"]
        print(f"Found {len(feishu_not_closed_pr_nums)} OPEN PR in Feishu.")
        # 忽略已经关闭的 PR
        pr_list = [
            pr
            for pr in pr_list
            if pr["state"] == "open" or str(pr["number"]) in feishu_not_closed_pr_nums
        ]
        print(f"Processing {len(pr_list)} OPEN PR...")
        for pr in pr_list:
            try:
                # Parse and Update index.json
                pr_number = pr["number"]
                pr_user = pr["user"]["login"]
                pr_state = pr["state"]
                # assignees
                assignees = pr["assignees"]
                if len(assignees) == 0 or assignees == None:
                    assignees_list = []
                else:
                    assignees_list = [a["login"] for a in assignees]
                # labels
                pr_labels = pr["labels"]
                if len(pr_labels) == 0:
                    pr_labels_list = []
                else:
                    pr_labels_list = [l["name"] for l in pr_labels]
                print(f"Processing PR#{pr_number}...")
                index_json, lab_path = self.pr_index_json(repo_name, pr_number)
                if index_json != None:
                    lab_title = index_json.get("title")
                    lab_type = index_json.get("type")
                    lab_steps = index_json.get("details").get("steps")
                    pr_title = pr["title"]
                    pr_html_url = pr["html_url"]
                    # milestone
                    milestone = pr.get("milestone")
                    if milestone != None:
                        milestone = pr.get("milestone").get("title")
                    # pr_reviews
                    approved_by, changes_requested_by = self.pr_reviews(
                        repo_name, pr_number
                    )
                    # created at
                    created_at = self.unix_ms_timestamp(pr["created_at"])
                    updated_at = self.unix_ms_timestamp(pr["updated_at"])
                    merged_at = self.unix_ms_timestamp(pr["merged_at"])
                    # payloads
                    payloads = {
                        "fields": {
                            "SCENARIO_TITLE": lab_title,
                            "SCENARIO_PATH": lab_path,
                            "SCENARIO_SLUG": lab_path.split("/")[-1],
                            "SCENARIO_TYPE": lab_type,
                            "SCENARIO_STEP": len(lab_steps),
                            "PR_TITLE": pr_title,
                            "PR_USER": pr_user,
                            "PR_NUM": pr_number,
                            "PR_STATE": pr_state.upper(),
                            "PR_LABELS": pr_labels_list,
                            "ASSIGNEES": assignees_list,
                            "MILESTONE": milestone,
                            "CHANGES_REQUESTED": changes_requested_by,
                            "APPROVED": approved_by,
                            "CREATED_AT": created_at,
                            "UPDATED_AT": updated_at,
                            "MERGED_AT": merged_at,
                            "HTML_URL": {
                                "link": pr_html_url,
                                "text": "OPEN IN GITHUB",
                            },
                        }
                    }
                    # Update record
                    if str(pr_number) in num_id_dicts.keys():
                        r = self.feishu.update_bitable_record(
                            self.app_token,
                            self.table_id,
                            num_id_dicts[str(pr_number)],
                            payloads,
                        )
                        print(f"→ Updating {lab_path} {r['msg'].upper()}")
                    else:
                        # Add record
                        r = self.feishu.add_bitable_record(
                            self.app_token, self.table_id, payloads
                        )
                        print(f"↑ Adding {lab_path} {r['msg'].upper()}")
                else:
                    print(f"→ Skipping {pr_number} because no index.json found.")
                # Assign issue user to PR
                pr_body = pr["body"]
                issue_id = self.get_pr_assign_issue_id(pr_body)
                # 如果 pr_state 为 open
                if pr_state == "open":
                    # 如果 issue_id 不为 0
                    if issue_id != 0:
                        issue = self.github.get_issue(repo_name, issue_id)
                        issue_user = issue["user"]["login"]
                        # 判断是否已经测试完成
                        if "Test Completed" in pr_labels_list:
                            # 测试完成，如果 issue user 不等于 pr_user
                            if issue_user != pr_user:
                                # 且 issue user 不在 assignees 里，准备添加
                                if issue_user not in assignees_list:
                                    # 添加 issue user
                                    assignees_list.append(issue_user)
                                    comment = f"Hi, @{issue_user} \n\n由于该 PR 关联了由你创建的 Issue，系统已将你自动分配为 Reviewer，请你及时完成 Review，并和作者进行沟通。确认无误后，可以执行 `Approve` 操作，LabEx 会二次确认后再合并。请勿自行合并 PR。\n\n- Review 操作指南和标准详见：https://www.labex.wiki/zh/advanced/how-to-review \n\n如有疑问可以直接回复本条评论，或者微信联系。"
                                    self.github.patch_pr_assignees(
                                        repo_name, pr_number, assignees_list
                                    )
                                    self.github.comment_pr(
                                        repo_name, pr_number, comment
                                    )
                                    print(
                                        f"→ Adding {issue_user} as a reviewer to PR#{pr_number}."
                                    )
                                else:
                                    print(f"→ {issue_user} is already a reviewer.")
                            # 测试完成，如果 issue user 等于 pr_user
                            else:
                                # 且 huhuhang 不在 assignees 里，准备添加
                                if "huhuhang" not in assignees_list:
                                    # 添加 huhuhang
                                    assignees_list.append("huhuhang")
                                    comment = f"Hi, @huhuhang \n\n系统已将你自动分配为 Reviewer，请你及时完成 Review，并和作者进行沟通。确认无误后，可以执行 `Approve` 操作，LabEx 会二次确认后再合并。请勿自行合并 PR。\n\n- Review 操作指南和标准详见：https://www.labex.wiki/zh/advanced/how-to-review \n\n如有疑问可以直接回复本条评论，或者微信联系。"
                                    self.github.patch_pr_assignees(
                                        repo_name, pr_number, assignees_list
                                    )
                                    self.github.comment_pr(
                                        repo_name, pr_number, comment
                                    )
                                    print(
                                        f"→ Adding huhuhang as a reviewer to PR#{pr_number}."
                                    )
                                else:
                                    print(f"→ huhuhang is already a reviewer.")
                        else:
                            # 未测完
                            print(f"→ PR#{pr_number} is not Test Completed")
                    # 如果 issue_id 为 0
                    else:
                        comment = f"Hi, @{pr_user} \n\n该 PR 未检测到正确关联 Issue，请你在 PR 描述中按要求添加，如有问题请及时联系 LabEx 的同事。\n\n如有疑问可以直接回复本条评论，或者微信联系。"
                        self.github.comment_pr(repo_name, pr_number, comment)
                        print(
                            f"→ No issue id found in {pr_number}, comment to {pr_user}"
                        )
                else:
                    print(
                        f"→ Skipping add Reviewer to PR#{pr_number}, because it's closed."
                    )
            except Exception as e:
                print(f"Exception: {e}")
                continue


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Repo PRs to Feishu")
    parser.add_argument("--appid", type=str, help="Feishu App ID")
    parser.add_argument("--appsecret", type=str, help="Feishu App Secret")
    parser.add_argument(
        "--repo", type=str, help="Repo Name like 'labex-dev/devops-labs'"
    )
    parser.add_argument("--ghtoken", type=str, help="GitHub Token")
    args = parser.parse_args()
    main = Sync(app_id=args.appid, app_secret=args.appsecret, ghtoken=args.ghtoken)
    main.sync_pr(repo_name=args.repo)
