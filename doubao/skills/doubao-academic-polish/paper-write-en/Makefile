# paper-write-en 交付编排（Makefile 声明式）
#
# 设计原则见同目录 SKILL.md。核心：控制流在 make 里，不在模型脑子里。
# 模型只需运行 `make`，make 依赖图会强制 prepare -> write -> deliver 的顺序，
# 任何一步的产物或检查未过，都会停在最早未满足的那一步并打印修复指令。
#
# 状态即产物文件：不存在 handoff.json，不存在模型维护的 state.json。
# 阶段是否完成，由脚本检查 .workflow/ 下真实文件算出。
#
# 与中文侧的唯一实质差异：prepare 阶段的来源门是 verify_literature.py 的
# 真实性联网核验（Crossref/OpenAlex/Semantic Scholar 三源），只有 A/B 级、
# 通过 title/author/doi 校验的文献进 core_literature。需要引用时无网会阻断。
#
# 用法：
#   make prepare     校验 meta + 候选文献验真
#   make write       校验英文正文（引用体例/章节顺序/词数）
#   make deliver     按 meta.output_target 生成终稿或交付飞书（默认目标）
#   make status      打印 PASS / BLOCKED / DRAFT_ONLY
#   make clean       清理交付中间产物
#
# 明确篇幅写入 meta.json 的 min_words/max_words；标题取终稿首个一级标题。

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.PHONY: all prepare write deliver status clean help FORCE

# ---- 可配置变量 ----
WF          := .workflow
SCRIPTS     := scripts
STYLE       ?= apa7
MIN_WORDS   ?=
MAX_WORDS   ?=
MIN_CORE    ?= 1
# 仅无引用任务可设为1；needs_citation=yes时离线模式会阻断prepare。
OFFLINE     ?= 0
# 仅当用户已针对本次交付文档明确授权 anyone_readable 公网档位时设为1。
PUBLIC_LARK ?= 0
PUBLIC_LARK_ORIGIN := $(origin PUBLIC_LARK)

# ---- 产物文件（即状态）----
META        := $(WF)/meta.json
CANDIDATES  := $(WF)/candidates.json
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
LARK_PERMISSION := $(WF)/lark_permission.json
LARK_PATCH  := $(WF)/lark_permission_patch.json
LARK_ERROR  := $(WF)/lark_error.log
REGISTRY    := $(SCRIPTS)/quality-registry.sample.json

OFFLINE_FLAG := $(if $(filter 1,$(OFFLINE)),--offline,)
WORD_RANGE_FLAGS := $(if $(strip $(MIN_WORDS)),--min-words $(MIN_WORDS)) $(if $(strip $(MAX_WORDS)),--max-words $(MAX_WORDS))

all: deliver

# ---- 阶段一：准备（任务定位 + 候选文献验真）----
# 产物：meta.json、（需引用时）candidates.json。通过后写 prepare_check.json、verified_refs.json。
$(PREPARE_OK): $(META) FORCE
	@mkdir -p $(WF)
	@echo "=== [prepare] 校验元数据并对候选文献验真 ==="
	@python3 $(SCRIPTS)/check_prepare.py \
		--meta $(META) \
		--candidates $(CANDIDATES) \
		--workflow $(WF) \
		--min-core $(MIN_CORE) \
		--quality-registry $(REGISTRY) \
		$(OFFLINE_FLAG) \
		--write-report $(PREPARE_OK)
	@echo "[prepare] 通过"

$(META):
	@mkdir -p $(WF)
	@echo "❌ 缺少 $(META)"
	@echo "请创建 $(META)，示例："
	@echo '  {"task_scope":"full_paper","paper_type":"research_article",'
	@echo '   "citation_style":"apa7","needs_citation":"yes","output_target":"lark"}'
	@echo "需要引用时还需创建 $(CANDIDATES)：{\"references\":[{title,first_author,url,doi,...}]}。"
	@exit 1

prepare: $(PREPARE_OK)

# ---- 阶段二：写作（英文正文成稿）----
$(DRAFT_OK): $(PREPARE_OK) $(DRAFT)
	@echo "=== [write] 校验英文正文形态 ==="
	@python3 $(SCRIPTS)/check_draft.py \
		--input $(DRAFT) \
		--meta $(META) \
		--verified-refs $(WF)/verified_refs.json \
		--original $(ORIGINAL) \
		--revision-contract $(REVISION_CONTRACT) \
		$(WORD_RANGE_FLAGS) \
		--write-report $(DRAFT_OK)
	@echo "[write] 通过"

$(DRAFT):
	@echo "❌ 缺少正文 $(DRAFT)"
	@echo "请把英文论文正文写入 $(DRAFT)：按 subskill 各 guide 的章节顺序，"
	@echo "只用已验真文献，文内引用用作者-年份或编号，文末 References 按体例，"
	@echo "正文为连贯论述不用列表，不残留验真中间字段。"
	@exit 1

write: $(DRAFT_OK)

# ---- 阶段三：交付（终稿 + 飞书 + 读回）----
$(FINAL): $(DRAFT_OK)
	@cp $(DRAFT) $(FINAL)
	@echo "[deliver] 终稿已生成 $(FINAL)"

# deliver：飞书全程纯 shell。任何 lark-cli/读回检查失败都先写 lark_check.json，
# 再由 status.py 输出三态；不得以未归档的原始 shell 错误作为交付结论。
deliver: $(FINAL)
	@set -euo pipefail
	DOC_ID=""
	DOC_URL=""
	write_lark_failure() { \
		LARK_FAILURE_STEP="$$1" \
		LARK_FAILURE_REASON="$$2" \
		LARK_DOCUMENT_ID="$${DOC_ID:-}" \
		LARK_DOCUMENT_URL="$${DOC_URL:-}" \
		python3 -c 'import hashlib,json,os; from pathlib import Path; source=Path("$(FINAL)").read_text(encoding="utf-8-sig"); permission=Path("$(LARK_PERMISSION)"); result={"source_sha256":hashlib.sha256(source.encode("utf-8")).hexdigest(),"failure_step":os.environ["LARK_FAILURE_STEP"],"document_id":os.environ.get("LARK_DOCUMENT_ID",""),"document_url":os.environ.get("LARK_DOCUMENT_URL",""),"permission_snapshot_file":"$(LARK_PERMISSION)","permission_snapshot_available":permission.is_file(),"permission_snapshot_sha256":hashlib.sha256(permission.read_bytes()).hexdigest() if permission.is_file() else ""}; payload={"status":"fail","stage":"deliver","failures":[os.environ["LARK_FAILURE_REASON"]],"result":result,"fix":"按失败步骤修复后重新运行 make deliver；不得绕过权限读回或飞书内容校验。"}; Path("$(LARK_OK)").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")'; \
	}
	finish_with_status() { \
		set +e; \
		python3 $(SCRIPTS)/status.py --workflow $(WF) "$$@"; \
		status_rc=$$?; \
		set -e; \
		exit "$$status_rc"; \
	}
	block_lark() { \
		write_lark_failure "$$1" "$$2"; \
		finish_with_status; \
	}
	OUTPUT_TARGET=$$(python3 -c 'import json; print(json.load(open("$(META)", encoding="utf-8-sig"))["output_target"])'); \
	if [ "$$OUTPUT_TARGET" = "markdown_only" ]; then \
		echo "=== [deliver] meta 指定 markdown_only，仅生成终稿 ==="; \
		finish_with_status; \
	fi
	if [ "$$OUTPUT_TARGET" != "lark" ]; then \
		echo "❌ 未实现的 output_target：$$OUTPUT_TARGET"; exit 1; \
	fi
	rm -f $(LARK_OK) $(DOC_RESULT) $(DOC_UPDATE) $(DOC_FETCH) $(LARK_PERMISSION) $(LARK_PATCH) $(LARK_ERROR)
	if [ "$(PUBLIC_LARK)" != "0" ] && [ "$(PUBLIC_LARK)" != "1" ]; then \
		block_lark permission_contract "PUBLIC_LARK 只接受0或1；1仅表示用户已明确授权本次文档使用 anyone_readable 公网档位。"; \
	fi
	if [ "$(PUBLIC_LARK)" = "1" ] && [ "$(PUBLIC_LARK_ORIGIN)" != "command line" ]; then \
		block_lark permission_contract "PUBLIC_LARK=1 必须由本次 make 命令行显式传入，不能继承环境变量或文件默认值。"; \
	fi
	if ! DOC_TITLE=$$(python3 -c 'import pathlib,re,sys; text=pathlib.Path(sys.argv[1]).read_text(encoding="utf-8-sig"); match=re.search(r"(?m)^#\s+(.+?)\s*$$",text); assert match and match.group(1).strip(); print(match.group(1).strip())' "$(FINAL)"); then \
		block_lark title "无法从终稿读取文档标题。"; \
	fi
	echo "=== [deliver] 创建无正文飞书文档并先验权 ==="
	if ! ( cd $(WF) && lark-cli docs +create --title "$$DOC_TITLE" --json > doc-result.json 2> lark_error.log ); then \
		block_lark create "lark-cli 创建飞书文档失败；检查登录、权限及 $(LARK_ERROR)。"; \
	fi
	if ! DOC_ID=$$(python3 -c 'import json; print(json.load(open("$(DOC_RESULT)", encoding="utf-8-sig"))["data"]["document"]["document_id"])' 2>> $(LARK_ERROR)); then \
		block_lark create_result "无法从 $(DOC_RESULT) 解析 document_id；检查创建响应及 $(LARK_ERROR)。"; \
	fi
	if ! DOC_URL=$$(python3 -c 'import json; print(json.load(open("$(DOC_RESULT)", encoding="utf-8-sig"))["data"]["document"]["url"])' 2>> $(LARK_ERROR)); then \
		block_lark create_result "无法从 $(DOC_RESULT) 解析 document.url；检查创建响应及 $(LARK_ERROR)。"; \
	fi
	if [ -z "$$DOC_ID" ] || [ "$$DOC_ID" = "null" ]; then \
		block_lark create_result "$(DOC_RESULT) 未返回有效 document_id。"; \
	fi
	if [ -z "$$DOC_URL" ] || [ "$$DOC_URL" = "null" ]; then \
		block_lark create_result "$(DOC_RESULT) 未返回有效 document.url。"; \
	fi
	echo "[deliver] 文档已创建：$$DOC_URL"
	if [ "$(PUBLIC_LARK)" = "1" ]; then \
		echo "=== [deliver] 按本轮明确授权设置 anyone_readable 公网档位 ==="; \
		if ! lark-cli drive permission.public patch --token "$$DOC_ID" --type docx \
			--data '{"external_access": true, "link_share_entity": "anyone_readable"}' \
			--yes --format json > $(LARK_PATCH) 2> $(LARK_ERROR); then \
			block_lark permission_patch "已声明公开授权，但公开权限更新失败；检查 $(LARK_PATCH) 与 $(LARK_ERROR)。"; \
		fi; \
	else \
		echo "=== [deliver] 未授权公开，不执行高风险权限写入 ==="; \
	fi
	echo "=== [deliver] 读取并校验权限快照 ==="
	if ! lark-cli drive +permission-get-setting --token "$$DOC_ID" --type docx \
		--format json > $(LARK_PERMISSION) 2> $(LARK_ERROR); then \
		block_lark permission_fetch "无法读取飞书权限，不能证明文档满足交付权限合同；检查 $(LARK_ERROR)。"; \
	fi
	if ! PERMISSION_PUBLIC=$$(LARK_EXPECT_PUBLIC="$(PUBLIC_LARK)" python3 -c 'import json,os,sys; payload=json.load(open("$(LARK_PERMISSION)",encoding="utf-8-sig")); permission=(payload.get("data") or {}).get("permission_public"); print(json.dumps(permission,ensure_ascii=False,separators=(",",":"))); public=os.environ["LARK_EXPECT_PUBLIC"]=="1"; ok=isinstance(permission,dict) and ((permission.get("external_access") is True and permission.get("link_share_entity")=="anyone_readable") if public else (permission.get("external_access") is False and permission.get("link_share_entity")=="closed")); sys.exit(0 if ok else 1)' 2>> $(LARK_ERROR)); then \
		if [ "$(PUBLIC_LARK)" = "1" ]; then \
			block_lark permission_policy "权限读回不等于已授权的 external_access=true + anyone_readable；实际值：$${PERMISSION_PUBLIC:-不可解析}。"; \
		else \
			block_lark permission_policy "未授权公开且权限读回不是私有档位；要求 external_access=false 且 link_share_entity=closed，实际值：$${PERMISSION_PUBLIC:-不可解析}。请先取得用户对具体收紧操作的确认。"; \
		fi; \
	fi
	echo "=== [deliver] 权限符合合同，写入终稿 ==="
	if ! ( cd $(WF) && lark-cli docs +update --doc "$$DOC_ID" --command overwrite --doc-format markdown --content @paper_final.md --json > doc-update-result.json 2> lark_error.log ); then \
		block_lark update "飞书文档已通过权限检查，但正文写入失败；检查 $(DOC_UPDATE) 与 $(LARK_ERROR)。"; \
	fi
	echo "=== [deliver] 读回正文并校验 ==="
	if ! lark-cli docs +fetch --api-version v2 --doc "$$DOC_URL" --doc-format xml > $(DOC_FETCH) 2> $(LARK_ERROR); then \
		block_lark fetch "lark-cli 读回飞书文档失败；检查 $(LARK_ERROR)。"; \
	fi
	if ! python3 $(SCRIPTS)/check_lark.py --xml $(DOC_FETCH) --source $(FINAL) --meta $(META) --write-report $(LARK_OK) 2>> $(LARK_ERROR); then \
		if [ ! -s "$(LARK_OK)" ]; then \
			write_lark_failure check "check_lark.py 执行失败且未生成报告；检查输入文件与运行环境。"; \
		fi; \
		finish_with_status; \
	fi
	if ! LARK_PERMISSION_MODE=$$(if [ "$(PUBLIC_LARK)" = "1" ]; then printf '%s' public_anyone_readable; else printf '%s' non_public; fi) \
		LARK_DOCUMENT_ID="$$DOC_ID" \
		LARK_DOCUMENT_URL="$$DOC_URL" \
		python3 -c 'import hashlib,json,os; from pathlib import Path; report_path=Path("$(LARK_OK)"); permission_path=Path("$(LARK_PERMISSION)"); report=json.loads(report_path.read_text(encoding="utf-8-sig")); snapshot=json.loads(permission_path.read_text(encoding="utf-8-sig")); result=report.setdefault("result",{}); result["document_id"]=os.environ["LARK_DOCUMENT_ID"]; result["document_url"]=os.environ["LARK_DOCUMENT_URL"]; result["permission_mode"]=os.environ["LARK_PERMISSION_MODE"]; result["permission_snapshot_file"]="$(LARK_PERMISSION)"; result["permission_snapshot_sha256"]=hashlib.sha256(permission_path.read_bytes()).hexdigest(); result["permission_public"]=(snapshot.get("data") or {}).get("permission_public"); report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")' 2>> $(LARK_ERROR); then \
		block_lark permission_report "正文校验已通过，但无法把权限快照引用写入 $(LARK_OK)。"; \
	fi
	echo ""
	echo "🎉 交付完成，文档链接：$$DOC_URL"
	python3 $(SCRIPTS)/status.py --workflow $(WF)

status:
	@python3 $(SCRIPTS)/status.py --workflow $(WF)

clean:
	@rm -f $(PREPARE_OK) $(DRAFT_OK) $(LARK_OK) $(DOC_RESULT) $(DOC_UPDATE) $(DOC_FETCH) $(LARK_PERMISSION) $(LARK_PATCH) $(LARK_ERROR) $(WF)/verified_refs.json $(WF)/verification_report.json
	@echo "已清理交付中间产物，正文与候选文献保留。"

help:
	@echo "make prepare | write | deliver | status | clean"
	@echo "交付目标只读取 $(META) 的 output_target=lark|markdown_only"
	@echo "变量：STYLE MIN_WORDS MAX_WORDS MIN_CORE OFFLINE PUBLIC_LARK"
	@echo "持久篇幅要求写入 meta.json 的 min_words/max_words；命令行变量仅覆盖本次调用。"
	@echo "PUBLIC_LARK=1 仅在用户已明确授权本次文档使用 anyone_readable 公网档位时传入"

FORCE:
