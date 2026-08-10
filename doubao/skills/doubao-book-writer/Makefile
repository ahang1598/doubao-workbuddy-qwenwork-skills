# doubao-book-writer 交付编排（Makefile 增量DAG）
#
# 控制流在 make 中。模型只运行 make WORKDIR=<书稿目录>，阶段顺序和是否通过
# 由文件依赖与脚本共同决定。
#
# 注意：检查报告会在失败时写入，不能作为 make 成功目标。Make 只依赖 *.ok
# 通过态 stamp；recipe 开头删除 stamp，脚本成功后才重新 touch。

SHELL := /bin/bash
.ONESHELL:
.PHONY: all prepare write deliver quality status clean help _need_workspace

SCRIPTS := scripts/pipeline
TITLE ?= 书稿终稿
SKIP_LARK ?= 0

ifndef WORKDIR
WORKDIR_ERR := 1
endif

WF = $(WORKDIR)/.doubao-book-writer
REPORTS = $(WF)/reports
STAMPS = $(WF)/stamps
CHECKLIST = $(WF)/requirement-checklist.json
PREPARE_REPORT = $(REPORTS)/prepare_check.json
DRAFT_REPORT = $(REPORTS)/draft_check.json
LARK_REPORT = $(REPORTS)/lark_check.json
PREPARE_STAMP = $(STAMPS)/prepare.ok
DRAFT_STAMP = $(STAMPS)/draft.ok
FINAL_STAMP = $(STAMPS)/final.ok
LARK_STAMP = $(STAMPS)/lark.ok
SHORT_MS = $(WORKDIR)/manuscript.md
MANUSCRIPT_DIR = $(WORKDIR)/manuscript
MANUSCRIPT_FILES := $(shell if [ -n "$(WORKDIR)" ] && [ -d "$(WORKDIR)/manuscript" ]; then find "$(WORKDIR)/manuscript" -type f -name '*.md' 2>/dev/null; fi)
DRAFT_INPUTS = $(wildcard $(SHORT_MS) $(MANUSCRIPT_DIR)) $(MANUSCRIPT_FILES)
OUTLINE_INPUTS = $(wildcard $(WORKDIR)/outline.md $(WORKDIR)/chapter-ledger.md)
FINAL = $(WORKDIR)/deliverables/final.md
DOC_RESULT = $(WF)/doc-result.json
DOC_FETCH = $(WF)/doc_fetch.md
DELIVERY_RECEIPT = $(WF)/delivery-receipt.json

all: deliver

_need_workspace:
	@if [ -z "$(WORKDIR)" ]; then \
		echo "❌ 必须指定 WORKDIR=<书稿目录>，例如 make deliver WORKDIR=./mybook"; \
		exit 2; \
	fi

$(CHECKLIST): | _need_workspace
	@mkdir -p "$(WF)"
	@echo "❌ 缺少需求清单 $(CHECKLIST)"
	@echo "请按 references/checklist-schema.md 创建：冻结 topic、requirements、layout、wordCountRules。"
	@echo "长稿还需 outline.md 与 chapter-ledger.md。"
	@exit 1

$(PREPARE_STAMP): $(CHECKLIST) $(OUTLINE_INPUTS) scripts/pipeline/check_prepare.mjs scripts/gates/outline-structure-gate.mjs | _need_workspace
	@set -euo pipefail
	mkdir -p "$(REPORTS)" "$(STAMPS)"
	rm -f "$@"
	echo "=== [prepare] 校验需求清单与布局 ==="
	node $(SCRIPTS)/check_prepare.mjs --workspace "$(WORKDIR)" --write-report
	touch "$@"
	echo "[prepare] 通过"

prepare: $(PREPARE_STAMP)

$(DRAFT_STAMP): $(PREPARE_STAMP) $(WORKDIR) $(DRAFT_INPUTS) scripts/pipeline/check_draft.mjs scripts/quality/check-writing-shape.mjs scripts/gates/manuscript-word-count-gate.mjs scripts/core/refresh-chapter-ledger.mjs scripts/gates/verify-chapter-ledger-truth.mjs | _need_workspace
	@set -euo pipefail
	mkdir -p "$(REPORTS)" "$(STAMPS)"
	rm -f "$@"
	echo "=== [write] 校验正文形态与字数 ==="
	node $(SCRIPTS)/check_draft.mjs --workspace "$(WORKDIR)" --write-report
	touch "$@"
	echo "[write] 通过"

write: $(DRAFT_STAMP)

quality: _need_workspace
	@set -euo pipefail
	echo "=== [quality] 深度质检 S/P/C/B + 机器硬指标 ==="
	node $(SCRIPTS)/check_quality.mjs --workspace "$(WORKDIR)"

$(FINAL_STAMP): $(DRAFT_STAMP) $(WORKDIR) $(DRAFT_INPUTS) scripts/pipeline/merge_chapters.mjs scripts/core/merge-chapters.mjs | _need_workspace
	@set -euo pipefail
	mkdir -p "$(WORKDIR)/deliverables" "$(STAMPS)"
	rm -f "$@"
	if [ -f "$(SHORT_MS)" ] && [ -s "$(SHORT_MS)" ]; then \
		echo "=== [deliver] 短稿：复制 manuscript.md 为终稿 ==="; \
		cp "$(SHORT_MS)" "$(FINAL)"; \
	else \
		echo "=== [deliver] 长稿：合并 manuscript/*.md 为终稿 ==="; \
		node $(SCRIPTS)/merge_chapters.mjs --workspace "$(WORKDIR)" --output "$(FINAL)"; \
	fi
	touch "$@"
	echo "[deliver] 终稿已生成 $(FINAL)"

$(LARK_STAMP): $(FINAL_STAMP) $(FINAL) scripts/pipeline/check_lark.mjs scripts/pipeline/delivery_cache.mjs | _need_workspace
	@set -euo pipefail
	mkdir -p "$(REPORTS)" "$(STAMPS)"
	rm -f "$@"
	if node $(SCRIPTS)/delivery_cache.mjs check --workspace "$(WORKDIR)" --final "$(FINAL)"; then \
		echo "=== [deliver] 终稿未变化，复用上次飞书交付 ==="; \
		touch "$@"; \
		exit 0; \
	fi
	echo "=== [deliver] 创建飞书文档 ==="
	( cd "$(WORKDIR)" && lark-cli docs +create --api-version v2 --doc-format markdown --content @deliverables/final.md --format json > .doubao-book-writer/doc-result.json )
	DOC_URL=$$(node -e 'const fs=require("fs");try{const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));process.stdout.write((j.data&&j.data.document&&j.data.document.url)||"")}catch{process.stdout.write("")}' "$(DOC_RESULT)"); \
	if [ -z "$$DOC_URL" ]; then \
		echo "❌ 飞书文档创建失败，检查 lark-cli 登录与 $(DOC_RESULT)"; exit 1; \
	fi; \
	echo "[deliver] 文档已创建：$$DOC_URL"; \
	echo "=== [deliver] 读回校验 ==="; \
	lark-cli docs +fetch --api-version v2 --doc "$$DOC_URL" --doc-format markdown --format json > "$(DOC_FETCH)"; \
	node $(SCRIPTS)/check_lark.mjs --markdown "$(FINAL)" --fetched "$(DOC_FETCH)" --workspace "$(WORKDIR)" --write-report; \
	node $(SCRIPTS)/delivery_cache.mjs record --workspace "$(WORKDIR)" --final "$(FINAL)" --doc-result "$(DOC_RESULT)" --lark-report "$(LARK_REPORT)"; \
	touch "$@"; \
	echo ""; \
	echo "🎉 交付完成，文档链接：$$DOC_URL"

ifeq ($(SKIP_LARK),1)
deliver: $(FINAL_STAMP)
	@node $(SCRIPTS)/status.mjs --workspace "$(WORKDIR)" --allow-lark-skip
else
deliver: $(LARK_STAMP)
	@node $(SCRIPTS)/status.mjs --workspace "$(WORKDIR)"
endif

status: _need_workspace
	@if [ "$(SKIP_LARK)" = "1" ]; then \
		node $(SCRIPTS)/status.mjs --workspace "$(WORKDIR)" --allow-lark-skip; \
	else \
		node $(SCRIPTS)/status.mjs --workspace "$(WORKDIR)"; \
	fi

clean: _need_workspace
	@rm -f "$(PREPARE_STAMP)" "$(DRAFT_STAMP)" "$(FINAL_STAMP)" "$(LARK_STAMP)"
	@rm -f "$(PREPARE_REPORT)" "$(DRAFT_REPORT)" "$(LARK_REPORT)" "$(DOC_RESULT)" "$(DOC_FETCH)" "$(DELIVERY_RECEIPT)"
	@echo "已清理检查报告、通过态 stamp 与交付中间产物，正文与需求清单保留。"

help:
	@echo "make {prepare|write|deliver|quality|status|clean} WORKDIR=<书稿目录> [SKIP_LARK=1] [TITLE=...]"
