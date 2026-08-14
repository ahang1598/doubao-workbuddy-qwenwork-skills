# paper-write-zh 交付编排（Makefile 声明式）
#
# 设计原则见同目录 SKILL.md。核心：控制流在 make 里，不在模型脑子里。
# 模型只需运行 `make`，make 依赖图会强制 prepare -> write -> deliver 的顺序，
# 任何一步的产物或检查未过，都会停在最早未满足的那一步并打印修复指令。
#
# 状态即产物文件：不存在 handoff.json，不存在模型维护的 state.json。
# 阶段是否完成，由脚本检查 .workflow/ 下真实文件算出。
#
# 用法：
#   make prepare     只跑准备阶段检查
#   make write       跑到写作阶段检查（自动先要求 prepare 通过）
#   make deliver     按 meta.output_target 交付（默认目标，自动串起前两阶段）
#   make status      打印三态结论 PASS / BLOCKED / DRAFT_ONLY
#   make clean       清理交付中间产物（不删正文与来源池）
#
# 明确篇幅写入 meta.json 的 min_chars/max_chars；标题取终稿首个一级标题。

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.PHONY: all prepare write deliver status clean help FORCE

# ---- 可配置变量 ----
WF          := .workflow
SCRIPTS     := scripts
MIN_CHARS   ?=
MAX_CHARS   ?=
MIN_SOURCES ?= 3
# 来源池默认必须含可追溯 URL；沙箱无外网只校验字段存在，不校验可达。
REQUIRE_URL ?= 1
# 仅当用户针对本次文档明确授权“互联网获得链接者可读”时设为 1。
PUBLIC_LARK ?= 0
PUBLIC_LARK_ORIGIN := $(origin PUBLIC_LARK)

# ---- 产物文件（即状态）----
META        := $(WF)/meta.json
SOURCE_POOL := $(WF)/source_pool.md
DRAFT       := $(WF)/paper_draft.md
ORIGINAL    := $(WF)/original_draft.md
REVISION_CONTRACT := $(WF)/revision_contract.json
FINAL       := $(WF)/paper_final.md
PREPARE_OK  := $(WF)/prepare_check.json
DRAFT_OK    := $(WF)/draft_check.json
LARK_OK     := $(WF)/lark_check.json
DOC_RESULT  := $(WF)/doc-result.json
DOC_UPDATE  := $(WF)/doc-update-result.json
DOC_FETCH   := $(WF)/doc_fetch.xml
PERMISSION_RESULT := $(WF)/permission-result.json

URL_FLAG    := $(if $(filter 1,$(REQUIRE_URL)),--require-url,)
DRAFT_RANGE_FLAGS := $(if $(strip $(MIN_CHARS)),--min-chars $(MIN_CHARS)) $(if $(strip $(MAX_CHARS)),--max-chars $(MAX_CHARS))

all: deliver

# ---- 阶段一：准备（读材料 + 来源池可追溯检查）----
# 产物：meta.json、（需引用时）source_pool.md。检查通过写 prepare_check.json。
$(PREPARE_OK): $(META) FORCE
	@mkdir -p $(WF)
	@echo "=== [prepare] 校验任务元数据与来源池可追溯字段 ==="
	@python3 $(SCRIPTS)/check_prepare.py \
		--meta $(META) \
		--source-pool $(SOURCE_POOL) \
		--min-sources $(MIN_SOURCES) \
		$(URL_FLAG) \
		--write-report $(PREPARE_OK)
	@echo "[prepare] 通过"

$(META):
	@mkdir -p $(WF)
	@echo "❌ 缺少 $(META)"
	@echo "请创建 $(META)，示例："
	@echo '  {"mode":"draft","task_scope":"full_paper","paper_type":"journal",'
	@echo '   "discipline_branch":"technical","needs_citation":"yes",'
	@echo '   "output_target":"markdown_and_lark","citation_style":"gbt7714_numeric"}'
	@echo "需要引用时还需创建 $(SOURCE_POOL)，每条来源含题录、核验状态、"
	@echo "核验依据与可访问 URL；只有状态为“已核验”的条目计入来源数。"
	@exit 1

prepare: $(PREPARE_OK)

# ---- 阶段二：写作（蓝图 + 成稿）----
# 依赖 prepare 通过。产物：paper_draft.md。检查通过写 draft_check.json。
$(DRAFT_OK): $(PREPARE_OK) $(DRAFT)
	@echo "=== [write] 校验正文形态 ==="
	@python3 $(SCRIPTS)/check_draft.py \
		--input $(DRAFT) \
		--meta $(META) \
		--source-pool $(SOURCE_POOL) \
		--original $(ORIGINAL) \
		--revision-contract $(REVISION_CONTRACT) \
		$(DRAFT_RANGE_FLAGS) \
		--write-report $(DRAFT_OK)
	@echo "[write] 通过"

$(DRAFT):
	@echo "❌ 缺少正文 $(DRAFT)"
	@echo "请把论文正文写入 $(DRAFT)：按学科结构分节，文献性判断带文内引用，"
	@echo "只用已核验来源，正文不残留 ** 加粗、emoji、AI 过程说明。"
	@exit 1

write: $(DRAFT_OK)

# ---- 阶段三：交付（清洁终稿 + 飞书 + 读回）----
# 终稿由检查通过的正文生成。这里做最小清洁：直接复制为 final，
# 深度清洁规则已在 check_draft 拦截，故终稿等同通过检查的正文。
$(FINAL): $(DRAFT_OK)
	@cp $(DRAFT) $(FINAL)
	@echo "[deliver] 终稿已生成 $(FINAL)"

# deliver：meta.output_target 是唯一交付目标；markdown_only 不创建飞书，
# markdown_and_lark 创建后查询权限、读回正文，并把两类结果汇入 lark_check。
# 注意：lark-cli 的 --content @file 要求相对路径，故创建文档一步 cd 进 .workflow；
# 该步放进子 shell (…) 隔离，避免 .ONESHELL 下 cd 影响后续行的路径基准。
deliver: $(FINAL)
	@set -euo pipefail
	OUTPUT_TARGET=$$(python3 -c 'import json; print(json.load(open("$(META)", encoding="utf-8-sig"))["output_target"])')
	run_status() {
		python3 $(SCRIPTS)/status.py --workflow $(WF)
	}
	fail_lark() {
		FAILURE_MESSAGE="$$1"
		python3 -c 'import hashlib, json, sys; from pathlib import Path; report, source, permission = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]); result = {"source_sha256": hashlib.sha256(source.read_text(encoding="utf-8-sig").encode("utf-8")).hexdigest()}; result.update({"permission_public": json.loads(permission.read_text(encoding="utf-8-sig"))["data"]["permission_public"]} if permission.exists() else {}); payload = {"status": "fail", "stage": "deliver", "failures": [sys.argv[4]], "fix": "按失败原因处理后重跑 make deliver。", "result": result}; report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")' \
			"$(LARK_OK)" "$(FINAL)" "$(PERMISSION_RESULT)" "$$FAILURE_MESSAGE"
		run_status || true
		exit 1
	}
	if [ "$$OUTPUT_TARGET" = "markdown_only" ]; then
		echo "=== [deliver] output_target=markdown_only，仅生成终稿 ==="
		run_status
		exit 0
	fi
	if [ "$$OUTPUT_TARGET" != "markdown_and_lark" ]; then
		echo "❌ 未实现的 output_target：$$OUTPUT_TARGET"
		exit 1
	fi
	if [ "$(PUBLIC_LARK)" != "0" ] && [ "$(PUBLIC_LARK)" != "1" ]; then
		fail_lark "PUBLIC_LARK 只接受0或1；1仅表示用户已明确授权本次文档使用 anyone_readable 公网档位。"
	fi
	if [ "$(PUBLIC_LARK)" = "1" ] && [ "$(PUBLIC_LARK_ORIGIN)" != "command line" ]; then
		fail_lark "PUBLIC_LARK=1 必须由本次 make 命令行显式传入，不能继承环境变量或文件默认值。"
	fi
	rm -f $(LARK_OK) $(DOC_RESULT) $(DOC_FETCH) $(PERMISSION_RESULT) \
		$(DOC_UPDATE) $(WF)/doc-result.tmp.json $(WF)/permission-result.tmp.json
	if ! DOC_TITLE=$$(python3 -c 'import pathlib,re,sys; text=pathlib.Path(sys.argv[1]).read_text(encoding="utf-8-sig"); match=re.search(r"(?m)^#\s+(.+?)\s*$$",text); assert match and match.group(1).strip(); print(match.group(1).strip())' "$(FINAL)"); then
		fail_lark "无法从终稿读取文档标题。"
	fi
	echo "=== [deliver] 创建无正文飞书文档并先验权 ==="
	if ! ( cd $(WF) && lark-cli docs +create --title "$$DOC_TITLE" \
		--format json > doc-result.tmp.json ); then
		rm -f $(WF)/doc-result.tmp.json
		fail_lark "飞书文档创建失败；检查 lark-cli 登录、授权范围与命令错误输出。"
	fi
	mv $(WF)/doc-result.tmp.json $(DOC_RESULT)
	if ! DOC_ID=$$(python3 -c 'import json, sys; data = json.load(open(sys.argv[1], encoding="utf-8-sig")); assert data.get("ok") is True; print(data["data"]["document"]["document_id"])' "$(DOC_RESULT)"); then
		fail_lark "飞书创建结果缺少有效 document_id；检查 $(DOC_RESULT)。"
	fi
	if ! DOC_URL=$$(python3 -c 'import json, sys; data = json.load(open(sys.argv[1], encoding="utf-8-sig")); print(data["data"]["document"]["url"])' "$(DOC_RESULT)"); then
		fail_lark "飞书创建结果缺少有效文档 URL；检查 $(DOC_RESULT)。"
	fi
	if [ -z "$$DOC_ID" ] || [ "$$DOC_ID" = "null" ] || [ -z "$$DOC_URL" ]; then
		fail_lark "飞书创建结果中的 document_id 或 URL 为空；检查 $(DOC_RESULT)。"
	fi
	echo "[deliver] 文档已创建：$$DOC_URL"
	if [ "$(PUBLIC_LARK)" = "1" ]; then
		echo "=== [deliver] 按本次明确授权设置互联网获得链接者可读 ==="
		if ! lark-cli drive permission.public patch --token "$$DOC_ID" --type docx \
			--data '{"external_access": true, "link_share_entity": "anyone_readable"}' \
			--format json --yes > /dev/null; then
			fail_lark "公开权限设置失败；检查租户策略、文档密级、授权范围与命令错误输出。"
		fi
	else
		echo "=== [deliver] 不修改权限，只读验证文档为私有 ==="
	fi
	echo "=== [deliver] 查询权限状态 ==="
	if ! lark-cli drive +permission-get-setting --token "$$DOC_ID" --type docx \
		--format json > $(WF)/permission-result.tmp.json; then
		rm -f $(WF)/permission-result.tmp.json
		fail_lark "飞书权限查询失败；无法证明文档处于目标权限档位。"
	fi
	mv $(WF)/permission-result.tmp.json $(PERMISSION_RESULT)
	if ! python3 -c 'import json, sys; permission = json.load(open(sys.argv[1], encoding="utf-8-sig"))["data"]["permission_public"]; public = sys.argv[2] == "1"; valid = permission.get("external_access") is public and permission.get("link_share_entity") == ("anyone_readable" if public else "closed"); raise SystemExit(0 if valid else 1)' \
		"$(PERMISSION_RESULT)" "$(PUBLIC_LARK)"; then
		if [ "$(PUBLIC_LARK)" = "1" ]; then
			fail_lark "权限读回不符合已授权的公开档位：要求 external_access=true 且 link_share_entity=anyone_readable。"
		else
			fail_lark "权限读回不是私有档位：要求 external_access=false 且 link_share_entity=closed；未获本轮针对该文档的确认，不会自动收紧权限。"
		fi
	fi
	echo "=== [deliver] 权限符合合同，写入终稿 ==="
	if ! ( cd $(WF) && lark-cli docs +update --doc "$$DOC_ID" --command overwrite \
		--doc-format markdown --content @paper_final.md --format json > doc-update-result.json ); then
		fail_lark "飞书文档已通过权限检查，但正文写入失败；检查 $(DOC_UPDATE)。"
	fi
	echo "=== [deliver] 读回校验 ==="
	if ! lark-cli docs +fetch --doc "$$DOC_URL" \
		--doc-format xml --format json \
		| python3 -c 'import json, sys; print(json.load(sys.stdin)["data"]["document"]["content"])' \
		> $(DOC_FETCH); then
		fail_lark "飞书文档读回失败；检查文档访问权限、登录状态与命令错误输出。"
	fi
	CHECK_RC=0
	python3 $(SCRIPTS)/check_lark.py --xml $(DOC_FETCH) --source $(FINAL) \
		--meta $(META) --write-report $(LARK_OK) || CHECK_RC=$$?
	if [ "$$CHECK_RC" -ne 0 ]; then
		if ! python3 -c 'import json, sys; report = json.load(open(sys.argv[1], encoding="utf-8-sig")); raise SystemExit(0 if report.get("status") == "fail" else 1)' "$(LARK_OK)"; then
			fail_lark "飞书读回检查执行失败，且未生成有效的失败 lark_check.json。"
		fi
	fi
	if ! python3 -c 'import hashlib, json, sys; from pathlib import Path; report_path, permission_path = Path(sys.argv[1]), Path(sys.argv[2]); report = json.loads(report_path.read_text(encoding="utf-8-sig")); snapshot = json.loads(permission_path.read_text(encoding="utf-8-sig")); result = report.setdefault("result", {}); result["permission_public"] = snapshot["data"]["permission_public"]; result["permission_snapshot_file"] = sys.argv[2]; result["permission_snapshot_sha256"] = hashlib.sha256(permission_path.read_bytes()).hexdigest(); result["permission_mode"] = "public_anyone_readable" if sys.argv[5] == "1" else "non_public"; result["document_url"] = sys.argv[3]; result["document_id"] = sys.argv[4]; report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")' \
		"$(LARK_OK)" "$(PERMISSION_RESULT)" "$$DOC_URL" "$$DOC_ID" "$(PUBLIC_LARK)"; then
		fail_lark "无法把权限状态合并进 lark_check.json。"
	fi
	if [ "$$CHECK_RC" -ne 0 ]; then
		run_status || true
		exit 1
	fi
	echo ""
	echo "🎉 交付完成，文档链接：$$DOC_URL"
	run_status

# ---- 三态结论 ----
status:
	@python3 $(SCRIPTS)/status.py --workflow $(WF)

# 只清交付中间产物；保留 meta、来源池、正文、终稿，支持增量重跑。
clean:
	@rm -f $(PREPARE_OK) $(DRAFT_OK) $(LARK_OK) $(DOC_RESULT) $(DOC_FETCH) \
		$(PERMISSION_RESULT) $(DOC_UPDATE) $(WF)/doc-result.tmp.json $(WF)/permission-result.tmp.json
	@echo "已清理交付中间产物，正文与来源池保留。"

help:
	@echo "make prepare | write | deliver | status | clean"
	@echo "交付目标只读取 $(META) 的 output_target：markdown_only | markdown_and_lark"
	@echo "变量：MIN_CHARS MAX_CHARS MIN_SOURCES REQUIRE_URL PUBLIC_LARK"
	@echo "持久篇幅要求写入 meta.json 的 min_chars/max_chars；命令行变量仅覆盖本次调用。"
	@echo "PUBLIC_LARK=1 仅表示用户明确授权本次文档为互联网获得链接者可读。"

FORCE:
